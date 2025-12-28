#!/bin/bash

# Image Upload Test Script - Complete Test Suite
# This script tests image upload functionality and verifies files are saved correctly

BASE_URL="http://localhost:8000/api"
STUDENT_TOKEN="0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
BEACON_ID="safe:uuid:403:403"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Image Upload Test Suite - Campus Security  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}\n"

# Check if image file exists or create a test image
TEST_IMAGE="test_image.jpg"
if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${YELLOW}Creating test image...${NC}"
    # Create a minimal JPEG using Python
    python3 << 'EOF'
from PIL import Image
import os

# Create a simple test image
img = Image.new('RGB', (100, 100), color='red')
img.save('test_image.jpg')
print("✓ Test image created: test_image.jpg")
EOF
fi

echo -e "\n${YELLOW}Test Configuration:${NC}"
echo "  Base URL: $BASE_URL"
echo "  Student Token: ${STUDENT_TOKEN:0:20}..."
echo "  Beacon ID: $BEACON_ID"
echo ""

# Test 1: Single Image Upload
echo -e "${YELLOW}Test 1: Single Image Upload${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Safety Concern" \
  -F "description=Single image test" \
  -F "location=Library 3F" \
  -F "images=@test_image.jpg" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Single image upload successful${NC}"
    INCIDENT_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('incident_id', 'N/A'))" 2>/dev/null)
    IMAGE_COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('images', [])))" 2>/dev/null)
    echo "  Incident ID: $INCIDENT_ID"
    echo "  Images stored: $IMAGE_COUNT"
else
    echo -e "${RED}✗ Single image upload failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi

echo ""

# Test 2: Multiple Images Upload
echo -e "${YELLOW}Test 2: Multiple Images Upload (3 images)${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Suspicious Activity" \
  -F "description=Multiple images test" \
  -F "location=Library 3F" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Multiple images upload successful${NC}"
    IMAGE_COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('images', [])))" 2>/dev/null)
    echo "  Images stored: $IMAGE_COUNT/3"
else
    echo -e "${RED}✗ Multiple images upload failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi

echo ""

# Test 3: No Images (Text Only)
echo -e "${YELLOW}Test 3: No Images (Text Only Report)${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Infrastructure Issue" \
  -F "description=Text only report without images" \
  -F "location=Library 3F" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Text-only report successful${NC}"
else
    echo -e "${RED}✗ Text-only report failed (HTTP $HTTP_CODE)${NC}"
fi

echo ""

# Test 4: Location-based report with image
echo -e "${YELLOW}Test 4: Location-based Report with Image${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "type=Suspicious Activity" \
  -F "description=Location-based report with image" \
  -F "location=Dormitory Building A, Ground Floor" \
  -F "images=@test_image.jpg" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Location-based report with image successful${NC}"
else
    echo -e "${RED}✗ Location-based report with image failed (HTTP $HTTP_CODE)${NC}"
fi

echo ""

# Test 5: Too Many Images (Should fail)
echo -e "${YELLOW}Test 5: Too Many Images (Should fail - 4 images)${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Test Report" \
  -F "description=Testing max 3 images limit" \
  -F "location=Test" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ Correctly rejected 4 images (max 3 allowed)${NC}"
else
    echo -e "${RED}✗ Should have rejected 4 images${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Test Suite Complete             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Log in to Django admin at $BASE_URL/../admin/"
echo "2. Go to Incidents app → Incident Images"
echo "3. Verify images are showing in the list"
echo "4. Check image previews are displayed correctly"
echo ""
echo -e "${YELLOW}File Storage Location:${NC}"
echo "  Media files should be in: ./media/incidents/{YYYY}/{MM}/{DD}/"
echo ""
