import csv
import os
import shutil
import re

# Define paths
BASE_DIR = r"D:\KT Informatik\ATS project\Final Version"
CSV_PATH = os.path.join(BASE_DIR, "dataset.csv")
RESUME_DIR = os.path.join(BASE_DIR, "data", "real_resumes")

def clean_filename(name):
    """Sanitize the filename to avoid invalid characters."""
    # Remove common markdown symbols just in case
    name = name.replace('*', '').replace('**', '')
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name.strip())

def extract_name_from_resume(text):
    """
    Attempts to extract the candidate name from the resume text.
    Many entries start with "Here's a professional resume for [Name]:"
    """
    # Pattern 1: Intro sentence
    # Matches: "Here's a professional resume for John Doe:" or "Here's a sample resume for Jane Smith,"
    match = re.search(r"Here's a .*? resume for\s+([^,:\.\n]+)", text, re.IGNORECASE)
    if match:
        raw_name = match.group(1).strip()
        # Sometimes the regex might catch too much if the pattern isn't exact, 
        # but the non-greedy .*? and exclusion class [^,:\.\n] helps.
        return raw_name
    
    # Pattern 2: Look at the first few non-empty lines. 
    # Usually the name is the first line or right after the intro.
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Skip the "Here's a..." line/sentence if it didn't match the regex for some reason 
    # (or if we want to look past it for the *title* header which might be the name)
    for line in lines[:5]:  # Check first 5 lines
        if "Here's a" in line or "Here is a " in line:
            continue
        # If the line looks like a name (mostly letters, not too long), use it
        # Heuristic: < 50 chars, doesn't contain "Resume" or "Summary"
        if len(line) < 50 and "resume" not in line.lower() and "professional summary" not in line.lower():
            # Ensure it has some letters
            if any(c.isalpha() for c in line):
                return line
                
    return "Candidate"

def main():
    # 1. Clear the target directory
    if os.path.exists(RESUME_DIR):
        print(f"Cleaning directory: {RESUME_DIR}")
        # Delete all files and subdirs
        for item in os.listdir(RESUME_DIR):
            item_path = os.path.join(RESUME_DIR, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Failed to delete {item_path}. Reason: {e}")
    else:
        print(f"Directory {RESUME_DIR} does not exist. Creating it.")
        os.makedirs(RESUME_DIR)

    # 2. Read CSV and generate files
    print(f"Reading from {CSV_PATH}...")
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    count_by_role = {}
    total_files = 0
    
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                role = row.get('Role', 'Uncategorized').strip()
                resume_content = row.get('Resume', '').strip()
                
                if not resume_content:
                    continue
                
                # Extract Name
                name = extract_name_from_resume(resume_content)
                
                # Update count
                if role not in count_by_role:
                    count_by_role[role] = 1
                else:
                    count_by_role[role] += 1
                
                # Construct filename: Role_Name_Index.txt
                safe_role = clean_filename(role)
                safe_name = clean_filename(name)
                
                # Truncate name if excessively long to prevent filesystem errors
                if len(safe_name) > 40:
                    safe_name = safe_name[:40]
                
                filename = f"{safe_role}_{safe_name}_{count_by_role[role]}.txt"
                file_path = os.path.join(RESUME_DIR, filename)
                
                # Write content to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(resume_content)
                
                total_files += 1
                if total_files % 1000 == 0:
                    print(f"Generated {total_files} resumes...")
                    
        print(f"Successfully generated {total_files} resume files with names in {RESUME_DIR}.")
        
    except Exception as e:
        print(f"An error occurred while processing the CSV: {e}")

if __name__ == "__main__":
    main()
