import os
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from embeddings import BGE_MODEL

DB_PATH = "db\chroma_db"
VECTOR_STORE = Chroma(
    persist_directory= DB_PATH,
    embedding_function = BGE_MODEL,
    collection_metadata= {"hnsw:space" : "cosine"}    
    )

def add_jd_as_whole_blob(jd : str):
    print(f"Job Desc Len: {len(jd)}")
    
    #we're using rag fusion search
    
    
def add_jd_as_section(jd : dict):
    #experience, skills, education
    #print(f"Experience: {jd['experience']} \n Skills: {jd['skills']} \n Education: {jd['education']}")

    result = query_resume_by_section(jd)
    
    # print(result)
    
    score = extract_resume_scores(result)
    
    comp_score = calc_composite_scores(score)
    
    rank_resumes(comp_score)
    

def query_resume_by_section(parse_jd : dict):
    
    results = {
        "skills" : [],
        "experience" : [],
        "education" : []
    }
    
    REQUIRED_K = 3
    
    if parse_jd["skills"].strip():
        skill_result = VECTOR_STORE.similarity_search_with_score(
            query= parse_jd['skills'],
            k= REQUIRED_K,
            filter={"section": "skills"}
        )
        results['skills'] = skill_result
    
    
    if parse_jd["experience"].strip():
        exp_results = VECTOR_STORE.similarity_search_with_score(
            query=parse_jd["experience"],
            k=REQUIRED_K,
            filter={"section": "experience"}
        )
        results["experience"] = exp_results
    
    # Query education section (if exists in JD)
    if parse_jd["education"].strip():
        edu_results = VECTOR_STORE.similarity_search_with_score(
            query=parse_jd["education"],
            k=REQUIRED_K,
            filter={"section": "education"}
        )
        results["education"] = edu_results
    
    return results

def extract_resume_scores(search_results):
    """
    Convert search results into resume-level scores
    Each result = (document, similarity_score)
    Extract resume_id from metadata
    """
    
    resume_scores = {
        "skills": {},      # {resume_id: score}
        "experience": {},
        "education": {}
    }
    
    for section_name, results in search_results.items():
        for document, similarity_distance in results:
            resume_id = document.metadata["resume_id"]
            
            similarity_score = 1 - similarity_distance
            
            # Store score (similarity is already 0-1)
            if resume_id not in resume_scores[section_name]:
                resume_scores[section_name][resume_id] = similarity_score
    
    # print(resume_scores)
    
    return resume_scores
    
def calc_composite_scores(resume_score):
        
    '''resume score
        {
        'skills': {4: 0.7193393707275391, 3: 0.8640181422233582, 1: 1.038132905960083}, 
        'experience': {4: 1.4268860816955566, 1: 1.4517958164215088, 3: 1.6093555688858032}, 
        'education': {}
        }
        '''
        
        #later we'll take input from user
        #we can also set it according to job title internship, junior, senior position
    weights = {
            "experience" : 0.6,
            "skills" : 0.3,
            "education" : 0.1
        }    
        
    composite_score = {}
        
    all_resume_ids = set() #to remove dublicates
        
    for section_scores in resume_score.values():
        all_resume_ids.update(section_scores.keys())
        
    
    for resume_id in all_resume_ids:
        # print(resume_id)
        weighted_score = 0
        total_weight = 0
        
        #resume id {1, 3, 4}
        for section_name, weight in weights.items(): 
           
            if resume_id in resume_score[section_name]: 
                # print(resume_id)
                section_score = resume_score[section_name][resume_id] 
                weighted_score += section_score * weight
                total_weight += weight
                
        if total_weight > 0:
            composite_score[resume_id] = weighted_score / 1
        else:
            composite_score[resume_id] = 0
    
    # print(f"composite score: {composite_score}")
    return composite_score
            
    #composite score: {1: 1.3139081796010337, 3: 1.3609097599983218, 4: 1.1910371780395508}
    #composite score: {1: 1.1825173616409301, 3: 1.2248187839984894, 4: 1.0719334602355957}
    
def rank_resumes(composite_scores):
    """
    Sort resumes by composite score
    Add resume metadata (name, email, path)
    Return top N resumes
    """
    
    # Sort by score (descending)
    sorted_resumes = sorted(
        composite_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    # candidate_info = {}
    # all_metadata = VECTOR_STORE.get()['metadatas']
   
    ranked_results = []
    
    for resume_id, score in sorted_resumes[:10]:  # Top 10
        
        # Get resume metadata from vector store
        # (You need to query Chroma to get candidate info)
        # For now, assume you have a function that maps resume_id to metadata
        
        resume_info = {
            "resume_id": resume_id,
            "candidate_name" : finding_cadidate(resume_id),
            "composite_score": score,
            "rank": len(ranked_results) + 1,
            # Add metadata here
        }
        ranked_results.append(resume_info)
    
    print(ranked_results)
    return ranked_results

def finding_cadidate(resume_id):
    
    resume_metadata_list = VECTOR_STORE.get()['metadatas']
    for data in resume_metadata_list:
        for key , val in data.items():
            if resume_id == val:
                return(data['candidate_name'])
                break

def main():
    print("Main Calling")
    
    # job_desc = {
    # "experience": "2 to 3 years of experience in .NET development. Experience in building web applications using Microsoft technologies. Working in Agile/Scrum environments."
    # ,
    # "skills": "C#, .NET Core, .NET Framework, ASP.NET MVC, Web API, REST APIs and REST services, SQL Server, database design, Entity Framework, ADO.NET, LINQ, HTML, CSS, JavaScript, Git, source control systems, OOP. JWT, OAuth, OpenIddict, Identity, Azure, AWS, Blazor, React, and CI/CD pipelines. collaboration, code review participation, debugging, troubleshooting, and performance optimization."
    # ,
    # "education": ""
    # }
    job_desc = {
    "experience": "2 to 3 years of experience in Android application development. Experience in building and maintaining mobile applications for Android platforms. Working in Agile/Scrum environments.",
    
    "skills": "Java, Kotlin, Android SDK, Android Studio, Jetpack Components, MVVM architecture, Clean Architecture, REST APIs, Retrofit, Volley, JSON parsing, Room Database, SQLite, Firebase, Dependency Injection (Hilt/Dagger), Coroutines, Flow, LiveData, ViewModel, XML layouts, Material Design, Git, source control systems, OOP, design patterns, unit testing, UI testing, app performance optimization, debugging, troubleshooting, Google Play Store deployment, CI/CD pipelines, collaboration, and code review participation.",
    
    "education": ""
    }
    
    add_jd_as_section(job_desc)
    
    
    print("DONE")
    
if __name__ == "__main__":
    main()