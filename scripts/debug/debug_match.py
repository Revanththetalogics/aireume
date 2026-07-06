from app.backend.services.skill_matcher import match_skills, _expand_skill, _normalize_skill, SKILL_ALIASES

candidate_skills = ['Hadoop', 'Informatica', 'Teradata', 'AWS', 'Java', 'Scala', 'PostgreSQL']
jd_skills = ['railway', 'rtos']

print('=== SIMULATING MATCH_SKILLS ===')
print('Candidate skills:', candidate_skills)
print('JD required skills:', jd_skills)

cand_normalized = []
for s in candidate_skills:
    expanded = _expand_skill(s)
    cand_normalized.extend(expanded)
    print('Expanding', s, '->', expanded)

cand_set = set(cand_normalized)
print('Candidate set:', cand_set)

print('=== TESTING EACH JD SKILL ===')
for req in jd_skills:
    print('\n--- Testing:', req, '---')
    req_variants = _expand_skill(req)
    print('Variants:', req_variants)
    
    found = False
    if any(v in cand_set for v in req_variants):
        print('  FOUND via exact/alias match')
        found = True
    
    if not found:
        req_norm = _normalize_skill(req)
        print('  Normalized requirement:', req_norm)
        print('  Checking substring matching:')
        for c in cand_set:
            if req_norm in c or c in req_norm:
                print('    MATCH FOUND: req_norm=\"' + req_norm + '\" in/contains c=\"' + c + '\"')
                found = True
                break
        if not found:
            print('  No substring match found')
    
    result = 'MATCHED' if found else 'MISSING'
    print('  Result:', result)
