import os
import sys

def main(context):
    """
    Appwrite Function Entry Point
    Handles Web UI rendering and API requests
    """
    req = context.req
    res = context.res

    path = getattr(req, 'path', '/') or '/'
    method = getattr(req, 'method', 'GET') or 'GET'
    
    context.log(f"Received request: {method} {path}")

    # Ensure current working directory is in sys.path
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    if CURRENT_DIR not in sys.path:
        sys.path.insert(0, CURRENT_DIR)

    # Route: GET / -> Render the Full HTML Website UI
    if method == 'GET' and (path == '/' or path == '/index.html'):
        try:
            html_path = os.path.join(CURRENT_DIR, 'templates', 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return res.text(html_content, 200, {'content-type': 'text/html; charset=utf-8'})
        except Exception as e:
            context.error(f"Error loading index.html: {str(e)}")

    # Route: GET /health -> Health check
    if path == '/health' or path == '/api/health':
        return res.json({
            "status": "success",
            "message": "Converter app is running on Appwrite Function!",
            "version": "1.0.0"
        })

    # Default API response
    return res.json({
        "status": "online",
        "service": "File Converter App",
        "method": method,
        "path": path,
        "message": "Appwrite Function is deployed and responding successfully!"
    })
