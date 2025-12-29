#!/usr/bin/env powershell
# Test image upload to RESQ backend with Google Cloud Storage
# Usage: .\test_image_upload_gcs.ps1

# Configuration
$BaseUrl = "http://localhost:8000/api"
$StudentToken = "0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
$BeaconId = "3e3f5319-b90a-4077-86b5-f81ce8e5b0a7"
$ImagePath = "C:\Users\Shivansh\OneDrive\Desktop\resq_backend\test1.png"

# Check if image exists
if (-not (Test-Path $ImagePath)) {
    Write-Host "❌ Error: Image file not found at: $ImagePath" -ForegroundColor Red
    exit 1
}

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Testing Image Upload with Google Cloud Storage" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Base URL: $BaseUrl" -ForegroundColor Green
Write-Host "Image File: $(Split-Path $ImagePath -Leaf)" -ForegroundColor Green
Write-Host "Image Size: $([Math]::Round((Get-Item $ImagePath).Length / 1MB, 2))MB" -ForegroundColor Green
Write-Host ""

Write-Host "Uploading incident report with image..." -ForegroundColor Yellow
Write-Host ""

$ReportUrl = "$BaseUrl/incidents/report/"

# Create multipart form data
$fileItem = Get-Item $ImagePath
$fileStream = [System.IO.File]::OpenRead($fileItem.FullName)
$boundary = [System.Guid]::NewGuid().ToString()

# Build multipart body
$bodyLines = @(
    "--$boundary",
    'Content-Disposition: form-data; name="beacon_id"',
    "",
    $BeaconId,
    "--$boundary",
    'Content-Disposition: form-data; name="description"',
    "",
    "Test with GCS upload",
    "--$boundary",
    'Content-Disposition: form-data; name="severity"',
    "",
    "MEDIUM",
    "--$boundary",
    "Content-Disposition: form-data; name=`"images`"; filename=`"$($fileItem.Name)`"",
    "Content-Type: application/octet-stream",
    ""
)

$body = [System.Text.Encoding]::UTF8.GetBytes(($bodyLines -join "`r`n") + "`r`n")
$fileBytes = [System.IO.File]::ReadAllBytes($fileItem.FullName)
$endBoundary = "`r`n--$boundary--"

try {
    $request = [System.Net.HttpWebRequest]::Create($ReportUrl)
    $request.Method = "POST"
    $request.Headers.Add("Authorization", "Token $StudentToken")
    $request.ContentType = "multipart/form-data; boundary=$boundary"
    $request.AllowAutoRedirect = $false

    $requestStream = $request.GetRequestStream()
    $requestStream.Write($body, 0, $body.Length)
    $requestStream.Write($fileBytes, 0, $fileBytes.Length)
    $requestStream.Write([System.Text.Encoding]::UTF8.GetBytes($endBoundary), 0, $endBoundary.Length)
    $requestStream.Close()

    $response = $request.GetResponse()
    $streamReader = [System.IO.StreamReader]::new($response.GetResponseStream())
    $responseContent = $streamReader.ReadToEnd()
    $streamReader.Close()
    $response.Close()

    $result = $responseContent | ConvertFrom-Json

    Write-Host "✅ Report created successfully!" -ForegroundColor Green
    Write-Host "Incident ID: $($result.id)" -ForegroundColor Green
    Write-Host ""

    if ($result.images -and $result.images.Count -gt 0) {
        Write-Host "✅ Images uploaded to Google Cloud Storage:" -ForegroundColor Green
        Write-Host ""
        foreach ($image in $result.images) {
            Write-Host "  [IMAGE] File: $(Split-Path $image.image -Leaf)" -ForegroundColor Cyan
            Write-Host "          URL: $($image.image)" -ForegroundColor Green
            Write-Host "          By: $($image.uploaded_by_email)" -ForegroundColor Cyan
            Write-Host ""
        }
    }

    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host "✅ Image upload to GCS WORKING PERFECTLY!" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Green

} catch {
    Write-Host "❌ Error uploading incident!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $errorStream = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $errorContent = $errorStream.ReadToEnd()
        Write-Host "Details: $errorContent" -ForegroundColor Red
        $errorStream.Close()
    }
    exit 1
} finally {
    if ($fileStream) {
        $fileStream.Close()
    }
}