import os
import sys
import io
import json
import traceback

# Ensure current working directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from datetime import datetime

# Known tools list for clean URL routing
TOOLS_LIST = [
    'merge-pdf', 'split-pdf', 'compress-pdf', 'pdf-to-word',
    'pdf-to-ppt', 'pdf-to-excel', 'word-to-pdf', 'ppt-to-pdf',
    'excel-to-pdf', 'pdf-to-jpg', 'jpg-to-pdf', 'unlock-pdf',
    'protect-pdf', 'page-numbers', 'translate-pdf', 'compress-image',
    'convert-image-format'
]

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

def dispatch_wsgi(flask_app, path, method, headers, query, body_bytes):
    """
    Native PEP 3333 WSGI Dispatcher
    Dispatches Appwrite HTTP request directly to Flask WSGI app without test_client state bugs.
    """
    query_str = ""
    if isinstance(query, dict):
        query_str = '&'.join([f"{k}={v}" for k, v in query.items()])
    elif isinstance(query, str):
        query_str = query

    host_header = 'officialali.dev'
    if isinstance(headers, dict):
        host_header = headers.get('host') or headers.get('Host') or 'officialali.dev'
    server_name = host_header.split(':')[0]

    environ = {
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'PATH_INFO': path,
        'QUERY_STRING': query_str,
        'SERVER_NAME': server_name,
        'SERVER_PORT': '443',
        'HTTP_HOST': host_header,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': io.BytesIO(body_bytes),
        'wsgi.errors': io.StringIO(),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'CONTENT_LENGTH': str(len(body_bytes)),
    }

    if isinstance(headers, dict):
        for k, v in headers.items():
            k_upper = k.upper().replace('-', '_')
            if k_upper == 'CONTENT_TYPE':
                environ['CONTENT_TYPE'] = str(v)
            elif k_upper == 'CONTENT_LENGTH':
                environ['CONTENT_LENGTH'] = str(v)
            elif k_upper != 'HOST':
                environ[f'HTTP_{k_upper}'] = str(v)

    if 'CONTENT_TYPE' not in environ:
        environ['CONTENT_TYPE'] = 'application/json'

    status_code_box = [200]
    headers_box = []

    def start_response(status, response_headers, exc_info=None):
        try:
            status_code_box[0] = int(status.split()[0])
        except Exception:
            status_code_box[0] = 200
        headers_box.extend(response_headers)

    response_chunks = flask_app(environ, start_response)
    response_bytes = b''.join(response_chunks)
    
    resp_headers = {k: v for k, v in headers_box if k.lower() != 'content-length'}
    resp_headers['Access-Control-Allow-Origin'] = '*'

    return status_code_box[0], resp_headers, response_bytes

def main(context):
    """
    Appwrite Function Entry Point
    Provides instant website load & handles API routing
    """
    req = context.req
    res = context.res

    path = getattr(req, 'path', '/') or '/'
    if not path.startswith('/'):
        path = '/' + path
    method = (getattr(req, 'method', 'GET') or 'GET').upper()
    headers = getattr(req, 'headers', {}) or {}
    query = getattr(req, 'query', {}) or {}
    
    context.log(f"Processing: {method} {path}")

    clean_path = path.strip('/')
    # Route: GET / or GET /<tool-name> -> Render HTML Website UI INSTANTLY (< 50ms) without loading heavy python modules
    if method == 'GET' and (path == '/' or path == '/index.html' or clean_path in TOOLS_LIST):
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
        sitemap_routes = [''] + TOOLS_LIST
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        urls_xml = ""
        for tool_path in sitemap_routes:
            if tool_path == '':
                loc_url = f"{base_url}/"
                priority = "1.0"
            else:
                loc_url = f"{base_url}/{tool_path}"
                priority = "0.8"
            urls_xml += f"  <url>\n    <loc>{loc_url}</loc>\n    <lastmod>{today_date}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>{priority}</priority>\n  </url>\n"

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

    # Forward API requests (/upload, /download, etc.) to Flask App via native WSGI
    try:
        flask_app = get_flask_app()

        body_data = getattr(req, 'body_raw', None)
        if not body_data:
            body_data = getattr(req, 'body_text', None)
        if not body_data:
            body_data = getattr(req, 'body_binary', None)
        if not body_data:
            body_data = getattr(req, 'body', '')

        if isinstance(body_data, dict):
            body_bytes = json.dumps(body_data).encode('utf-8')
        elif isinstance(body_data, str):
            body_bytes = body_data.encode('utf-8')
        elif isinstance(body_data, bytes):
            body_bytes = body_data
        else:
            body_bytes = str(body_data).encode('utf-8')

        status_code, resp_headers, response_bytes = dispatch_wsgi(
            flask_app=flask_app,
            path=path,
            method=method,
            headers=headers,
            query=query,
            body_bytes=body_bytes
        )

        text_response = response_bytes.decode('utf-8', errors='replace')
        
        if hasattr(res, 'send'):
            return res.send(text_response, status_code, resp_headers)
        
        return res.text(text_response, status_code, resp_headers)

    except Exception as e:
        err_msg = f"Flask WSGI execution error: {str(e)}\n{traceback.format_exc()}"
        context.error(err_msg)
        return res.json({"error": f"Function execution error: {str(e)}"}, 500)
