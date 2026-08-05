import os
import json
from app import app as flask_app

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
