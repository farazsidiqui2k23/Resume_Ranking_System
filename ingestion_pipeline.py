import os
import re
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def load_resume(docs_path):
    print(f"Laoding Resume from {docs_path}")

    if not os.path.exists(docs_path):
        raise FileNotFoundError(f"The Directory {docs_path} doesn't Exist in your System.")

    loader = DirectoryLoader( #list of doc objects
        path= docs_path,
        glob= "*.pdf",  #only look the file whose extension is .pdf
        loader_cls = PyPDFLoader, 
    )
    
    documents = loader.load()
    
    if len(documents) == 0:
        raise FileNotFoundError(f"No .pdf file found in {docs_path}")
    
    merged_docs = {}
    
    for doc in documents:
        source = doc.metadata["source"]
        # print(source)
        
        if source not in merged_docs:
            merged_docs[source] = ""
            
            # print(doc.page_content)
        else:
            merged_docs[source] += doc.page_content
            
        merged_docs[source] += doc.page_content + "\n"
            
    final_document = []
    
    for source, content in merged_docs.items():
        final_document.append(
            Document(
                page_content=content,
                metadata={"source": source}
            )
        )
        

    for i, doc in enumerate(final_document):
        print(f"\nDocument: {i+1}")
        print(f" metadata: {doc.metadata['source']}")
        print(f"Page Content: {doc.page_content}")
        
        
    return final_document;

def section_chunking(docs):
    print("Splitting Sections")
    
    candidate_resumes = []
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    for i, resume_data in enumerate(docs[1:]):
        print(resume_data.metadata['source'])
        
        # print(f"Seeing Document: {i}")
        
        lines = resume_data.page_content.split("\n")
        
        resume = {
            "meta_data" : {
                "path" : resume_data.metadata['source'], 
                "name" : "",
                "email" : ""
            },
            "page_content" : {
                "skills" : "",  
                "experience": "",
                "projects" : "",
                "education" : "",
                "certifications" : ""
            }
        }    
        
        resume["meta_data"]["name"] = lines[0]
        
        section_map = {
        "skills": ["skills", "technical skills", "core skills", "expertise", "tech skills"],
        "experience": ["work experience", "experience", "professional experience"],
        "education": [ "academic background","education", "qualifications"],
        "projects": ["projects", "personal projects", "academic projects"],
        "certifications": ["certifications", "certificates", "certifications & training"]
        }
        
        current_section = ""
        resume_sec_heading = ""
        email_found = False;
        
        education_line_count = 0
        
        for line in lines:
            print(line)
            if(not email_found):
                found_emails = re.findall(EMAIL_PATTERN, line)
                
                if found_emails:
                    # print("Email Found")
                    resume["meta_data"]["email"] += found_emails[0]
                    email_found = True
                    
            for section_name, section_list in section_map.items():
                # print(f"section_map elements : {section_list}")        
                for sections in section_list:
                    # print(f"section list items: {sections}")
                    if(line.lower().strip() == sections):
                        current_section = section_name
                        resume_sec_heading = sections
                        break
                     
            if(line.lower() in ["professional summary", "career summary", "summary", "achievement",  "achievements", "key achievements"]):
                current_section = ""
                         
            if current_section:
                if(line.lower() != resume_sec_heading):
                    
                    # ✅ EDUCATION LIMIT LOGIC
                    if current_section == "education":
                        
                        if education_line_count < 3:
                            resume["page_content"]["education"] += line + " "
                            education_line_count += 1
                    
                    else:
                        resume["page_content"][current_section] += line + "\n"
                             
        candidate_resumes.append(resume)          
    
    
    
    
    for resume in candidate_resumes:

        print("\n================ RESUME =================")

        print(f"PATH  : {resume['meta_data']['path']}")
        print(f"NAME  : {resume['meta_data']['name'] or 'NOT FOUND'}")
        print(f"EMAIL : {resume['meta_data']['email'] or 'NOT FOUND'}")

        print("\n=========== PAGE CONTENT ===========")

        sections = resume['page_content']

        for section_name, content in sections.items():

            if content and len(content.strip()) > 0:

                print(f"\n--- {section_name.upper()} ---")
                print(f"Length : {len(content)}")
            
                print(f"CONTENT: {content}")

            else:
                print(f"\n--- {section_name.upper()} ---")
                print("Length : 0")
                print("CONTENT NOT FOUND")

        print("\n===========================================\n")
    
        
    return candidate_resumes;
    
