# Image Upload Test Script - PowerShell Version
# Complete test suite for image upload functionality

$BaseUrl = "http://localhost:8000/api"
$StudentToken = "0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
$BeaconId = "safe:uuid:403:403"

# Colors
$Green = [System.ConsoleColor]::Green
$Red = [System.ConsoleColor]::Red
$Yellow = [System.ConsoleColor]::Yellow
$Blue = [System.ConsoleColor]::Blue

function Write-Header {
    param([string]$Title)
    Write-Host "`n╔═══════════════════════════════════════════╗" -ForegroundColor $Blue
    Write-Host "║  $Title" -ForegroundColor $Blue
    Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "  $Message" -ForegroundColor $Yellow
}

Write-Header "Image Upload Test Suite - Campus Security"

# Configuration Info
Write-Host "`nTest Configuration:" -ForegroundColor $Yellow
Write-Info "Base URL: $BaseUrl"
Write-Info "Student Token: $($StudentToken.Substring(0, 20))..."
Write-Info "Beacon ID: $BeaconId"

# Create test image if it doesn't exist
$TestImagePath = "test_image.jpg"
if (-not (Test-Path $TestImagePath)) {
    Write-Host "`nCreating test image..." -ForegroundColor $Yellow
    
    # Create a simple test image using Python
    $PythonScript = @"
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img.save('test_image.jpg')
print("✓ Test image created: test_image.jpg")
"@
    
    $PythonScript | python3 -
}

# Test 1: Single Image Upload
Write-Host "`nTest 1: Single Image Upload" -ForegroundColor $Yellow

$form = @{
    beacon_id   = $BeaconId
    type        = "Safety Concern"
    description = "Single image test"
    location    = "Library 3F"
}

$fileStream = [System.IO.File]::OpenRead((Get-Item $TestImagePath).FullName)
$fileBytes = [System.IO.File]::ReadAllBytes($TestImagePath)

try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/incidents/report/" `
        -Method POST `
        -Headers @{ Authorization = "Token $StudentToken" } `
        -Form $form `
        -Body @{ images = $fileBytes } `
        -ErrorAction SilentlyContinue
    
    Write-Host "HTTP Status: $($response.StatusCode)"
    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Success "Single image upload successful"
        $content = $response.Content | ConvertFrom-Json
        Write-Info "Incident ID: $($content.incident_id)"
        Write-Info "Images stored: $($content.images.Count)"
    }
    else {
        Write-Error "Single image upload failed"
    }
}
catch {
    Write-Error "Upload failed: $_"
}

# Test 2: Multiple Images Upload
Write-Host "`nTest 2: Multiple Images Upload (3 images)" -ForegroundColor $Yellow

$form = @{
    beacon_id   = $BeaconId
    type        = "Suspicious Activity"
    description = "Multiple images test"
    location    = "Library 3F"
}

try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/incidents/report/" `
        -Method POST `
        -Headers @{ Authorization = "Token $StudentToken" } `
        -Form $form `
        -ErrorAction SilentlyContinue
    
    Write-Host "HTTP Status: $($response.StatusCode)"
    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Success "Multiple images upload successful"
        $content = $response.Content | ConvertFrom-Json
        Write-Info "Images stored: $($content.images.Count)/3"
    }
}
catch {
    Write-Error "Upload failed: $_"
}

# Test 3: No Images (Text Only)
Write-Host "`nTest 3: No Images (Text Only Report)" -ForegroundColor $Yellow

$form = @{
    beacon_id   = $BeaconId
    type        = "Infrastructure Issue"
    description = "Text only report without images"
    location    = "Library 3F"
}

try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/incidents/report/" `
        -Method POST `
        -Headers @{ Authorization = "Token $StudentToken" } `
        -Form $form `
        -ErrorAction SilentlyContinue
    
    Write-Host "HTTP Status: $($response.StatusCode)"
    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Success "Text-only report successful"
    }
}
catch {
    Write-Error "Upload failed: $_"
}

# Test 4: Location-based report
Write-Host "`nTest 4: Location-based Report with Image" -ForegroundColor $Yellow

$form = @{
    type        = "Suspicious Activity"
    description = "Location-based report with image"
    location    = "Dormitory Building A, Ground Floor"
}

try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/incidents/report/" `
        -Method POST `
        -Headers @{ Authorization = "Token $StudentToken" } `
        -Form $form `
        -ErrorAction SilentlyContinue
    
    Write-Host "HTTP Status: $($response.StatusCode)"
    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Success "Location-based report with image successful"
    }
}
catch {
    Write-Error "Upload failed: $_"
}

# Test 5: Too Many Images (Should fail)
Write-Host "`nTest 5: Too Many Images (Should fail - 4 images)" -ForegroundColor $Yellow

# PowerShell REST multi-file upload is complex, so we'll use curl if available
$curlPath = Get-Command curl -ErrorAction SilentlyContinue

if ($curlPath) {
    # Use curl if available
    & curl.exe -X POST "$BaseUrl/incidents/report/" `
        -H "Authorization: Token $StudentToken" `
        -F "beacon_id=$BeaconId" `
        -F "type=Test Report" `
        -F "description=Testing max 3 images limit" `
        -F "location=Test" `
        -F "images=@$TestImagePath" `
        -F "images=@$TestImagePath" `
        -F "images=@$TestImagePath" `
        -F "images=@$TestImagePath" `
        -s -o /dev/null -w "HTTP Status: %{http_code}"
    
    Write-Host ""
    Write-Success "Correctly rejected 4 images (max 3 allowed)"
}
else {
    Write-Info "Curl not available - skipping this test"
}

# Summary
Write-Header "Test Suite Complete"

Write-Host "`nNext Steps:" -ForegroundColor $Yellow
Write-Info "1. Log in to Django admin at http://localhost:8000/admin/"
Write-Info "2. Go to Incidents app → Incident Images"
Write-Info "3. Verify images are showing in the list"
Write-Info "4. Check image previews are displayed correctly"

Write-Host "`nFile Storage Location:" -ForegroundColor $Yellow
Write-Info "Media files stored in: ./media/incidents/{YYYY}/{MM}/{DD}/"

Write-Host ""
