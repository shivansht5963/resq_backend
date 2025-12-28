#!/bin/bash

# Image Upload Test Script for Campus Security Backend

# Configuration
BASE_URL="https://resq-server.onrender.com/api"
# BASE_URL="http://localhost:8000/api"  # Use this for local testing

STUDENT_TOKEN="0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
BEACON_ID="safe:uuid:403:403"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Image Upload Test ===${NC}\n"

# Test 1: Single Image Upload
echo -e "${YELLOW}Test 1: Single Image Upload${NC}"
curl -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Safety Concern" \
  -F "description=Test image upload - single image" \
  -F "location=Library 3F" \
  -F "images=@test_image.jpg" \
  -w "\nStatus Code: %{http_code}\n\n"

# Test 2: Multiple Images Upload (3 images)
echo -e "${YELLOW}Test 2: Multiple Images Upload (3 images)${NC}"
curl -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Suspicious Activity" \
  -F "description=Test image upload - multiple images" \
  -F "location=Library 3F" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -F "images=@test_image.jpg" \
  -w "\nStatus Code: %{http_code}\n\n"

# Test 3: No Images (should still work)
echo -e "${YELLOW}Test 3: No Images (Text Only)${NC}"
curl -X POST "$BASE_URL/incidents/report/" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "type=Infrastructure Issue" \
  -F "description=Test report without images" \
  -F "location=Library 3F" \
  -w "\nStatus Code: %{http_code}\n\n"

echo -e "${GREEN}=== Tests Complete ===${NC}"
echo -e "\n${YELLOW}Notes:${NC}"
echo "- Replace test_image.jpg with actual image path"
echo "- Token must be valid for the specific environment"
echo "- Beacon ID must exist in the database"
echo "- Max 3 images per report"
