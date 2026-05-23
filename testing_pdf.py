import os
import re
import math
from pathlib import Path
from collections import defaultdict, Counter
import fitz

def extract_words(folder_path):
    
    candidate_resume = []
    
    folder = Path(folder_path)

    for file_path in folder.glob("*.pdf"):
        
        print(f"Opening file via file path {file_path}")
        
        if not file_path.exists:
            print("File does not Exist")
        
        all_words  = []
        all_sizes  = []    
        resume = {
            "metadata" : {
                "file_path" : file_path,
                "page_width" : 612,
                "major_font_size" : {}
            },
            "all_words" : []
        }
                
        # page_width = 612 #default
        doc = fitz.open(file_path)

        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]

            if page_num == 0:
                resume["metadata"]["page_width"] = round(page.rect.width)
                # print(f"PAGE WIDTH: {page_width}")
            
            # if(page_num > 0):
            #     if not page_num == resume["metadata"]["page_width"]:
            #         continue
                
            for block in blocks:
            
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                                    
                        text = span["text"].strip()
                        size = math.ceil(span["size"]*10)/10
                        bold = bool(span["flags"] & 2**4)
                        x0   = round(span["origin"][0], 1)
                        y0   = round(span["origin"][1], 1)
                        x1   = span['bbox'][2]
                        y1   = span['bbox'][3]
                        
                        if not text or text.isspace() or text == "|" or len(text) <= 3 or len(text) == 0 or text == "•":
                            continue
                                
                                # print({
                                #     "text": text,
                                #     "x0": x0,
                                #     "x1": x1,
                                #     "y0": y0,
                                #     "size": size
                                #     })

                        resume["all_words"].append({
                            "text" : text,
                            "size" : size,
                            "bold" : bold,
                            "y0"   : y0,
                            "x0"   : x0,
                            "x1"   : x1,
                            "y1"   : y1,
                            "page" : page_num + 1
                        })

                        all_sizes.append(size)
                   
        all_sizes.sort()                                
        size_counts  = Counter(all_sizes)       
        major_font_size = {
            "name_font" : size_counts.most_common()[-1][0],
            "body_font" : size_counts.most_common(1)[0][0]
        }
        
        resume["metadata"]["major_font_size"] = major_font_size

        candidate_resume.append(resume)

    return candidate_resume


def checking_resume_std(resume_list):
    
    rejected_resume = []
    resume_list_copy = resume_list
    
    for resume_index, resume_data in enumerate(resume_list_copy): 
        
        page_width = resume_data["metadata"]["page_width"]
        cluster_A = []
        cluster_B = []
        adaptive_threshold = round(page_width/100)*15
        
        page_third_val = round(page_width/100)*25
        # print(f"adaptive threshold {adaptive_threshold}")
        
        x_positions = sorted(round(w["x0"]) for w in resume_data["all_words"])
        for x0 in x_positions:
            if x0 in range(x_positions[0], adaptive_threshold):
                cluster_A.append(x0)
            else:
                cluster_B.append(x0)
        
        # print(f"Lenght of Cluster A: {len(cluster_A)}")
        # print(f"Lenght of Cluster B: {len(cluster_B)}")
        
        check_cond = max(len(cluster_A), len(cluster_B)) / 2
        
        if(len(cluster_A) >= check_cond and len(cluster_B) >= check_cond):
            
            cluster_A_centroid = sum(cluster_A) / len(cluster_A)
            cluster_B_centroid = sum(cluster_B) / len(cluster_B)
            
            separation_ratio = abs(cluster_B_centroid - cluster_A_centroid) / page_width
            
            # print(f"Separation Ratio of {resume_data['metadata']['file_path']}: {separation_ratio}")
            if(separation_ratio > 0.25):
                rejected_resume.append({"index" : resume_index, "path" : resume_data['metadata']['file_path']})
                print(f"Given Resume: {resume_data['metadata']['file_path']} is NOT ATS Standard")
            else:
                #going to second round checking
                if(detect_column_layout(all_words= resume_data["all_words"] , page_width = page_width) == "ATS"):
                    print(f"Given Resume: {resume_data['metadata']['file_path']} is ATS Standard")
                else:
                    rejected_resume.append({"index" : resume_index, "path" : resume_data['metadata']['file_path']})
                    print(f"Given Resume: {resume_data['metadata']['file_path']} is NOT ATS Standard")
            
        else:
            #going to second round checking
                if(detect_column_layout(all_words= resume_data["all_words"] , page_width = page_width) == "ATS"):
                    print(f"Given Resume: {resume_data['metadata']['file_path']} is ATS Standard")
                else:
                    rejected_resume.append({"index" : resume_index, "path" : resume_data['metadata']['file_path']})
                    print(f"Given Resume: {resume_data['metadata']['file_path']} is NOT ATS Standard")
    
    rejected_resume_path = []
    for rej in rejected_resume:
        for rej_key, rej_val in rej.items():
            if(rej_key == "index"):
                del resume_list_copy[rej_val]
            elif(rej_key == "path"):
                rejected_resume_path.append(rej_val)
    
    return resume_list_copy, rejected_resume_path

