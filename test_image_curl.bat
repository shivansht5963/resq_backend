@echo off
REM Test image upload to RESQ with Google Cloud Storage using curl.exe
setlocal enabledelayedexpansion

set "BASE_URL=http://localhost:8000/api"
set "TOKEN=0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
set "BEACON_ID=3e3f5319-b90a-4077-86b5-f81ce8e5b0a7"
set "IMAGE_PATH=C:\Users\Shivansh\OneDrive\Desktop\resq_backend\test1.png"

echo ====================================================================
echo Testing Image Upload with Google Cloud Storage
echo ====================================================================
echo.
echo Base URL: %BASE_URL%
echo Image: %IMAGE_PATH%
echo.

if not exist "%IMAGE_PATH%" (
    echo ERROR: Image file not found!
    exit /b 1
)

echo Uploading incident report with image...
echo.

curl.exe -X POST "%BASE_URL%/incidents/report/" ^
  -H "Authorization: Token %TOKEN%" ^
  -F "beacon_id=%BEACON_ID%" ^
  -F "type=Safety Concern" ^
  -F "description=Test incident with Google Cloud Storage image upload" ^
  -F "location=Test Location" ^
  -F "images=@%IMAGE_PATH%"

echo.
echo.
echo ====================================================================
echo Test complete! Check above for success response and image URL
echo ====================================================================
=
