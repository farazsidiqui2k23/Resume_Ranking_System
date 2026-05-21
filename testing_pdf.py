import pdfplumber
import math
from collections import defaultdict, Counter
import fitz
# def extract_characters():
#     all_chars = []
#     pdf_file = 'resume_test\TestingResume.pdf'

#     with pdfplumber.open(pdf_file) as pdf:
#         for page_num, page in enumerate(pdf.pages):
            
#             chars = page.chars
#             for char in chars:
#                 all_chars.append({
#                     "text"    : char["text"],
#                     "x0"      : char["x0"],
#                     "x1"      : char["x1"],
#                     "y0"      : char["y0"],
#                     # "size"    : round(char["size"], 5),
#                     "size" : math.ceil(char["size"] * 10)/10,
#                     "fontname": char["fontname"],
#                     "page"    : page_num + 1
#                 })
        
#     for c in all_chars:
#         print (c)    
#     return all_chars;

# def group_by_line(chars):
#     lines = defaultdict(list)

#     for char in chars:
#         # round y0 to 1 decimal to handle floating point noise
#         # e.g. 644.0323 and 644.0324 are the same line
#         y_key = round(char["y0"], 1)
#         lines[y_key].append(char)

#     # sort each line's characters by x0 left to right
#     for y_key in lines:
#         lines[y_key].sort(key=lambda c: c["x0"])

#     # return lines sorted top to bottom (highest y0 first in PDF = top of page)
#     sorted_lines = sorted(lines.items(), key=lambda x: x[0], reverse=True)

#     return sorted_lines


# def detect_spaces(line_chars):
#     words = []
#     current_word = line_chars[0]["text"]

#     for i in range(1, len(line_chars)):
#         prev_char    = line_chars[i - 1]
#         current_char = line_chars[i]

#         gap = current_char["x0"] - prev_char["x1"]
#         space_threshold = prev_char["size"] * 0.3

#         if gap > space_threshold:
#             words.append(current_word)
#             current_word = current_char["text"]
#         else:
#             current_word += current_char["text"]

#     words.append(current_word)
#     return words


# def extract_lines(chars):
#     grouped = group_by_line(chars)
#     result  = []

#     for y_key, line_chars in grouped:
#         words     = detect_spaces(line_chars)
#         line_text = " ".join(words)
#         avg_size  = sum(c["size"] for c in line_chars) / len(line_chars)
#         fontname  = line_chars[0]["fontname"]

#         result.append({
#             "text"    : line_text,
#             "y0"      : y_key,
#             "size"    : round(avg_size, 2),
#             "fontname": fontname,
#             "is_bold" : "Bold" in fontname or "bold" in fontname
#         })

#     print(result)
#     return result

# if __name__ == "__main__":
    
#     # Step 1 — raw characters
#     chars = extract_characters()
#     print(f"\n extract_characters → returns {len(chars)} character dicts")
#     print("  sample:", chars[0])

#     # Step 2 — group by line and sort by x
#     grouped = group_by_line(chars)
#     print(f"\n group_by_line → returns {len(grouped)} lines (tuples)")
#     print("  sample tuple key (y0)  :", grouped[0][0])
#     print("  sample chars in line   :", [c["text"] for c in grouped[0][1]])

#     # Step 3 — detect spaces within one line
#     first_line_chars = grouped[0][1]
#     words = detect_spaces(first_line_chars)
#     print(f"\n detect_spaces → returns {len(words)} words")
#     print("  words:", words)

#     # Step 4 — full pipeline, all lines with metadata
#     lines = extract_lines(chars)
#     print(f"\n extract_lines → returns {len(lines)} line dicts")
#     for line in lines:
#         print(f"  y0:{line['y0']}  bold:{line['is_bold']}  size:{line['size']}  text: {line['text']}")


# ══════════════════════════════════════════════
#  PASS 1 — Extract words + learn font hierarchy
# ══════════════════════════════════════════════

