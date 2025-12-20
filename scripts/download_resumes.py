import requests
import csv
import os
import io
import random
from collections import defaultdict

# Direct raw link to the CSV file on Hugging Face
DATASET_URL = "https://huggingface.co/datasets/AzharAli05/Resume-Screening-Dataset/resolve/main/dataset.csv"
# Fallback URL if the first one doesn't exist (common name variation)
FALLBACK_URL = "https://huggingface.co/datasets/AzharAli05/Resume-Screening-Dataset/resolve/main/Resume.csv"

OUTPUT_DIR = "data/real_resumes"

def download_and_process():
    print(f"Downloading dataset...")
    
    response = requests.get(DATASET_URL)
    if response.status_code != 200:
        print(f"Primary URL failed ({response.status_code}). Trying fallback...")
        response = requests.get(FALLBACK_URL)
        if response.status_code != 200:
            print(f"Failed to download dataset. Status: {response.status_code}")
            return

    content = response.content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(content))
    
    # Group by category
    categories = defaultdict(list)
    rows = list(csv_reader)
    
    print(f"Total rows found: {len(rows)}")
    
    # normalize column names
    # Expecting 'Resume_str' or 'Resume' and 'Category'
    resume_key = None
    category_key = None
    
    if rows:
        keys = rows[0].keys()
        print(f"Columns found: {list(keys)}")
        for k in keys:
            k_lower = k.lower()
            if 'resume' in k_lower or 'description' in k_lower:
                resume_key = k
            if 'category' in k_lower or 'role' in k_lower:
                category_key = k
    
    if not resume_key:
        print("Could not identify Resume column.")
        return

    for row in rows:
        cat = row[category_key] if category_key else "Uncategorized"
        text = row[resume_key]
        categories[cat].append(text)
    
    print(f"Found {len(categories)} categories.")
    
    # ensure output dir exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # Select 50 resumes balanced
    selected = []
    
    # Calculate target per category
    target_per_cat = max(1, 50 // len(categories))
    
    for cat, resumes in categories.items():
        # Clean category name for filename
        safe_cat = "".join(c for c in cat if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        
        # Take sample
        sample = resumes[:target_per_cat]
        for i, text in enumerate(sample):
            filename = f"{safe_cat}_{i+1}.txt"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Clean text (sometimes CSVs have artifacts)
            clean_text = text.replace('\\n', '\n').strip()
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(clean_text)
            
            print(f"Saved: {filename}")
            selected.append(filepath)
            
            if len(selected) >= 50:
                break
        if len(selected) >= 50:
            break
            
    print(f"Successfully saved {len(selected)} resumes to {OUTPUT_DIR}")

if __name__ == "__main__":
    download_and_process()
