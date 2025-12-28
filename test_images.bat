@echo off
REM Image Upload Test - Windows Batch
REM Make sure server is running on http://localhost:8000

setlocal enabledelayedexpansion

set "BASE_URL=http://localhost:8000/api"
set "STUDENT_TOKEN=0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
set "BEACON_ID=safe:uuid:403:403"
set "TEST_IMAGE=test_image.jpg"

echo.
echo ╔═══════════════════════════════════════════╗
echo ║  Image Upload Test Suite - Campus Security ║
echo ╚═══════════════════════════════════════════╝
echo.

REM Check if test image exists
if not exist "%TEST_IMAGE%" (
    echo ERROR: test_image.jpg not found!
    echo Run: python gen_image.py
    exit /b 1
)

echo ✓ Test image found: %TEST_IMAGE%
echo.

REM Test 1: Single Image Upload
echo Test 1: Single Image Upload
echo ────────────────────────────
curl.exe -X POST "%BASE_URL%/incidents/report/" ^
  -H "Authorization: Token %STUDENT_TOKEN%" ^
  -F "beacon_id=%BEACON_ID%" ^
  -F "type=Safety Concern" ^
  -F "description=Single image test" ^
  -F "location=Library 3F" ^
  -F "images=@%TEST_IMAGE%"
echo.
echo.

REM Test 2: Multiple Images (3)
echo Test 2: Multiple Images Upload (3 images)
echo ──────────────────────────────────────────
curl.exe -X POST "%BASE_URL%/incidents/report/" ^
  -H "Authorization: Token %STUDENT_TOKEN%" ^
  -F "beacon_id=%BEACON_ID%" ^
  -F "type=Suspicious Activity" ^
  -F "description=Multiple images test" ^
  -F "location=Library 3F" ^
  -F "images=@%TEST_IMAGE%" ^
  -F "images=@%TEST_IMAGE%" ^
  -F "images=@%TEST_IMAGE%"
echo.
echo.

REM Test 3: Text Only (No Images)
echo Test 3: Text Only Report (No Images)
echo ────────────────────────────────────
curl.exe -X POST "%BASE_URL%/incidents/report/" ^
  -H "Authorization: Token %STUDENT_TOKEN%" ^
  -F "beacon_id=%BEACON_ID%" ^
  -F "type=Infrastructure Issue" ^
  -F "description=Text only test no images" ^
  -F "location=Library 3F"
echo.
echo.

REM Test 4: Location-based with Image
echo Test 4: Location-based Report with Image
echo ──────────────────────────────────────────
curl.exe -X POST "%BASE_URL%/incidents/report/" ^
  -H "Authorization: Token %STUDENT_TOKEN%" ^
  -F "type=Suspicious Activity" ^
  -F "description=Location-based with image" ^
  -F "location=Dormitory Building A, Ground Floor" ^
  -F "images=@%TEST_IMAGE%"
echo.
echo.

echo ╔═══════════════════════════════════════════╗
echo ║           Tests Complete!                 ║
echo ╚═══════════════════════════════════════════╝
echo.
echo Next: Check admin panel at http://localhost:8000/admin/
echo - Go to Incidents app
echo - Click on Incident Images
echo - Verify images appear with previews
