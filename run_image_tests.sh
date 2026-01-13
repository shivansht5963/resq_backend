#!/bin/bash
# Simple script to run local image tests

echo "========================================"
echo "Local Image Upload Test Suite"
echo "========================================"
echo ""

# Run tests with Django test runner
python manage.py test test_image_workflow_local.TestImageUploadLocal -v 2

echo ""
echo "========================================"
echo "Test Complete"
echo "========================================"
