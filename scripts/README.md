# Resume AI - Pre-Commit & Test Scripts

This directory contains validation and testing scripts for the Resume AI subscription system and overall codebase quality.

## Available Scripts

### 1. Pre-Commit Validation (`pre-commit-check.ps1`)

Quick validation script to run before committing. This performs syntax checks, file validation, and basic integration tests.

**Usage (Windows PowerShell):**
```powershell
# Basic check
powershell -ExecutionPolicy Bypass -File scripts/pre-commit-check.ps1

# With options
powershell -ExecutionPolicy Bypass -File scripts/pre-commit-check.ps1 -Verbose
```

**What it checks:**
- Python file syntax (subscription.py, analyze.py, db_models.py, etc.)
- Test file syntax
- Migration file existence and order
- Frontend file presence
- API route registration
- Database model patterns
- Integration points (SubscriptionProvider in App.jsx, etc.)

### 2. Full Test Suite (`run-full-tests.bat` / `run-full-tests.sh`)

Comprehensive validation script that runs all checks in sequence. Use this for CI/CD or before major releases.

**Windows (Command Prompt/PowerShell):**
```batch
scripts\run-full-tests.bat
```

**Linux/macOS:**
```bash
bash scripts/run-full-tests.sh
```

**Docker (recommended for full validation):**
```bash
docker-compose exec backend bash /app/scripts/run-full-tests.sh
```

**What it checks:**
- All Python syntax validation
- Import validation for all modules
- Test file validation
- Migration file validation
- Frontend file existence
- Database model patterns
- Integration pattern checks
- Route registration
- 25+ individual validation points

## Git Hook Integration

A pre-commit hook is automatically installed in `.git/hooks/pre-commit`. This runs the validation checks before each commit.

**To bypass the hook (not recommended):**
```bash
git commit --no-verify
```

**To re-enable if disabled:**
```bash
# On Windows
copy scripts\pre-commit-check.ps1 .git\hooks\pre-commit

# On Linux/macOS
ln -sf ../../scripts/run-full-tests.sh .git/hooks/pre-commit
```

## Running in Docker

For the most accurate testing, run the full test suite in the Docker environment:

```bash
# Run syntax and import checks
docker-compose exec backend python -m py_compile app/backend/routes/subscription.py

# Run full test suite
docker-compose exec backend bash /app/scripts/run-full-tests.sh

# Run actual pytest tests
docker-compose exec backend python -m pytest app/backend/tests/test_subscription.py -v
docker-compose exec backend python -m pytest app/backend/tests/test_usage_enforcement.py -v
```

## Manual Validation Commands

### Python Syntax Check
```bash
python -m py_compile app/backend/routes/subscription.py
python -m py_compile app/backend/routes/analyze.py
python -m py_compile app/backend/models/db_models.py
```

### Import Validation
```bash
python -c "from app.backend.routes import subscription"
python -c "from app.backend.models.db_models import SubscriptionPlan, Tenant, UsageLog"
python -c "from app.backend.models.schemas import SubscriptionResponse"
```

### Migration Check
```bash
# Check migration exists
ls alembic/versions/003_subscription_system.py

# Validate syntax
python -m py_compile alembic/versions/003_subscription_system.py

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Frontend Check
```bash
# Check required files exist
ls app/frontend/src/hooks/useSubscription.jsx
ls app/frontend/src/pages/SettingsPage.jsx

# Validate JSX (if Node.js available)
cd app/frontend && npm run lint
```

## Troubleshooting

### PowerShell Execution Policy
If you get execution policy errors on Windows:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### Python Import Errors
If imports fail, ensure you're in the correct directory and Python path is set:
```powershell
$env:PYTHONPATH = "$(Get-Location)"
```

### Missing Test Dependencies
Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
name: Pre-Commit Checks
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Run validation
        run: bash scripts/run-full-tests.sh
```

## Exit Codes

- **0**: All checks passed, ready to commit
- **1**: Some checks failed, fix issues before committing

## Test Coverage

The validation scripts cover:

### Backend
- Python syntax validation (5+ files)
- Import validation (4+ modules)
- Database model validation
- Migration file validation
- Test file validation (2+ test modules)
- API route registration
- Usage enforcement integration

### Frontend
- Required file existence (6+ files)
- JSX component validation
- API integration checks
- React context/provider validation

### Integration
- Backend-frontend API alignment
- Database-API consistency
- Migration-Database model alignment
- Environment variable presence

**Total: 25+ validation points**
