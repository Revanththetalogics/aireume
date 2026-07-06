# Test regex fallback behavior
import re

MASTER_SKILLS = ['railway', 'rtos', 'hadoop', 'java']

text_lower = 'I work with railway company data infrastructure and rtos systems'.lower()

# This is what the code does
found_regex = [s for s in MASTER_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', text_lower)]
print('Regex fallback (with word boundaries):', found_regex)

# Without word boundaries (what flashtext might do)
found_no_boundary = [s for s in MASTER_SKILLS if re.search(re.escape(s), text_lower)]
print('Simple substring match (no boundaries):', found_no_boundary)

# Test on various texts
test_cases = [
    'railway company data infrastructure',
    'Real-time operating system knowledge',
    'FreeRTOS kernel code',
    'RTOs is not a skill'
]

for test_text in test_cases:
    found = [s for s in MASTER_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', test_text.lower())]
    print(f'Text: \"{test_text}\" -> Found: {found}')