def refinining_chunks(chunked_resume):
    
    chat_model = ChatOllama(model="llama3") 
    # chat_model = ChatOllama(model="phi") 
    
    refined_chunk_list = []
    
    SYSTEM_MESSAGE = """You are a resume section validator and cleaner. Your task is to refine extracted resume sections by:
                            1. Removing irrelevant content, headers, formatting artifacts, and noise
                            2. Keeping only content that belongs to the specific section
                            3. Maintaining original meaning and information
                            4. Removing duplicates and redundant entries
                            5. Fixing formatting inconsistencies
                        Return only the cleaned section content, nothing else. Be strict about relevance."""

        # Section-specific prompts
    SECTION_PROMPTS = {
            "skills": """Clean this Skills section. Extract and list only technical skills, programming languages, tools, frameworks, and relevant soft skills. Remove descriptions and context. Return as a clean list.
            CRITICAL: Output ONLY the cleaned list. No introduction. No explanation. No notes.
            Raw content:
            {content}""",
            
            "experience": """Clean this Experience section. Keep company name, job title, duration, key responsibilities, and achievements. Remove narrative fluff, personal opinions, and irrelevant details. Maintain structure and clarity.
            IMPORTANT: Return ONLY the cleaned content. Do not include any explanations, introductions, preamble or notes.
            Raw content:
            {content}""",
            
            "education": """Clean this Education section. Keep degree name, institution, graduation date, GPA (if relevant), and relevant coursework/honors. Remove filler text and descriptions.
            CRITICAL: Output ONLY the cleaned list. No introduction. No explanation. No notes.
            Raw content:
            {content}""",
    
            "projects": """Clean this Projects section. Keep project name, description, technologies used, and outcomes/impact. Remove personal commentary and irrelevant details.
            IMPORTANT: Return ONLY the cleaned content. Do not include any explanations, introductions, preamble or notes.
            Raw content:
            {content}""",
    
            "certifications": """Clean this Certifications section. Keep certification name, issuing organization, date obtained, and credential ID if present. Remove descriptions and context.
            IMPORTANT: Return ONLY the cleaned content. Do not include any explanations, introductions, preamble or notes.
            Raw content:
            {content}"""
        }

    for resume in chunked_resume:
        
        refined_chunk = {
            "meta_data" : resume["meta_data"],
            "page_content" : {
                "skills" : "",  
                "experience": "",
                "projects" : "",
                "education" : "",
                "certifications" : ""
            }
        }  
            # In your loop:
        for section_key, section_data in resume["page_content"].items():
    
            if section_key in SECTION_PROMPTS:
                if(section_data and len(section_data.strip()) > 0):
                    message = [
                        SystemMessage(content=SYSTEM_MESSAGE),
                        HumanMessage(content=SECTION_PROMPTS[section_key].format(content=section_data))
                    ]
        
                    response = chat_model.invoke(message)
                    refined_chunk["page_content"][section_key] = response.content
                else:
                    refined_chunk["page_content"][section_key] = section_data
                
        refined_chunk_list.append(refined_chunk)
            
    for resume in refined_chunk_list:

        print("\n================ RESUME =================")

        print(f"PATH  : {resume['meta_data']['path']}")
        print(f"NAME  : {resume['meta_data']['name'] or 'NOT FOUND'}")
        print(f"EMAIL : {resume['meta_data']['email'] or 'NOT FOUND'}")

        print("\n=========== PAGE CONTENT ===========")

        sections = resume['page_content']

        for section_name, content in sections.items():

            if content and len(content.strip()) > 0:

                print(f"\n--- {section_name.upper()} ---")
                print(f"Length : {len(content)}")
            
                print(f"CONTENT: {content}")

            else:
                print(f"\n--- {section_name.upper()} ---")
                print("Length : 0")
                print("CONTENT NOT FOUND")

        print("\n===========================================\n")
        
    return refined_chunk_list
    
def creating_embeddings(section_chunks, persist_direct = "db/chroma_db"):
    print("Creating Embeddings")
    
    
    embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    documents = []
    
    for i, resume in enumerate(section_chunks):
        print(f"Creating Embedding of Resume: {i+1}")
        
        resume_id = i + 1
        candidate_name = resume['meta_data']['name']
        candidate_email = resume['meta_data']['email']
        resume_path = resume['meta_data']['path']
        
        for section_name, section_content in resume["page_content"].items():
            
            if not section_content or section_content.strip() == "":
                continue
            
            metadata = {
                "resume_id": resume_id,
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "section": section_name,
                "resume_path": resume_path
            } 
            
            doc = Document(
                page_content= section_content,
                metadata = metadata
            )
            
            documents.append(doc)
            print(f"  Added {section_name} section for {candidate_name}")
            
    print(f"\nCreating Chroma collection with {len(documents)} documents...")
    
    vector_store = Chroma.from_documents(
        documents= documents,
        embedding= embedding_model,
        persist_directory= persist_direct
    )

    print(f"Embeddings created and persisted at: {persist_direct}")
    
    return vector_store
    
    
def main():
    
    DOCS_PATH = "docs"
    
    print("Main Function")
    
    documents = load_resume(docs_path= DOCS_PATH)
 
    # chuked_resume = section_chunking(docs= documents)
    
    # creating_embeddings(chuked_resume)
    
    
    
  
    
if __name__ == "__main__":
    main()