def detect_column_layout(all_words, page_width):  # 612 is standard A4 width in points

    # group words by y0 — same y = same line
    
    line_buckets = defaultdict(list)

    for word in all_words:
        y_key = round(word["y0"], 1)
        line_buckets[y_key].append(word)

    
    multi_column_votes = 0
    total_lines = len(line_buckets)

    for y_key, words in line_buckets.items():

        # sort words left to right by x0
        words_sorted = sorted(words, key=lambda w: w["x0"])
        
        # print(f"\nLINE y={y_key}")
        # for w in words_sorted:
        #     print(w["text"], w["x0"], w["x1"])
        
        
        for i in range(1, len(words_sorted)):
            prev_word    = words_sorted[i - 1]
            
            current_word = words_sorted[i]
            # gap between end of prev word and start of current word
            gap = current_word["x0"] - prev_word["x1"]

            # print(
            #     f"GAP: {gap} | "
            #     f"prev='{prev_word['text']}' ({prev_word['x1']}) -> "
            #     f"curr='{current_word['text']}' ({current_word['x0']})"
            #     )

            if gap > page_width * 0.25:  # 25% of page width = column separator
                multi_column_votes += 1
                break  # one vote per line is enough

    # if more than 20% of lines show column gap → multi column resume
    column_ratio = multi_column_votes / total_lines if total_lines > 0 else 0

    # print(f"column_ratio = {column_ratio}")

    # print(f"\n[COLUMN DETECTION]")
    # print(f"  Total lines         : {total_lines}")
    # print(f"  Multi column votes  : {multi_column_votes}")
    # print(f"  Column ratio        : {round(column_ratio * 100, 2)}%")

    if column_ratio > 0.20:
        # print(f"  Result              : ⚠️  MULTI COLUMN — ATS parsing not supported")
        return "NON-ATS"
    else:
        # print(f"  Result              : ✅  SINGLE COLUMN — Safe to proceed")
        return "ATS"

