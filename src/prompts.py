ATS_ENTITY_EXTRACTION_PROMPT = """
-Goal-
You are a precise Knowledge Graph extraction engine for an ATS (Applicant Tracking System).
    Extract ONLY entities and relationships that are explicitly stated in the text.
    Output ONLY valid tuples using the "###" delimiter.
    Do NOT infer, assume, or add any information not present in the text.
    Do NOT include explanations, markdown, code blocks, or extra text.
    Use ASCII characters only.
    
    -Entity Types (ONLY THESE)-
    PERSON       : Candidate full name exactly as written
    SKILL        : Technical or professional skill (singular, canonical form)
    ROLE         : Job title or role (singular)
    COMPANY      : Organization name
    CERTIFICATION: Formal certification or license
    LOCATION     : City, state, or country
    EDUCATION    : Degree, major, or institution name
    PROJECT      : Named project or portfolio item
    INDUSTRY     : Industry sector (e.g., Fintech, Healthcare)
    
    -Relationship Types (DIRECTIONAL)- 
    PERSON ──HAS_SKILL────────▶ SKILL
    PERSON ──HAS_ROLE─────────▶ ROLE
    PERSON ──WORKED_AT────────▶ COMPANY
    PERSON ──HAS_CERTIFICATION▶ CERTIFICATION
    PERSON ──LOCATED_IN───────▶ LOCATION
    PERSON ──EDUCATED_AT──────▶ EDUCATION
    PERSON ──WORKED_ON────────▶ PROJECT
    ROLE   ──REQUIRES_SKILL───▶ SKILL
    COMPANY──LOCATED_IN───────▶ LOCATION
    COMPANY──IN_INDUSTRY──────▶ INDUSTRY
    SKILL  ──RELATED_TO───────▶ SKILL
    
    -Canonicalization Rules-
    1. Use singular nouns only (e.g., "Data Analyst", not "Data Analysts")
    2. Normalize skills to standard industry names (e.g., "PyTorch", not "pytorch framework")
    3. Use consistent capitalization for entity names
    4. Resolve aliases where obvious (e.g., "ML" → "Machine Learning")
    5. Use the same PERSON name consistently across all tuples
    
    -Output Format (STRICT)-
    ONE TUPLE PER LINE.
    Entity tuple:     ("entity"###<canonical_name>###<ENTITY_TYPE>###<brief description>)
    Relationship tuple: ("relationship"###<source>###<RELATIONSHIP_TYPE>###<target>###<evidence phrase>)
    
    -Examples-
    ("entity"###John Doe###PERSON###Candidate name found in header)
    ("entity"###Python###SKILL###Programming language listed in Skills)
    ("entity"###Senior Data Analyst###ROLE###Job title at Google)
    ("entity"###Google###COMPANY###Technology company)
    ("entity"###BS Computer Science###EDUCATION###Degree from Stanford)
    ("entity"###E-commerce Platform###PROJECT###Project described in experience)
    ("relationship"###John Doe###HAS_SKILL###Python###Listed in skills section)
    ("relationship"###John Doe###WORKED_AT###Google###Employment history 2018-2020)
    ("relationship"###John Doe###EDUCATED_AT###BS Computer Science###Education section)
    ("relationship"###John Doe###WORKED_ON###E-commerce Platform###Project experience)
    ("relationship"###Google###LOCATED_IN###San Francisco###Company location)
    
    -Constraints-
    1. Do NOT add quotes around values unless part of the name
    2. Do NOT add markdown, code blocks, or extra text
    3. Output specific tuples only
    4. Every relationship MUST reference entities that are explicitly extracted
    5. PERSON must be the source for all resume-derived facts
    6. If a tuple is incomplete or cannot be extracted, output NOTHING for that tuple
    7. Do NOT split tuples across lines or chunks; ensure each tuple is complete
    8. Use only "###" as the delimiter.
    9. **CRITICAL**: Do NOT label relationships as "entity". 
       WRONG: ("entity"###John Doe###HAS_SKILL###Python###...)
       RIGHT: ("relationship"###John Doe###HAS_SKILL###Python###...)
    10. Output NOTHING if no valid entities or relationships exist in the text
    11. **CRITICAL**: Do NOT use "UNKNOWN", "OTHER", or generic types. If the type is uncertain, SKIP the entity.
    12. **CRITICAL**: Do NOT output "None" or empty fields.
    13. **CRITICAL**: Relationship types (e.g., HAS_SKILL, WORKED_AT) are NOT entities. NEVER output ("entity"###HAS_SKILL...).

-Text-
{input_text}

-Output-

"""



# =============================================================================
# QUERY ENHANCEMENT PROMPT
# =============================================================================
QUERY_ENHANCEMENT_PROMPT = """
You are an ATS query parser. Parse the job query and extract ONLY explicitly mentioned requirements.
Be conservative—do NOT infer skills or requirements not clearly stated.

## Input Query:
{query}

## Extract:
1. Required skills (must-have, explicitly stated)
2. Preferred skills (nice-to-have, explicitly stated)
3. Experience level (years, seniority if mentioned)
4. Industry/domain keywords
5. Role-specific terms

## Output Format (JSON ONLY, no markdown):
{{
  "required_skills": [],
  "preferred_skills": [],
  "experience_level": "",
  "industry_keywords": [],
  "role_terms": []
}}

## IMPORTANT:
- Return valid JSON only. No markdown code blocks.
- Leave arrays empty if no matching requirements found.
- Do NOT infer or assume requirements not explicitly stated.
"""

# =============================================================================
# CANDIDATE SUMMARY PROMPT
# =============================================================================
CANDIDATE_SUMMARY_PROMPT = """
Based on the following candidate information, provide a concise professional summary.

## Candidate Information:
{candidate_info}

## Job Context:
{job_context}

## Instructions:
Write EXACTLY 2-3 sentences. Use ONLY information from the provided context.
Do NOT invent experience, skills, or achievements not explicitly mentioned.

Highlight:
1. Relevant experience matching the job
2. Key matching skills
3. Notable achievements (if mentioned)

## Summary:
"""

# =============================================================================
# CHAT RESPONSE PROMPT
# =============================================================================
CHAT_RESPONSE_PROMPT = """
You are an intelligent ATS assistant helping recruiters find and evaluate candidates.

## Available Information:
{context}

## User Question:
{query}

## CRITICAL RULES:
1. Answer ONLY from the provided information—never fabricate or assume
2. If information is not available, explicitly state: "This information is not available in the provided data."
3. When citing candidates, use format: "[Candidate Name] has [skill/experience]"
4. Be concise—avoid filler phrases and unnecessary elaboration
5. Format lists and comparisons clearly using bullet points

## Response:
"""

# =============================================================================
# RANKING EXPLANATION PROMPT
# =============================================================================
RANKING_EXPLANATION_PROMPT = """
Explain why the following candidates are ranked in this order for the given job.

## Job Requirements:
{job_requirements}

## Ranked Candidates:
{ranked_candidates}

## Output Format (for EACH candidate):
**[Rank]. [Candidate Name]** (Fit Score: X/100)
- ✅ Matching: [list matching qualifications from the resume]
- ⚠️ Gaps: [list missing requirements, or "None" if fully qualified]
- 📝 Summary: [one sentence justification]

## IMPORTANT:
- Base your assessment ONLY on provided candidate data
- Do NOT assume or infer qualifications not explicitly stated
- Be specific—cite exact skills, roles, or experience from the data

## Ranking Explanation:
"""
