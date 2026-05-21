#!/bin/bash
# Manual database initialization for production
# Run this on your VPS if the backend keeps failing to start

echo "========================================="
echo "ARIA Production DB Initialization"
echo "========================================="
echo ""

# Step 1: Create tables manually
echo "Step 1: Creating database tables..."
docker exec aria-backend-prod python -c "
from app.backend.models.db_models import Base
from app.backend.db.database import engine
print('Creating tables...')
Base.metadata.create_all(bind=engine)
print('Tables created successfully!')
"

if [ $? -eq 0 ]; then
    echo "✅ Tables created successfully"
else
    echo "❌ Failed to create tables"
    exit 1
fi

echo ""
echo "Step 2: Running migrations..."
docker exec aria-backend-prod alembic -c alembic.ini upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

echo ""
echo "Step 3: Restarting backend..."
docker restart aria-backend-prod

echo ""
echo "========================================="
echo "✅ Production backend should now be running!"
echo "========================================="
echo ""
echo "Check logs: docker logs aria-backend-prod --tail 50"
echo "Test health: curl http://localhost:8080/health"
