import os
import sys

# Ensure current working directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Safely import Flask application
try:
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for API requests
    APP_LOADED = True
    APP_ERROR = None
except Exception as e:
    flask_app = None
    APP_LOADED = False
    APP_ERROR = str(e)

def main(context):
    """
    Appwrite Function Entry Point
    Routes requests to Flask backend & renders Web UI
    """
    req = context.req
    res = context.res

    path = getattr(req, 'path', '/') or '/'
    method = (getattr(req, 'method', 'GET') or 'GET').upper()
    headers = getattr(req, 'headers', {}) or {}
    query = getattr(req, 'query', {}) or {}
    
    context.log(f"Processing: {method} {path}")

    # Route: GET / -> Render HTML Website UI
    if method == 'GET' and (path == '/' or path == '/index.html'):
        try:
            html_path = os.path.join(CURRENT_DIR, 'templates', 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return res.text(html_content, 200, {
                    'content-type': 'text/html; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                })
        except Exception as e:
            context.error(f"Error reading index.html: {str(e)}")

    # Route: GET /health
    if path == '/health' or path == '/api/health':
        return res.json({
            "status": "success",
            "message": "Converter app is running on Appwrite Function!",
            "app_status": "loaded" if APP_LOADED else f"error: {APP_ERROR}",
            "version": "1.0.0"
        })

    # Forward all API & Upload requests to Flask Application
    if APP_LOADED and flask_app:
        try:
            body_data = getattr(req, 'body_raw', None) or getattr(req, 'body', None) or ''
            
            with flask_app.test_client() as client:
                rv = client.open(
                    path,
                    method=method,
                    headers=headers,
                    query_string=query,
                    data=body_data
                )
                
                resp_headers = {k: v for k, v in rv.headers if k.lower() != 'content-length'}
                resp_headers['Access-Control-Allow-Origin'] = '*'
                
                return res.text(
                    rv.get_data(as_text=True),
                    rv.status_code,
                    resp_headers
                )
        except Exception as e:
            context.error(f"Flask execution error: {str(e)}")
            return res.json({"error": f"Function execution error: {str(e)}"}, 500)

    return res.json({"error": f"App initialization error: {APP_ERROR}"}, 500)
