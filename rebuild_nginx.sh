#!/bin/bash
# Rebuild and push nginx image with updated configuration
# This fixes the 413 error by including the client_max_body_size 500M setting

set -e

echo "=========================================="
echo "Rebuilding Nginx Image"
echo "=========================================="
echo ""

# Configuration
IMAGE_NAME="revanth2245/resume-nginx"
TAG="latest"

# Navigate to nginx directory
cd nginx

echo "Step 1: Building nginx image..."
docker build -t ${IMAGE_NAME}:${TAG} .
echo "✓ Image built successfully"
echo ""

echo "Step 2: Pushing to Docker Hub..."
docker push ${IMAGE_NAME}:${TAG}
echo "✓ Image pushed successfully"
echo ""

echo "=========================================="
echo "✓ Nginx Image Rebuilt and Pushed!"
echo "=========================================="
echo ""
echo "The updated nginx image includes:"
echo "  - client_max_body_size 500M (global)"
echo "  - client_max_body_size 500M (in /api/ location)"
echo "  - DNS resolver with fallback (127.0.0.11 8.8.8.8)"
echo ""
echo "Next steps on production server:"
echo "1. Watchtower will auto-pull the new image within 60 seconds"
echo "2. Or manually restart: docker-compose -f docker-compose.prod.yml restart nginx"
echo "3. Verify: docker logs resume-screener-nginx"
echo "4. Test batch upload with 50 resumes"
echo ""
