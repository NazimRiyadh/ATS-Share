def robust_split_string_by_multi_markers(content: str, markers: list[str], item_fallback: bool = False):
    """
    Copy of robust splitting function from rag_config.py
    """
    if not markers:
        return [content.strip()]
    
    results = [content]
    for marker in markers:
        new_results = []
        for r in results:
            new_results.extend(r.split(marker))
        results = new_results
    
    results = [r.strip() for r in results if r.strip()]
    
    if not results:
        return []
        
    # Normalize first token to check type (safely ignore quotes/parens)
    first_token = results[0].lower().strip('("')

    # ---------------------------------------------------------
    # SMART FIX 1: Enforce strict field counts (Truncate/Pad)
    # ---------------------------------------------------------
    if "entity" in first_token:
        # Expected: ("entity", Name, Type, Description) -> 4 fields
        if len(results) > 4:
            results = results[:4]  # Truncate extra fields
        elif len(results) < 4:
            missing = 4 - len(results)
            results.extend(["Description not provided"] * missing)
            
    elif "relationship" in first_token:
        # Expected: ("relationship", Src, Rel, Tgt, Desc) -> 5 fields
        if len(results) > 5:
            results = results[:5]  # Truncate extra fields
        elif len(results) < 5:
            missing = 5 - len(results)
            results.extend(["Evidence not provided"] * missing)
            
    return results

def test_split():
    print("Testing ISOLATED robust_split_string_by_multi_markers logic...\n")

    cases = [
        # Normal
        ('("entity"###Name###Type###Desc)', "Normal Entity"),
        ('("relationship"###Src###Rel###Tgt###Desc)', "Normal Relationship"),
        
        # Missing fields (Should be padded)
        ('("entity"###Name###Type)', "Missing Desc"), 
        ('("entity"###Name)', "Missing Type & Desc"),
        
        # Extra fields (Should be truncated)
        ('("entity"###Name###Type###Desc###Extra)', "Extra Entity Field (5 total)"),
        ('("entity"###Name###Type###Desc###Extra###Junk)', "Extra Entity Fields (6 total)"),
        
        ('("relationship"###Src###Rel###Tgt###Desc###Extra)', "Extra Rel Field (6 total)"),
        
        # Malformed
        ('("entity")', "Just Label"),
    ]

    for input_str, desc in cases:
        print(f"Case: {desc}")
        print(f"Input: {input_str}")
        try:
            res = robust_split_string_by_multi_markers(input_str, ["###"])
            print(f"Result: {res} (Len: {len(res)})")
            
            if "entity" in res[0] and len(res) != 4:
                print("❌ FAIL: Entity length != 4")
            elif "relationship" in res[0] and len(res) != 5:
                print("❌ FAIL: Relationship length != 5")
            else:
                print("✅ PASS")
                
        except Exception as e:
            print(f"❌ CRASH: {e}")
        print("-" * 30)

if __name__ == "__main__":
    test_split()
