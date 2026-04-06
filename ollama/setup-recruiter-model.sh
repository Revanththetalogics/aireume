#!/bin/bash
# Build ARIA - the custom recruiter AI model - inside the ollama container on VPS.
# Run this ONCE after deploying the stack, or whenever the Modelfile changes.
#
# Usage:  bash setup-recruiter-model.sh
#         (run from any directory on the VPS)

set -e

CONTAINER="resume-screener-ollama"
MODEL_NAME="aria-recruiter"

echo "================================================"
echo "  ARIA - Recruiter AI Model Builder"
echo "  ThetaLogics Resume Screener"
echo "================================================"

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "[ERROR] Container '${CONTAINER}' is not running."
  echo "  Start the stack first via Portainer, then re-run this script."
  exit 1
fi

echo ""
echo "[1/4] Ensuring gemma4:e4b base model is available..."
docker exec "$CONTAINER" ollama pull gemma4:e4b
echo "      gemma4:e4b base model ready."

echo ""
echo "[2/4] Copying Modelfile into container..."
docker cp "$(dirname "$0")/Modelfile" "${CONTAINER}:/tmp/Modelfile"
echo "      Modelfile copied."

echo ""
echo "[3/4] Building custom ARIA recruiter model (this takes ~1-2 minutes)..."
docker exec "$CONTAINER" ollama create "$MODEL_NAME" -f /tmp/Modelfile
echo "      Model '${MODEL_NAME}' created successfully."

echo ""
echo "[4/4] Verifying model..."
docker exec "$CONTAINER" ollama list | grep "$MODEL_NAME"

echo ""
echo "================================================"
echo "  Done! ARIA recruiter model is ready."
echo ""
echo "  To use it, set in Portainer stack environment:"
echo "    OLLAMA_MODEL=${MODEL_NAME}"
echo ""
echo "  Or test it directly:"
echo "    docker exec ${CONTAINER} ollama run ${MODEL_NAME} \"hello\""
echo "================================================"
