def robust_split_string_by_multi_markers(content: str, markers: list[str], item_fallback: bool = False):
    print(f"DEBUG: Processing content of length {len(content)}")
    print(f"DEBUG: Markers: {markers}")
    
    if not markers:
        return [content.strip()]
    
    results = [content]
    for marker in markers:
        new_results = []
        for r in results:
            new_results.extend(r.split(marker))
        results = new_results
    
    results = [r.strip() for r in results if r.strip()]
    
    print(f"DEBUG: Initial Split Results ({len(results)} items): {results}")
    
    if not results:
        return []

    # Copy of the logic from rag_config.py
    first_token = results[0].lower().strip('("')

    # SMART FIX 1
    if len(results) >= 5 and "entity" in first_token:
        results[0] = results[0].lower().replace("entity", "relationship")
        first_token = "relationship"

    # SMART FIX 2
    if "entity" in first_token:
        if len(results) > 4:
            print("DEBUG: Truncating entity > 4")
            results = results[:4]
        elif len(results) < 4:
            missing = 4 - len(results)
            results.extend(["Description not provided"] * missing)
            
    elif "relationship" in first_token:
        if len(results) > 5:
            print("DEBUG: Truncating relationship > 5")
            results = results[:5]
        elif len(results) < 5:
            missing = 5 - len(results)
            results.extend(["Evidence not provided"] * missing)

    print(f"DEBUG: Final Results: {results}")
    return results

if __name__ == "__main__":
    # Mock Data matching test_lightrag_insert.py
    mock_extraction_output = """
entity###TestCandidate###PERSON###Candidate Name
entity###TestSkill_Python###SKILL###Programming Language
entity###TestSkill_Java###SKILL###Programming Language
relationship###TestCandidate###HAS_SKILL###TestSkill_Python###Known skill
relationship###TestCandidate###HAS_SKILL###TestSkill_Java###Known skill
"""
    markers = ["###"]
    
    print("--- Test 1: Full Block (Simulating bug condition) ---")
    robust_split_string_by_multi_markers(mock_extraction_output, markers)
    
    print("\n--- Test 2: Single Line (Expected usage) ---")
    single_line = "entity###TestCandidate###PERSON###Candidate Name"
    robust_split_string_by_multi_markers(single_line, markers)
