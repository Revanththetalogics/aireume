# Rebuild and push nginx image with updated configuration
# This fixes the 413 error by including the client_max_body_size 500M setting

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Rebuilding Nginx Image" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$IMAGE_NAME = "revanth2245/resume-nginx"
$TAG = "latest"

# Navigate to nginx directory
Set-Location nginx

Write-Host "Step 1: Building nginx image..." -ForegroundColor Yellow
docker build -t "${IMAGE_NAME}:${TAG}" .
Write-Host "✓ Image built successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Pushing to Docker Hub..." -ForegroundColor Yellow
docker push "${IMAGE_NAME}:${TAG}"
Write-Host "✓ Image pushed successfully" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✓ Nginx Image Rebuilt and Pushed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The updated nginx image includes:" -ForegroundColor Yellow
Write-Host "  - client_max_body_size 500M (global)"
Write-Host "  - client_max_body_size 500M (in /api/ location)"
Write-Host "  - DNS resolver with fallback (127.0.0.11 8.8.8.8)"
Write-Host ""
Write-Host "Next steps on production server:" -ForegroundColor Yellow
Write-Host "1. Watchtower will auto-pull the new image within 60 seconds"
Write-Host "2. Or manually restart: docker-compose -f docker-compose.prod.yml restart nginx"
Write-Host "3. Verify: docker logs resume-screener-nginx"
Write-Host "4. Test batch upload with 50 resumes"
Write-Host ""
