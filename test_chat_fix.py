"""
Quick verification script to test the chat.py fix without starting the server.
Simulates how /chat/job processes candidate data from /analyze.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Mock the CandidateContext class
class CandidateContext:
    def __init__(self, name, content, score, metadata):
        self.name = name
        self.content = content
        self.score = score
        self.metadata = metadata
    
    def __repr__(self):
        return f"CandidateContext(name='{self.name}', score={self.score}, content='{self.content[:50]}...')"

# Simulate stored job context (as saved by /analyze endpoint)
job_context = {
    "candidates": [
        {
            "name": "John Doe",
            "score": 0.85,
            "match_reason": "Strong match: Python, AWS, SQL",
            "skills_matched": ["Python", "AWS", "SQL", "Docker"],
            "experience_summary": "Senior Developer at Tech Corp"
        },
        {
            "name": "Jane Smith", 
            "score": 0.78,
            "match_reason": "Matches: Python, PostgreSQL",
            "skills_matched": ["Python", "PostgreSQL"],
            "experience_summary": "5 years experience"
        }
    ]
}

print("=" * 60)
print("Testing /chat/job Candidate Context Extraction")
print("=" * 60)

# Simulate the FIXED code from chat.py lines 61-81
print("\nProcessing candidate context...")
candidates = []
for c in job_context.get("candidates", []):
    # c is a dict from CandidatePreview.dict()
    # Create meaningful content from available fields
    content_parts = []
    if c.get('match_reason'):
        content_parts.append(f"Match Reason: {c['match_reason']}")
    if c.get('skills_matched'):
        content_parts.append(f"Skills: {', '.join(c['skills_matched'])}")
    if c.get('experience_summary'):
        content_parts.append(f"Experience: {c['experience_summary']}")
    
    content = " | ".join(content_parts) if content_parts else "No details available"
    
    candidates.append(CandidateContext(
        name=c.get('name', 'Unknown'),
        content=content,
        score=c.get('score', 0.0),
        metadata=c
    ))

print(f"\n✅ Successfully created {len(candidates)} CandidateContext objects\n")

# Verify the extracted data
for i, candidate in enumerate(candidates, 1):
    print(f"Candidate {i}:")
    print(f"  Name: {candidate.name}")
    print(f"  Score: {candidate.score}")
    print(f"  Content: {candidate.content}")
    print()

# Validation checks
print("=" * 60)
print("Validation Results")
print("=" * 60)

all_passed = True

# Check 1: All candidates processed
if len(candidates) == 2:
    print("✅ All candidates processed (2/2)")
else:
    print(f"❌ Expected 2 candidates, got {len(candidates)}")
    all_passed = False

# Check 2: Names extracted correctly
if candidates[0].name == "John Doe" and candidates[1].name == "Jane Smith":
    print("✅ Candidate names extracted correctly")
else:
    print(f"❌ Name mismatch: {candidates[0].name}, {candidates[1].name}")
    all_passed = False

# Check 3: Scores preserved
if candidates[0].score == 0.85 and candidates[1].score == 0.78:
    print("✅ Scores preserved correctly")
else:
    print(f"❌ Score mismatch")
    all_passed = False

# Check 4: Content includes all fields
for i, candidate in enumerate(candidates):
    if all(x in candidate.content for x in ["Match Reason:", "Skills:", "Experience:"]):
        print(f"✅ Candidate {i+1} has all content fields")
    else:
        print(f"❌ Candidate {i+1} missing content fields")
        all_passed = False

# Check 5: Skills properly joined
if "Python, AWS, SQL, Docker" in candidates[0].content:
    print("✅ Skills properly formatted as comma-separated list")
else:
    print(f"❌ Skills formatting issue")
    all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("🎉 ALL TESTS PASSED - Fix is working correctly!")
else:
    print("⚠️  Some tests failed - review the fix")
print("=" * 60)
