from app.backend.services.skill_matcher import match_skills, _expand_skill, _normalize_skill, _extract_skills_from_text

# Test the flashtext extraction on a resume that might contain embedded systems text

resume_text = '''
Senior Big Data Engineer with 8 years of experience in ETL and data processing.

TECHNICAL SKILLS:
Hadoop, Spark, YARN, Hive, Pig, Teradata, Informatica, AWS (S3, EC2, Redshift), Java, Scala, Python, PostgreSQL, Linux

EXPERIENCE:
Led migration of 200TB data warehouse from on-premise Teradata to AWS Redshift using Apache Spark and YARN for orchestration.
Strong experience with railway company data pipelines... well-known railway infrastructure...
Experience with real-time operating system considerations for high-performance computing scenarios.
'''

print('=== EXTRACTING SKILLS FROM RESUME TEXT ===')
extracted = _extract_skills_from_text(resume_text)
print('Extracted skills from resume:', extracted)

# Now check if railway or rtos appear
print('\nChecking if railway/rtos in extracted:', 'railway' in extracted, 'rtos' in extracted)

# Check substring matching
print('\nSubstring check in resume text:')
resume_lower = resume_text.lower()
print('railway in resume:', 'railway' in resume_lower)
print('rtos in resume:', 'rtos' in resume_lower)

# Now simulate match_skills with jd_text parameter
print('\n=== SIMULATING MATCH_SKILLS WITH JD_TEXT ===')
candidate_skills = ['Hadoop', 'Informatica', 'Teradata', 'AWS', 'Java', 'Scala', 'PostgreSQL']
jd_skills = ['railway', 'rtos']
jd_text = resume_text  # This is the resume being scanned

result = match_skills(candidate_skills, jd_skills, jd_text=jd_text)
print('Match result:')
print('  Matched skills:', result['matched_skills'])
print('  Missing skills:', result['missing_skills'])
