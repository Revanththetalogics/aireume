from app.backend.services.skill_matcher import match_skills

resume_skills = ['Hadoop', 'Informatica', 'Teradata', 'AWS', 'Java', 'Scala', 'PostgreSQL']
jd_skills = ['railway', 'rtos']

resume_text = '''Senior Big Data Engineer
Experience: Hadoop, Apache Spark, YARN, Hive, Pig
Data Integration: Informatica, Teradata
Cloud: AWS (S3, EC2, Redshift)
Languages: Java, Scala, Python
Database: PostgreSQL'''

print('Scenario 1: Resume text WITHOUT railway/rtos')
result1 = match_skills(resume_skills, jd_skills, jd_text=resume_text)
print('Matched:', result1['matched_skills'])
print('Missing:', result1['missing_skills'])

resume_text_with_terms = '''Senior Big Data Engineer
Experience: Hadoop, Apache Spark, YARN, Hive, Pig
Data Integration: Informatica, Teradata
Cloud: AWS (S3, EC2, Redshift)
Languages: Java, Scala, Python
Database: PostgreSQL

Career Notes: Started in railway infrastructure, now focus on real-time operating system RTOS optimization.'''

print('\nScenario 2: Resume text WITH railway and rtos mentions')
result2 = match_skills(resume_skills, jd_skills, jd_text=resume_text_with_terms)
print('Matched:', result2['matched_skills'])
print('Missing:', result2['missing_skills'])
