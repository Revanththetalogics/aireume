from app.backend.services.skill_matcher import match_skills, _expand_skill, _normalize_skill, _extract_skills_from_text, SKILL_ALIASES

# Check flashtext behavior on freertos
print('=== Testing flashtext on freertos ===')
from flashtext import KeywordProcessor
kp = KeywordProcessor(case_sensitive=False)
kp.add_keyword('rtos')
kp.add_keyword('freertos')
kp.add_keyword('free rtos', 'freertos')
kp.add_keyword('free-rtos', 'freertos')

test_text1 = 'I know FreeRTOS and RTOS'
found1 = kp.extract_keywords(test_text1)
print(f'Test 1: {found1}')

test_text2 = 'FreeRTOS is great'
found2 = kp.extract_keywords(test_text2)
print(f'Test 2: {found2}')

test_text3 = 'I use FreeRTOS in my projects'
found3 = kp.extract_keywords(test_text3)
print(f'Test 3: {found3}')

# Try with resume text
resume_with_freertos = 'Experience with FreeRTOS and embedded systems'
found4 = kp.extract_keywords(resume_with_freertos)
print(f'Test 4 (with FreeRTOS): {found4}')

# Now check what the actual skills registry does
print('\n=== Using skills_registry flashtext ===')
test_resume = 'I worked with FreeRTOS kernel'
extracted = _extract_skills_from_text(test_resume)
print(f'Extracted from freertos resume: {extracted}')
print(f'Does extracted contain rtos? {"rtos" in extracted}')
