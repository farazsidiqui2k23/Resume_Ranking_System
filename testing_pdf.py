import math
from collections import defaultdict, Counter
import fitz

def extract_words(pdf_path):
    all_words  = []
    all_sizes  = []

    doc = fitz.open(pdf_path)
    page_width = 612

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        page_width = round(page.rect.width)
        # print(f"PAGE WIDTH: {page_width}")

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

                    if not text or text.isspace() or text == "|" or len(text) <= 3:
                        continue
                    if len(text.strip()) == 0:
                        continue
                    if text == "•":
                        continue
                    
                    # print({
                    #     "text": text,
                    #     "x0": x0,
                    #     "x1": x1,
                    #     "y0": y0,
                    #     "size": size
                    #     })

                    all_words.append({
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
 
    print(major_font_size)
    return all_words, major_font_size, page_width
    

def checking_resume_std(all_words, page_width):
    cluster_A = []
    cluster_B = []
    adaptive_threshold = round(page_width/100)*15
    page_third_val = round(page_width/100)*25
    # print(f"adaptive threshold {adaptive_threshold}")
    # print(f"25% of page {page_third_val}")
    x_positions = sorted(round(w["x0"]) for w in all_words)
    for x0 in x_positions:
        if x0 in range(x_positions[0], adaptive_threshold):
            cluster_A.append(x0)
        else:
            cluster_B.append(x0)
        
    # print(f"Lenght of Cluster A: {len(cluster_A)}")
    # print(f"Lenght of Cluster B: {len(cluster_B)}")
    
    if(len(cluster_A) >= 5 and len(cluster_B) >= 5):
        
        cluster_A_centroid = sum(cluster_A) / len(cluster_A)
        cluster_B_centroid = sum(cluster_B) / len(cluster_B)
        
        separation_ratio = abs(cluster_B_centroid - cluster_A_centroid) / page_width
         
        print(f"Separation Ratio: {separation_ratio}")
        if(separation_ratio > 0.25):
            print(f"  Result: ⚠️  MULTI COLUMN — ATS parsing not supported")
            return "NON-ATS"
        
    
    return(detect_column_layout(all_words, page_width))
        

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
            
            # if not prev_word['text'].isupper() or not current_word['text'].isupper():
            #     continue
            
           
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
        print(f"  Result              : ⚠️  MULTI COLUMN — ATS parsing not supported")
        return "NON-ATS"
    else:
        print(f"  Result              : ✅  SINGLE COLUMN — Safe to proceed")
        return "ATS"


def build_lines(all_words, major_font_size):
    
    
    line_buckets = defaultdict(list)

    # group words by y0
    for word in all_words:
        y_key = round(word["y0"], 1)
        line_buckets[y_key].append(word)

    # sort each line left to right by x0
    for y_key in line_buckets:
        line_buckets[y_key].sort(key=lambda w: w["x0"])
    
    # sort lines top to bottom (highest y0 first in PyMuPDF = top of page)
    sorted_lines = sorted(line_buckets.items(), key=lambda x: x[0])
    
    lines = []
    heading_list = []
    for i, (y_key, words) in enumerate(sorted_lines):
        
        line_text = " ".join(w["text"] for w in words)
        avg_size  = round(sum(w["size"] for w in words) / len(words), 2)
        is_bold   = any(w["bold"] for w in words)
            
        is_heading = True if(is_bold and avg_size > major_font_size["body_font"] and avg_size < major_font_size["name_font"] and line_text.isupper()) else False
        if is_heading:
            heading_list.append(i)    
        lines.append({
            "text"  : line_text,
            "y0"    : y_key,
            "size"  : avg_size,
            "bold"  : is_bold,
            "heading" : is_heading
        })

    print(f"Resume Contain {len(heading_list)} Headings")
    return lines, heading_list



# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":

    # pdf_path = "resume_test/TestingResume.pdf"
    # pdf_path = "docs/WaqasKhanResume.pdf"
    # pdf_path = "docs/Syed_Ibad_Ali_Resume.pdf"
    pdf_path = "docs/Bilal Ahmed Resume updated.pdf"
    

    # Pass 1
    all_words, major_font_size, pg_width = extract_words(pdf_path)

    # Column detection — before Pass 2
    checking_standard = checking_resume_std(all_words, pg_width)

    print(f"Resume Standard: {checking_standard}")
    
    if(checking_standard.strip() == "ATS"):
        build_lines(all_words, major_font_size)
    

   