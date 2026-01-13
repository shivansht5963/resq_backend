@echo off
REM Windows batch file to run local image tests

echo ========================================
echo Local Image Upload Test Suite
echo ========================================
echo.

REM Run tests with Django test runner
python manage.py test test_image_workflow_local.TestImageUploadLocal -v 2

echo.
echo ========================================
echo Test Complete
echo ========================================
pause
