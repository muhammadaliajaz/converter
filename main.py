import os
import sys

# Ensure current working directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Global Flask App cache for lazy loading
_FLASK_APP = None

def get_flask_app():
    """
    Lazy load Flask app ONLY when API requests (e.g. upload/download) arrive.
    This makes GET / website loading INSTANT (< 50ms).
    """
    global _FLASK_APP
    if _FLASK_APP is None:
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False
        _FLASK_APP = flask_app
    return _FLASK_APP

def main(context):
    """
    Appwrite Function Entry Point
    Provides instant website load & handles API routing
    """
    req = context.req
    res = context.res

    path = getattr(req, 'path', '/') or '/'
    method = (getattr(req, 'method', 'GET') or 'GET').upper()
    headers = getattr(req, 'headers', {}) or {}
    query = getattr(req, 'query', {}) or {}
    
    context.log(f"Processing: {method} {path}")

    # Route: GET / -> Render HTML Website UI INSTANTLY (< 50ms) without loading heavy python modules
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

    # Route: GET /googleff8c761e6fbde718.html
    if path == '/googleff8c761e6fbde718.html':
        return res.text("google-site-verification: googleff8c761e6fbde718.html", 200, {
            'content-type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET /robots.txt
    if path == '/robots.txt':
        return res.text("User-agent: *\nAllow: /\nSitemap: https://officialali.dev/sitemap.xml\n", 200, {
            'content-type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET /sitemap.xml
    if path == '/sitemap.xml':
        base_url = "https://officialali.dev"
        tools_list = [
            '', 'merge-pdf', 'split-pdf', 'compress-pdf', 'pdf-to-word',
            'pdf-to-ppt', 'pdf-to-excel', 'word-to-pdf', 'ppt-to-pdf',
            'excel-to-pdf', 'pdf-to-jpg', 'jpg-to-pdf', 'unlock-pdf',
            'protect-pdf', 'page-numbers', 'translate-pdf', 'compress-image',
            'convert-image-format'
        ]
        
        urls_xml = ""
        for tool_path in tools_list:
            loc_url = base_url if tool_path == '' else f"{base_url}/#{tool_path}"
            priority = "1.0" if tool_path == '' else "0.8"
            urls_xml += f"  <url>\n    <loc>{loc_url}</loc>\n    <changefreq>daily</changefreq>\n    <priority>{priority}</priority>\n  </url>\n"

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}</urlset>"""

        return res.text(xml_content, 200, {
            'content-type': 'application/xml; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET /health
    if path == '/health' or path == '/api/health':
        return res.json({
            "status": "success",
            "message": "Converter app is running on Appwrite Function!",
            "version": "1.0.0"
        })

    # Forward API requests (/upload, /download, etc.) to Flask App
    try:
        import json
        flask_app = get_flask_app()
        
        # Extract content-type before filtering headers
        content_type = 'application/json'
        headers_dict = {}
        if isinstance(headers, dict):
            for k, v in headers.items():
                if k.lower() == 'content-type':
                    content_type = v
                elif k.lower() not in ('host', 'content-length'):
                    headers_dict[k] = v

        body_data = getattr(req, 'body_raw', None)
        if not body_data:
            body_data = getattr(req, 'body_text', None)
        if not body_data:
            body_data = getattr(req, 'body_binary', None)
        if not body_data:
            body_data = getattr(req, 'body', '')

        if isinstance(body_data, dict):
            body_data = json.dumps(body_data).encode('utf-8')
        elif isinstance(body_data, str):
            body_data = body_data.encode('utf-8')

        with flask_app.test_client() as client:
            if method == 'POST':
                rv = client.post(
                    path,
                    data=body_data,
                    content_type=content_type
                )
            else:
                rv = client.get(
                    path,
                    query_string=query
                )
            
            resp_headers = {k: v for k, v in rv.headers if k.lower() != 'content-length'}
            resp_headers['Access-Control-Allow-Origin'] = '*'
            
            raw_response_bytes = rv.get_data()
            text_response = raw_response_bytes.decode('utf-8', errors='replace')
            
            if hasattr(res, 'send'):
                return res.send(text_response, rv.status_code, resp_headers)
            
            return res.text(text_response, rv.status_code, resp_headers)

    except Exception as e:
        context.error(f"Flask execution error: {str(e)}")
        return res.json({"error": f"Function execution error: {str(e)}"}, 500)
