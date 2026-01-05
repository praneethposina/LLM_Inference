#!/bin/bash
# Simple test script for the OpenAI-compatible API

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-sk-dev-default-key-12345}"

echo "Testing Gateway API at $GATEWAY_URL"
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s "$GATEWAY_URL/health" | jq .
echo ""

# Test models endpoint
echo "2. Testing models endpoint..."
curl -s "$GATEWAY_URL/v1/models" | jq .
echo ""

# Test non-streaming chat completion
echo "3. Testing non-streaming chat completion..."
curl -s -X POST "$GATEWAY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "max_tokens": 50,
    "stream": false
  }' | jq .
echo ""

# Test streaming chat completion
echo "4. Testing streaming chat completion..."
curl -s -N -X POST "$GATEWAY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "max_tokens": 100,
    "stream": true
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      data="${line#data: }"
      if [[ $data != "[DONE]" ]]; then
        echo "$data" | jq -r '.choices[0].delta.content // ""' | tr -d '\n'
      fi
    fi
  done
echo ""
echo ""

echo "✅ All tests completed!"