def extract_words(pdf_path):
    all_words  = []
    all_sizes  = []

    doc = fitz.open(pdf_path)
    page_width = 612

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        if(page_num == 1):
            break
        page_width = round(page.rect.width)
        print(f"PAGE WIDTH: {page_width}")

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
                    
    size_counts  = Counter(all_sizes)
   
    major_font_size = {
        "name_font" : size_counts.most_common()[-1][0],
        "body_font" : size_counts.most_common(1)[0][0]
    }
    
    return all_words, major_font_size, page_width
    

def checking_resume_std(all_words, page_width):
    cluster_A = []
    cluster_B = []
    adaptive_threshold = round(page_width/100)*15
    page_third_val = round(page_width/100)*25
    print(f"adaptive threshold {adaptive_threshold}")
    print(f"25% of page {page_third_val}")
    x_positions = sorted(round(w["x0"]) for w in all_words)
    for x0 in x_positions:
        if x0 in range(x_positions[0], adaptive_threshold):
            cluster_A.append(x0)
        else:
            cluster_B.append(x0)
        
    print(f"Lenght of Cluster A: {len(cluster_A)}")
    print(f"Lenght of Cluster B: {len(cluster_B)}")
    
    if(len(cluster_A) >= 5 and len(cluster_B) >= 5):
        
        cluster_A_centroid = sum(cluster_A) / len(cluster_A)
        cluster_B_centroid = sum(cluster_B) / len(cluster_B)
        
        separation_ratio = abs(cluster_B_centroid - cluster_A_centroid) / page_width
         
        print(f"Separation Ratio: {separation_ratio}")
        if(separation_ratio > 0.25):
            return "NON-ATS"
        
    
    return(detect_column_layout(all_words, page_width))
        

def detect_column_layout(all_words, page_width):  # 612 is standard A4 width in points

    # group words by y0 — same y = same line
    print("detection second round")
    line_buckets = defaultdict(list)

    for word in all_words:
        y_key = round(word["y0"], 1)
        line_buckets[y_key].append(word)

    
    multi_column_votes = 0
    total_lines = len(line_buckets)

    for y_key, words in line_buckets.items():

        # sort words left to right by x0
        words_sorted = sorted(words, key=lambda w: w["x0"])
        
        print(f"\nLINE y={y_key}")
        for w in words_sorted:
            print(w["text"], w["x0"], w["x1"])
        
        
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

    print(f"column_ratio = {column_ratio}")

    print(f"\n[COLUMN DETECTION]")
    print(f"  Total lines         : {total_lines}")
    print(f"  Multi column votes  : {multi_column_votes}")
    print(f"  Column ratio        : {round(column_ratio * 100, 2)}%")

    if column_ratio > 0.20:
        print(f"  Result              : ⚠️  MULTI COLUMN — ATS parsing not supported")
        return "NON-ATS"
    else:
        print(f"  Result              : ✅  SINGLE COLUMN — Safe to proceed")
        return "ATS"


# ══════════════════════════════════════════════
#  PASS 2 — Group words into lines
# ══════════════════════════════════════════════

def pass2_build_lines(all_words):

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

    for y_key, words in sorted_lines:
        line_text = " ".join(w["text"] for w in words)
        avg_size  = round(sum(w["size"] for w in words) / len(words), 2)
        is_bold   = any(w["bold"] for w in words)

        # get level from hierarchy
        # use the size of first word in line for level lookup
        first_size = words[0]["size"]
        level_info = hierarchy.get(first_size, {"level": 4, "label": "body"})

        lines.append({
            "text"  : line_text,
            "y0"    : y_key,
            "size"  : avg_size,
            "bold"  : is_bold,
            "level" : level_info["level"],
            "label" : level_info["label"]
        })

    # print(f"\n[PASS 2] {len(lines)} lines built")
    # for line in lines:
    #     print(f"y0:{line['y0']}  level:{line['level']}  label:{line['label']}  bold:{line['bold']}  size:{line['size']}  text: {line['text']}")

    return lines



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
    # if layout == "multi_column":
    #     print("\n  Stopping. Please resubmit resume in single column ATS format.")
    # else:
    #     # Pass 2 — only runs if single column
    #     lines = pass2_build_lines(all_words)

   