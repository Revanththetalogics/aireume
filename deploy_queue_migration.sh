#!/bin/bash
# Deploy Queue System Database Migration
# Run this script on the production server to create queue tables

set -e  # Exit on error

echo "=========================================="
echo "Queue System Migration Deployment"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "alembic.ini" ]; then
    echo "Error: alembic.ini not found. Run this from project root."
    exit 1
fi

# Backup database first
echo "Step 1: Creating database backup..."
BACKUP_FILE="backup_queue_migration_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -U aria -d aria_db > "$BACKUP_FILE"
echo "✓ Backup created: $BACKUP_FILE"
echo ""

# Show current migration status
echo "Step 2: Current migration status..."
alembic current
echo ""

# Run the migration
echo "Step 3: Running migration 008_analysis_queue_system..."
alembic upgrade head
echo "✓ Migration completed"
echo ""

# Verify tables were created
echo "Step 4: Verifying new tables..."
psql -U aria -d aria_db -c "\dt analysis_*"
echo ""

# Show table counts
echo "Step 5: Checking table structure..."
psql -U aria -d aria_db -c "
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_name LIKE 'analysis_%'
ORDER BY table_name;
"
echo ""

echo "=========================================="
echo "✓ Queue System Migration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart backend: docker-compose restart backend"
echo "2. Check logs: docker-compose logs -f backend"
echo "3. Verify queue worker started: Look for 'Queue worker started successfully'"
echo "4. Test queue API: curl http://localhost:8000/api/queue/stats"
echo ""
echo "Rollback if needed:"
echo "  alembic downgrade -1"
echo "  psql -U aria -d aria_db < $BACKUP_FILE"
