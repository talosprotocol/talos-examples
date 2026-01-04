#!/bin/bash
set -e

echo "== Verifying Network Isolation =="

# 1. Verify Agent cannot reach Ollama (Should Fail)
echo "Testing Agent -> Ollama (Should Fail)..."
if docker compose exec devops-agent curl --connect-timeout 2 http://ollama:11434; then
    echo "FAIL: Agent could reach Ollama directly!"
    exit 1
else
    echo "PASS: Agent connect timeout to Ollama."
fi

# 2. Verify Agent cannot reach Cloud (Should Fail)
# Check based on profile
if docker compose ps | grep -q localstack; then
    TARGET="localstack:4566"
else
    TARGET="minio:9000"
fi

echo "Testing Agent -> Cloud ($TARGET) (Should Fail)..."
if docker compose exec devops-agent curl --connect-timeout 2 http://$TARGET; then
    echo "FAIL: Agent could reach Cloud directly!"
    exit 1
else
    echo "PASS: Agent connect timeout to Cloud."
fi

# 3. Verify Talos Node connectivity (Should Succeed)
echo "Testing Talos Node -> Ollama (Should Succeed)..."
if docker compose exec talos-node curl --connect-timeout 5 -f http://ollama:11434; then
    echo "PASS: Talos Node reached Ollama."
else
    echo "FAIL: Talos Node could not reach Ollama!"
    exit 1
fi

echo "== Verification Complete =="
exit 0
