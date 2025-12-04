#!/bin/bash

echo "=================================================="
echo "HEALTH MONITOR - COMPLETE FLOW TEST"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL="https://health-monitor-1-6vo8.onrender.com"
FRONTEND_URL="https://health-monitor-tan.vercel.app"

echo "🔍 Step 1: Check Backend Health"
echo "================================"
VERSION=$(curl -s $BACKEND_URL/ | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])" 2>/dev/null)
if [ -n "$VERSION" ]; then
    echo -e "${GREEN}✓ Backend is running (v$VERSION)${NC}"
else
    echo -e "${RED}✗ Backend is NOT responding${NC}"
    exit 1
fi
echo ""

echo "🧪 Step 2: Test Backend /api/mood Endpoint"
echo "==========================================="
echo "Sending test mood entry with text only..."
echo ""

RESPONSE=$(curl -s -X POST $BACKEND_URL/api/mood \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_user_123",
    "mood_text": "I am feeling overwhelmed with work and very stressed. I have been anxious and having trouble sleeping.",
    "audio_url": null,
    "image_url": null
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool
echo ""

MESSAGE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', 'N/A'))" 2>/dev/null)

echo "Analysis:"
echo "--------"
if echo "$MESSAGE" | grep -q "text-only analysis (AWS Bedrock)"; then
    echo -e "${GREEN}✓ SUCCESS: Using AWS Bedrock Analyzer (TEXT-ONLY MODE)${NC}"
    echo -e "${GREEN}✓ This is the correct flow!${NC}"
elif echo "$MESSAGE" | grep -q "fallback"; then
    echo -e "${RED}✗ FAILURE: Using keyword fallback${NC}"
    echo -e "${YELLOW}⚠ The analyzer is not being called. Check Render logs.${NC}"
elif echo "$MESSAGE" | grep -q "full ML pipeline"; then
    echo -e "${GREEN}✓ SUCCESS: Using full ML pipeline (Preprocessor + Analyzer)${NC}"
    echo -e "${GREEN}✓ This is the best flow!${NC}"
else
    echo -e "${YELLOW}⚠ Unknown response message: $MESSAGE${NC}"
fi
echo ""

echo "📊 Step 3: Expected Data Flow"
echo "=============================="
echo ""
echo "CORRECT FLOW:"
echo "------------"
echo "1. Frontend (Vercel) → User enters mood text"
echo "2. Frontend uploads files to Supabase (if configured)"
echo "3. Frontend sends JSON to Backend:"
echo "   {id, mood_text, audio_url, image_url}"
echo ""
echo "4. Backend (Render) receives request"
echo "5. Backend checks: preprocessor=False, analyzer=True"
echo "6. Backend enters TEXT-ONLY MODE"
echo "7. Backend calls analyzer.analyze(user_id, simple_data)"
echo ""
echo "8. Analyzer (AWS Bedrock) processes:"
echo "   - Fetches user history from Supabase"
echo "   - Constructs prompt with mood text + history"
echo "   - Calls Claude 3.5 Sonnet via AWS Bedrock"
echo "   - Parses mood, stress level from response"
echo "   - Tracks stress history"
echo ""
echo "9. Report.py updates Supabase:"
echo "   - Updates user_reports table"
echo "   - Saves to mood_entries table"
echo "   - Creates stress notifications if needed"
echo ""
echo "10. Backend returns response to Frontend"
echo "11. Frontend displays recommendations to user"
echo ""

echo "🌐 Step 4: Frontend Check"
echo "========================="
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "To verify frontend is working:"
echo "1. Go to: $FRONTEND_URL"
echo "2. Open DevTools (F12) → Console tab"
echo "3. Submit a mood entry"
echo "4. Check console logs for:"
echo "   - '🌐 API URL: $BACKEND_URL'"
echo "   - '✅ Response received: 200'"
echo ""

echo "=================================================="
echo "TEST COMPLETE"
echo "=================================================="

