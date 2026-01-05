#!/bin/bash
# Demo script showing streaming chat completions with curl -N

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-sk-dev-default-key-12345}"

echo "🚀 Streaming Chat Completion Demo"
echo "=================================="
echo ""
echo "Request: Tell me a story about space"
echo ""

# Stream the response and parse it
curl -N -s -X POST "$GATEWAY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "echo-model",
    "messages": [{"role": "user", "content": "Tell me a story about space"}],
    "max_tokens": 150,
    "stream": true
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      data="${line#data: }"
      if [[ $data == "[DONE]" ]]; then
        echo ""
        echo "✅ Stream complete!"
        break
      fi
      
      # Extract content using jq if available, otherwise use grep/sed
      if command -v jq &> /dev/null; then
        content=$(echo "$data" | jq -r '.choices[0].delta.content // ""' 2>/dev/null)
      else
        # Fallback: simple grep/sed extraction
        content=$(echo "$data" | grep -o '"content":"[^"]*"' | sed 's/"content":"\(.*\)"/\1/' | head -1)
      fi
      
      if [[ -n "$content" ]]; then
        echo -n "$content"
      fi
    fi
  done

echo ""
echo ""
echo "📊 Try it yourself:"
echo "curl -N -X POST $GATEWAY_URL/v1/chat/completions \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer $API_KEY' \\"
echo "  -d '{\"model\": \"echo-model\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}], \"stream\": true}'"

