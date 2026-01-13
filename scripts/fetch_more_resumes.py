import csv
import os
import re
import hashlib

DATASET_PATH = 'dataset.csv'
RESUME_DIR = 'data/resumes'
TARGET_COUNT = 50

def get_existing_hashes():
    """Get SHA256 hashes of all existing resume files to avoid duplicates."""
    hashes = set()
    if not os.path.exists(RESUME_DIR):
        os.makedirs(RESUME_DIR)
        return hashes
        
    print(f"Scanning existing resumes in {RESUME_DIR}...")
    for filename in os.listdir(RESUME_DIR):
        if filename.endswith('.txt'):
            path = os.path.join(RESUME_DIR, filename)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Normalize: strip whitespace to ensure good matching
                    content_hash = hashlib.sha256(content.strip().encode('utf-8')).hexdigest()
                    hashes.add(content_hash)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    print(f"Found {len(hashes)} unique existing resumes.")
    return hashes

def extract_name(text):
    """Attempt to extract a name for better filenames."""
    # Look for patterns like "Here's a professional resume for [Name]:"
    match = re.search(r"resume for ([A-Z][a-z]+ [A-Z][a-z]+)", text)
    if match:
        return match.group(1).replace(" ", "_")
    
    # Fallback: Look for the first line being a name (often the case in these generated resumes)
    lines = text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if len(line.split()) == 2 and line.replace(" ", "").isalpha():
            return line.replace(" ", "_")
            
    return "Candidate"

def main():
    existing_hashes = get_existing_hashes()
    
    new_count = 0
    
    print(f"Reading {DATASET_PATH}...")
    
    try:
        with open(DATASET_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if new_count >= TARGET_COUNT:
                    break
                    
                resume_text = row.get('Resume', '')
                if not resume_text:
                    continue
                    
                # Clean up the text (remove the "Here's a resume..." prefix if desirable, 
                # but for now we keep it as is to match existing format/logic)
                
                # Check duplicate
                content_hash = hashlib.sha256(resume_text.strip().encode('utf-8')).hexdigest()
                if content_hash in existing_hashes:
                    continue
                
                # Prepare filename
                role = row.get('Role', 'Unknown').replace(" ", "_").replace("/", "_")
                name = extract_name(resume_text)
                
                # Create a safe filename
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name)
                safe_role = re.sub(r'[^a-zA-Z0-9_]', '', role)
                
                filename = f"{safe_role}_{safe_name}_{i}.txt"
                file_path = os.path.join(RESUME_DIR, filename)
                
                # Write file
                with open(file_path, 'w', encoding='utf-8') as out:
                    out.write(resume_text)
                    
                print(f"Created: {filename}")
                existing_hashes.add(content_hash) # Add to set to prevent duplicates within this run
                new_count += 1
                
    except FileNotFoundError:
        print(f"Error: {DATASET_PATH} not found!")
        return

    print(f"\nSuccessfully added {new_count} new resumes to {RESUME_DIR}")

if __name__ == "__main__":
    main()
