import os
import sys

# Add current directory to Python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Safely attempt to import Flask app
try:
    from app import app as flask_app
    APP_LOADED = True
    APP_ERROR = None
except Exception as e:
    APP_LOADED = False
    APP_ERROR = str(e)

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

    # Check if Flask app module loaded properly
    if not APP_LOADED:
        context.error(f"Module load error: {APP_ERROR}")
        return res.json({
            "status": "error",
            "message": f"App module loading failed: {APP_ERROR}"
        }, 500)

    # Handle health check endpoint
    if path == '/health' or path == '/api/health':
        return res.json({
            "status": "success",
            "message": "Converter app is running on Appwrite Function!",
            "version": "1.0.0"
        })

    # Return status message for Appwrite Function testing
    return res.json({
        "status": "online",
        "service": "File Converter App",
        "method": method,
        "path": path,
        "message": "Appwrite Function is deployed and ready!"
    })
