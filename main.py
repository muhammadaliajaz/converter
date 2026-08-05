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
        host = headers.get('host', 'officialali.dev')
        if '127.0.0.1' in host or 'localhost' in host: host = 'officialali.dev'
        return res.text(f"User-agent: *\nAllow: /\nSitemap: https://{host}/sitemap.xml\n", 200, {
            'content-type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET /sitemap.xml
    if path == '/sitemap.xml':
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://officialali.dev/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://6a72f0b2002ee68ba48d.fra.appwrite.run/</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>'''
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
        flask_app = get_flask_app()
        body_data = getattr(req, 'body_raw', None)
        if body_data is None:
            body_data = getattr(req, 'body_binary', None)
        if body_data is None:
            body_data = getattr(req, 'body', '')

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
            
            raw_response_bytes = rv.get_data()
            
            if hasattr(res, 'binary'):
                return res.binary(raw_response_bytes, rv.status_code, resp_headers)
            
            try:
                text_content = raw_response_bytes.decode('utf-8')
                return res.text(text_content, rv.status_code, resp_headers)
            except UnicodeDecodeError:
                if hasattr(res, 'send'):
                    return res.send(raw_response_bytes, rv.status_code, resp_headers)
                return res.text(raw_response_bytes.decode('latin-1'), rv.status_code, resp_headers)

    except Exception as e:
        context.error(f"Flask execution error: {str(e)}")
        return res.json({"error": f"Function execution error: {str(e)}"}, 500)
