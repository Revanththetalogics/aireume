# Deploy Queue System Database Migration
# Run this script on the production server to create queue tables

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Queue System Migration Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "alembic.ini")) {
    Write-Host "Error: alembic.ini not found. Run this from project root." -ForegroundColor Red
    exit 1
}

# Backup database first
Write-Host "Step 1: Creating database backup..." -ForegroundColor Yellow
$backupFile = "backup_queue_migration_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
pg_dump -U aria -d aria_db > $backupFile
Write-Host "✓ Backup created: $backupFile" -ForegroundColor Green
Write-Host ""

# Show current migration status
Write-Host "Step 2: Current migration status..." -ForegroundColor Yellow
alembic current
Write-Host ""

# Run the migration
Write-Host "Step 3: Running migration 008_analysis_queue_system..." -ForegroundColor Yellow
alembic upgrade head
Write-Host "✓ Migration completed" -ForegroundColor Green
Write-Host ""

# Verify tables were created
Write-Host "Step 4: Verifying new tables..." -ForegroundColor Yellow
psql -U aria -d aria_db -c "\dt analysis_*"
Write-Host ""

# Show table counts
Write-Host "Step 5: Checking table structure..." -ForegroundColor Yellow
psql -U aria -d aria_db -c @"
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_name LIKE 'analysis_%'
ORDER BY table_name;
"@
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✓ Queue System Migration Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart backend: docker-compose restart backend"
Write-Host "2. Check logs: docker-compose logs -f backend"
Write-Host "3. Verify queue worker started: Look for 'Queue worker started successfully'"
Write-Host "4. Test queue API: curl http://localhost:8000/api/queue/stats"
Write-Host ""
Write-Host "Rollback if needed:" -ForegroundColor Red
Write-Host "  alembic downgrade -1"
Write-Host "  psql -U aria -d aria_db < $backupFile"
