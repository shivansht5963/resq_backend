import os
import django
from django.conf import settings
from django.http import HttpResponse

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')

# Configure Django settings
if not settings.configured:
    django.setup()

from django.core.wsgi import get_wsgi_application
from django.http import HttpRequest

app = get_wsgi_application()

def handler(event, context):
    """Netlify Functions handler for Django WSGI"""
    
    # Create a mock environ dict for the WSGI application
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'SCRIPT_NAME': '',
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('queryStringParameters', ''),
        'CONTENT_TYPE': event.get('headers', {}).get('Content-Type', ''),
        'CONTENT_LENGTH': event.get('headers', {}).get('Content-Length', ''),
        'SERVER_NAME': event.get('headers', {}).get('Host', 'localhost'),
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': None,
        'wsgi.errors': None,
        'wsgi.multithread': True,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }
    
    # Add headers to environ
    for key, value in event.get('headers', {}).items():
        key = key.upper().replace('-', '_')
        if key not in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
            key = f'HTTP_{key}'
        environ[key] = value
    
    # Handle body
    body = event.get('body', '')
    
    # Create response
    status = None
    response_headers = []
    
    def start_response(status_str, headers):
        nonlocal status, response_headers
        status = int(status_str.split()[0])
        response_headers = headers
    
    # Call WSGI app
    response = app(environ, start_response)
    
    # Get response body
    body_parts = []
    for part in response:
        if isinstance(part, bytes):
            body_parts.append(part.decode('utf-8'))
        else:
            body_parts.append(part)
    
    body_content = ''.join(body_parts)
    
    # Convert headers to dict
    headers_dict = {k: v for k, v in response_headers}
    
    return {
        'statusCode': status or 200,
        'headers': headers_dict,
        'body': body_content
    }
