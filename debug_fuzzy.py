# Test different fuzzy matching approaches
import re
from difflib import SequenceMatcher

def simple_fuzz_ratio(s1, s2):
    m = SequenceMatcher(None, s1.lower(), s2.lower())
    return m.ratio() * 100

def token_sort_similarity(s1, s2):
    # Simulate token_sort_ratio
    tokens1 = sorted(s1.lower().split())
    tokens2 = sorted(s2.lower().split())
    s1_sorted = ' '.join(tokens1)
    s2_sorted = ' '.join(tokens2)
    m = SequenceMatcher(None, s1_sorted, s2_sorted)
    return m.ratio() * 100

data_skills = ['hadoop', 'yarn', 'hive', 'pig', 'spark', 'java', 'scala', 'teradata', 'informatica', 'aws', 'postgresql']

print('Testing railway with different fuzzy approaches:')
for skill in data_skills:
    ratio1 = simple_fuzz_ratio('railway', skill)
    ratio2 = token_sort_similarity('railway', skill)
    if ratio1 >= 70 or ratio2 >= 70:
        print(f'  railway vs {skill}: simple={ratio1:.1f}, token_sort={ratio2:.1f}')

print('Testing rtos with different fuzzy approaches:')
for skill in data_skills:
    ratio1 = simple_fuzz_ratio('rtos', skill)
    ratio2 = token_sort_similarity('rtos', skill)
    if ratio1 >= 70 or ratio2 >= 70:
        print(f'  rtos vs {skill}: simple={ratio1:.1f}, token_sort={ratio2:.1f}')

print('Testing substring matching:')
all_skills = data_skills + ['embedded linux', 'freertos', 'zephyr', 'vxworks', 'embedded']
for skill in all_skills:
    if 'railway' in skill or skill in 'railway':
        print(f'  railway matches: {skill}')
    if 'rtos' in skill or skill in 'rtos':
        print(f'  rtos matches: {skill}')
