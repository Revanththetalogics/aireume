from app.backend.services.skill_matcher import match_skills, _expand_skill, _normalize_skill, _extract_skills_from_text, SKILL_ALIASES

# Check RTOS more carefully
print('=== RTOS INVESTIGATION ===')
print('rtos in MASTER_SKILLS (via line 91):', 'rtos' in open('app/backend/services/skill_matcher.py').read())

# Check flashtext behavior
resume_text_with_rtos = '''
Real-time Operating System (RTOS) knowledge
Experience with FreeRTOS for embedded systems
Real-time kernel implementation
'''

print('Testing with RTOS mentions:')
extracted = _extract_skills_from_text(resume_text_with_rtos)
print('Extracted:', extracted)

# Test flashtext on freertos
print('\n=== Testing flashtext on freertos ===')
from flashtext import KeywordProcessor
kp = KeywordProcessor(case_sensitive=False)
kp.add_keyword('rtos')
kp.add_keyword('freertos')
kp.add_keyword('free rtos', 'freertos')
kp.add_keyword('free-rtos', 'freertos')

test_text = 'I know FreeRTOS and RTOS'
found = kp.extract_keywords(test_text)
print(f'Keywords found in \"{test_text}\": {found}')

test_text2 = 'FreeRTOS is great'
found2 = kp.extract_keywords(test_text2)
print(f'Keywords found in \"{test_text2}\": {found2}')

# The key issue: flashtext extracts RTOS as a substring match of FreeRTOS
test_text3 = 'I use FreeRTOS in my projects'
found3 = kp.extract_keywords(test_text3)
print(f'Keywords found in \"{test_text3}\": {found3}')
