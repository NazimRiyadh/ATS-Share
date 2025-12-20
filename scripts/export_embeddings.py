import asyncio
import os
import csv
import json
import re
import asyncpg
from dotenv import load_dotenv
import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings

# Configuration
# Construct DSN manually to ensure reliability and force asyncpg scheme
DSN = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@127.0.0.1:{settings.postgres_port}/{settings.postgres_db}"
OUTPUT_DIR = Path("data/visualization")

def clean_text(text: str) -> str:
    """Clean text for metadata label (remove newlines, limit length)."""
    if not text:
        return "Empty"
    # Replace newlines with spaces
    text = text.replace("\n", " ").replace("\r", "")
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Truncate to avoid huge labels
    return text[:100].strip()

async def export_embeddings():
    print(f"🔌 Connecting to {DSN}...")
    try:
        # Connect to database
        conn = await asyncpg.connect(DSN)
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        print("📊 Fetching vectors from lightrag_vdb_chunks...")
        try:
            # Use discovered table and column names
            rows = await conn.fetch("""
                SELECT content, content_vector::text as vec
                FROM lightrag_vdb_chunks
                LIMIT 10000
            """)
        except Exception as e:
            print(f"⚠️ Query failed: {e}")
            raise e
        
        if not rows:
            print("⚠️ No data found in lightrag_vdb_chunks table.")
            await conn.close()
            return
            
        print(f"✅ Found {len(rows)} chunks. Writing files...")
        
        vectors_path = OUTPUT_DIR / "vectors.tsv"
        metadata_path = OUTPUT_DIR / "metadata.tsv"
        
        with open(vectors_path, "w", encoding="utf-8", newline="") as f_vec, \
             open(metadata_path, "w", encoding="utf-8", newline="") as f_meta:
            
            # TSV writers
            vec_writer = csv.writer(f_vec, delimiter='\t')
            meta_writer = csv.writer(f_meta, delimiter='\t')
            
            # Write header for metadata
            meta_writer.writerow(["Label", "Content_Preview"])
            
            count = 0
            for row in rows:
                content = row['content']
                vec_str = row['vec']
                
                # Parse vector string "[0.1, 0.2, ...]" -> list of floats
                try:
                    # Remove brackets and split
                    vec_clean = vec_str.strip("[]")
                    vec_values = [float(x) for x in vec_clean.split(",")]
                    
                    # Write vector row
                    vec_writer.writerow(vec_values)
                    
                    # Write metadata row
                    label = clean_text(content)
                    meta_writer.writerow([label, content[:200]])
                    
                    count += 1
                except ValueError as e:
                    print(f"⚠️ Error parsing vector for row: {e}")
                    continue
                    
        print(f"🎉 Done! Exported {count} vectors.")
        print(f"📁 Files saved to:\n  - {vectors_path.absolute()}\n  - {metadata_path.absolute()}")
        print("\n🚀 To visualize:")
        print("1. Go to https://projector.tensorflow.org/")
        print("2. Click 'Load'")
        print("3. Upload 'vectors.tsv' (first) and 'metadata.tsv' (second)")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(export_embeddings())
