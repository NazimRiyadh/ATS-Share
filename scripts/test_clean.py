from src.llm_adapter import clean_extraction_output

def test_clean():
    sample_text = """
    ("entity"###Raghu###PERSON###Candidate name)
    ("relationship"###Raghu###HAS_SKILL###Python###Listed in skills section)
    ("relationship"###Description Not Provided)
    ("entity"###InvalidOne)
    ("entity"###HAS_SKILL###UNKNOWN###Bad keyword)
    """
    
    cleaned = clean_extraction_output(sample_text)
    print("Cleaned Output:")
    print(cleaned)
    
    assert "Raghu" in cleaned
    assert "Python" in cleaned
    assert "Description Not Provided" not in cleaned
    assert "InvalidOne" not in cleaned
    assert "HAS_SKILL" not in cleaned
    print("✅ Test Passed!")

if __name__ == "__main__":
    test_clean()
