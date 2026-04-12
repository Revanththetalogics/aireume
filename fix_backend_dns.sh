#!/bin/bash
# Fix Backend DNS Resolution Issue
# Diagnoses and fixes "backend could not be resolved" nginx errors

set -e

echo "=========================================="
echo "Backend DNS Resolution Troubleshooting"
echo "=========================================="
echo ""

# Step 1: Check if backend container is running
echo "Step 1: Checking backend container status..."
if docker ps | grep -q "resume-screener-backend"; then
    echo "✓ Backend container is running"
    docker ps | grep "resume-screener-backend"
else
    echo "✗ Backend container is NOT running!"
    echo ""
    echo "Checking if it exited..."
    docker ps -a | grep "resume-screener-backend" || echo "Container not found at all"
    echo ""
    echo "Checking backend logs for errors..."
    docker logs resume-screener-backend --tail 50
    echo ""
    echo "ACTION REQUIRED: Start the backend container"
    echo "  docker-compose -f docker-compose.prod.yml up -d backend"
    exit 1
fi
echo ""

# Step 2: Check backend health
echo "Step 2: Checking backend health endpoint..."
if docker exec resume-screener-backend curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✓ Backend health check passed"
else
    echo "✗ Backend health check failed"
    echo "Backend logs:"
    docker logs resume-screener-backend --tail 30
    exit 1
fi
echo ""

# Step 3: Check Docker network
echo "Step 3: Checking Docker network configuration..."
BACKEND_NETWORK=$(docker inspect resume-screener-backend --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
NGINX_NETWORK=$(docker inspect resume-screener-nginx --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')

echo "Backend network: $BACKEND_NETWORK"
echo "Nginx network: $NGINX_NETWORK"

if [ "$BACKEND_NETWORK" != "$NGINX_NETWORK" ]; then
    echo "✗ Containers are on DIFFERENT networks!"
    echo "ACTION REQUIRED: Recreate containers on same network"
    echo "  docker-compose -f docker-compose.prod.yml down"
    echo "  docker-compose -f docker-compose.prod.yml up -d"
    exit 1
else
    echo "✓ Containers are on the same network: $BACKEND_NETWORK"
fi
echo ""

# Step 4: Test DNS resolution from nginx container
echo "Step 4: Testing DNS resolution from nginx container..."
if docker exec resume-screener-nginx nslookup backend 2>/dev/null; then
    echo "✓ DNS resolution works from nginx"
else
    echo "✗ DNS resolution FAILED from nginx"
    echo "Trying with getent..."
    docker exec resume-screener-nginx getent hosts backend || echo "getent also failed"
    echo ""
    echo "ACTION REQUIRED: Restart nginx container"
    echo "  docker-compose -f docker-compose.prod.yml restart nginx"
    exit 1
fi
echo ""

# Step 5: Test connectivity from nginx to backend
echo "Step 5: Testing HTTP connectivity from nginx to backend..."
if docker exec resume-screener-nginx wget -qO- http://backend:8000/health 2>/dev/null; then
    echo "✓ Nginx can reach backend via HTTP"
else
    echo "✗ Nginx CANNOT reach backend via HTTP"
    echo "Checking backend IP..."
    BACKEND_IP=$(docker inspect resume-screener-backend --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
    echo "Backend IP: $BACKEND_IP"
    echo "Testing direct IP connection..."
    docker exec resume-screener-nginx wget -qO- http://$BACKEND_IP:8000/health || echo "Direct IP also failed"
    exit 1
fi
echo ""

# Step 6: Check nginx configuration
echo "Step 6: Verifying nginx configuration..."
if docker exec resume-screener-nginx nginx -t 2>&1; then
    echo "✓ Nginx configuration is valid"
else
    echo "✗ Nginx configuration has errors"
    exit 1
fi
echo ""

echo "=========================================="
echo "✓ All checks passed!"
echo "=========================================="
echo ""
echo "If you're still seeing 502 errors, try:"
echo "1. Restart nginx: docker-compose -f docker-compose.prod.yml restart nginx"
echo "2. Check nginx logs: docker logs resume-screener-nginx -f"
echo "3. Check backend logs: docker logs resume-screener-backend -f"
echo ""
echo "Recent nginx errors:"
docker logs resume-screener-nginx --tail 10 | grep -i error || echo "No recent errors"