def build_lines(accepted_resume):
    
    resume_list = []
   
    # group words by y0
    for resume in accepted_resume:
        line_buckets = defaultdict(list)
        resume_dict = {    } 
        # print(resume)
        lines = []
        heading_list = []
        
        font_size = resume["metadata"]["major_font_size"]
        
        for word in resume["all_words"]:
            y_key = round(word["y0"], 1)
            line_buckets[y_key].append(word)

        # sort each line left to right by x0
        for y_key in line_buckets:
            line_buckets[y_key].sort(key=lambda w: w["x0"])
    
        # sort lines top to bottom (highest y0 first in PyMuPDF = top of page)
        sorted_lines = sorted(line_buckets.items(), key=lambda x: x[0])
    
        for i, (y_key, words) in enumerate(sorted_lines):
        
            line_text = " ".join(w["text"] for w in words)
            avg_size  = round(sum(w["size"] for w in words) / len(words), 2)
            is_bold   = any(w["bold"] for w in words)
                
            is_heading = True if(avg_size > font_size["body_font"] and avg_size < font_size["name_font"] and line_text.isupper()) else False
            if is_heading:
                heading_list.append(i)    
            lines.append({
                "text"  : line_text,
                "y0"    : y_key,
                "size"  : avg_size,
                "bold"  : is_bold,
                "heading" : is_heading
            })

        resume_dict["metadata"] = resume["metadata"]
        resume_dict["line"] = lines
        resume_dict["heading_index"] = heading_list
        
        resume_list.append(resume_dict)
        # print(resume)
    
    for resume in resume_list:
        print(f"METADATA : {resume['metadata']}")
        print(f"Lines : {resume['line']}")
        print(f"HEADING LIST : {resume['heading_index']}")
    
    
    return resume_list

def section_chunking(resume_data):
    print("Section Chunking")
    
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    section_map = {
        "skills": ["skills", "technical skills", "core skills", "expertise", "tech skills"],
        "experience": ["work experience", "experience", "professional experience"],
        "education": [ "academic background","education", "qualifications"],
        "projects": ["projects", "personal projects", "academic projects"],
        "certifications": ["certifications", "certificates", "certifications & training"]
        }
    
    resume_doc = []
    for i, resume in enumerate(resume_data):
        # print(resume)
        continue
        section_heading = ""
        metadata = {
                "resume_id": i + 1,
                "candidate_name": "",
                "candidate_email": "",
                "section": "",
                "resume_path": resume["metadata"]["file_path"]
            }
        section_content  = {
            "skills" : [],
            "experience" : [],
            "education" : [],
            "projects" : [],
            "certifications" : []
        }
        metadata["candidate_name"] = resume["line"][0]['text']
        
        heading_index = sorted(resume["heading_index"])
        
        j = 0
        start_i = heading_index[j]
        for i, line in enumerate(resume["line"]):
            # print(i)
            # print(line)
            found_emails = re.findall(EMAIL_PATTERN, line['text'])
            if found_emails:
                metadata["candidate_email"] = found_emails[0]
                continue
                
            if i == start_i: #heading found
                # print(f"j: {j}") #len(heading_index) = 5
                if (j < len(heading_index)-1):
                    j += 1
                    start_i = heading_index[j]
                for section_name, section_list in section_map.items():
            #     # print(f"section_map elements : {section_list}")        
                    for section in section_list:
                        # print(line["text"])
                        if(section == line["text"].lower()): #heading match
                           section_heading = section_name
                        #    print(section_heading)
                            
                           break
                    
            elif section_heading:
                section_content[section_heading].append(line["text"])
        
        for key, val in section_content.items():
            print(f"{key} : {val} \n")
                

if __name__ == "__main__":

    # pdf_path = "resume_test/TestingResume.pdf"
    # pdf_path = "docs/Ahmed_Raza_Resume.pdf"
    # pdf_path = "docs/Syed_Ibad_Ali_Resume.pdf"
    pdf_path = "docs/Bilal Ahmed Resume updated.pdf"
    
    DOC_PATH = "docs"
    
    extracted_resume = extract_words(DOC_PATH)
    
    # print(extracted_resume)
    accepted_resume, rejected_resume_path = checking_resume_std(extracted_resume)
    
    # print(accepted_resume[1])
   
    
    # print(f"Accepted Resume: {accepted_resume}")
    # print(f"Rejected Resume Path: {rejected_resume_path}")

    
    refined_resumes = build_lines(accepted_resume)
    
    
    section_chunking(refined_resumes)
    

   