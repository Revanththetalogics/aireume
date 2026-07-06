from app.backend.services.skill_matcher import match_skills, _expand_skill, SKILL_ALIASES, MASTER_SKILLS

# Check if railway and rtos are in MASTER_SKILLS
print('=== MASTER_SKILLS CHECK ===')
print('railway in MASTER_SKILLS:', 'railway' in MASTER_SKILLS)
print('rtos in MASTER_SKILLS:', 'rtos' in MASTER_SKILLS)

# Check aliases
print('\n=== SKILL_ALIASES CHECK ===')
print('railway aliases:', SKILL_ALIASES.get('railway', 'NOT FOUND'))
print('rtos aliases:', SKILL_ALIASES.get('rtos', 'NOT FOUND'))

# Check for reverse aliases
print('\n=== REVERSE ALIAS CHECK ===')
found_railway = False
found_rtos = False
for canonical, aliases in SKILL_ALIASES.items():
    if 'railway' in aliases:
        print(f'Found railway as alias of: {canonical}')
        found_railway = True
    if 'rtos' in aliases:
        print(f'Found rtos as alias of: {canonical}')
        found_rtos = True

if not found_railway:
    print('railway is NOT an alias of any skill')
if not found_rtos:
    print('rtos is NOT an alias of any skill')

# Expand railway and rtos
print('\n=== EXPANSION CHECK ===')
print('expand_skill(railway):', _expand_skill('railway'))
print('expand_skill(rtos):', _expand_skill('rtos'))

# Test fuzzy matching
print('\n=== FUZZY MATCHING TEST ===')
try:
    from rapidfuzz import fuzz
    data_skills = ['hadoop', 'yarn', 'hive', 'pig', 'spark', 'java', 'scala', 'teradata', 'informatica', 'aws', 'postgresql']
    
    print('Testing railway vs data skills:')
    for skill in data_skills:
        ratio = fuzz.token_sort_ratio('railway', skill)
        if ratio >= 70:
            print(f'  railway vs {skill}: {ratio}')
    
    print('Testing rtos vs data skills:')
    for skill in data_skills:
        ratio = fuzz.token_sort_ratio('rtos', skill)
        if ratio >= 70:
            print(f'  rtos vs {skill}: {ratio}')
except Exception as e:
    print(f'Error: {e}')
