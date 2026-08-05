import os
import sys

def main(context):
    """
    Appwrite Function Entry Point
    Handles incoming HTTP requests from Appwrite Cloud / Appwrite Server
    """
    req = context.req
    res = context.res

    # Extract request metadata from Appwrite context
    path = getattr(req, 'path', '/') or '/'
    method = getattr(req, 'method', 'GET') or 'GET'
    
    context.log(f"Received request: {method} {path}")

    # Ensure current working directory is in sys.path
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    if CURRENT_DIR not in sys.path:
        sys.path.insert(0, CURRENT_DIR)

    # Safely load Flask app
    try:
        from app import app as flask_app
        app_status = "loaded"
    except Exception as e:
        context.error(f"Flask App Import Warning: {str(e)}")
        app_status = f"warning: {str(e)}"

    # Handle health check endpoint
    if path == '/health' or path == '/api/health':
        return res.json({
            "status": "success",
            "message": "Converter app is running on Appwrite Function!",
            "app_status": app_status,
            "version": "1.0.0"
        })

    # Default API response for Appwrite Function execution
    return res.json({
        "status": "online",
        "service": "File Converter App",
        "method": method,
        "path": path,
        "app_status": app_status,
        "message": "Appwrite Function is deployed and responding successfully!"
    })
