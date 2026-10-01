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
    'convert-image-format', 'edit-pdf'
]

TOOLS_SEO_DATA = {
    'merge-pdf': {
        'title': 'Merge PDF Online Free - Combine PDF Files | Smart File Converter',
        'desc': 'Merge multiple PDF files into one clean document online for free. Easily arrange page order and combine files with total privacy.'
    },
    'split-pdf': {
        'title': 'Split PDF Online Free - Extract PDF Pages | Smart File Converter',
        'desc': 'Split PDF pages or extract specific page ranges online for free. Separate large PDF documents into individual files in seconds.'
    },
    'compress-pdf': {
        'title': 'Compress PDF Online Free - Reduce PDF File Size | Smart File Converter',
        'desc': 'Compress PDF file size online for free while keeping your text and graphics sharp. Choose custom target KB size or compression level.'
    },
    'pdf-to-word': {
        'title': 'PDF to Word Converter Free Online - Convert PDF to DOCX | Smart File Converter',
        'desc': 'Convert PDF to editable Word (DOCX) free online. Retain original layout, fonts, formatting, tables, and images without software installation.'
    },
    'pdf-to-ppt': {
        'title': 'PDF to PowerPoint Free Online - Convert PDF to PPTX | Smart File Converter',
        'desc': 'Convert PDF documents into editable Microsoft PowerPoint (PPTX) presentation slides free online.'
    },
    'pdf-to-excel': {
        'title': 'PDF to Excel Converter Free Online - Extract Tables to XLSX | Smart File Converter',
        'desc': 'Convert PDF files to editable Excel (XLSX) spreadsheets free online. Extract tables and data cleanly into spreadsheet cells.'
    },
    'word-to-pdf': {
        'title': 'Word to PDF Converter Online Free - 100% Free DOCX to PDF | Smart File Converter',
        'desc': 'Convert Word documents (DOCX & DOC) to PDF online for free. Instant 100% free conversion with perfect layout retention.'
    },
    'ppt-to-pdf': {
        'title': 'PowerPoint to PDF Free Online - Convert PPTX to PDF | Smart File Converter',
        'desc': 'Convert PowerPoint presentations (PPTX & PPT) to PDF online for free. Keep your slide deck presentation-ready on any device.'
    },
    'excel-to-pdf': {
        'title': 'Excel to PDF Converter Online Free - Convert XLSX to PDF | Smart File Converter',
        'desc': 'Convert Excel spreadsheets (XLSX & XLS) to clean PDF tables online for free.'
    },
    'pdf-to-jpg': {
        'title': 'PDF to JPG Converter Free Online - Convert PDF Pages to Images | Smart File Converter',
        'desc': 'Convert PDF pages into high-quality JPG image files online for free.'
    },
    'jpg-to-pdf': {
        'title': 'JPG to PDF Converter Free Online - Convert Images to PDF | Smart File Converter',
        'desc': 'Combine JPG, PNG, WEBP, and BMP images into a single PDF file online for free.'
    },
    'unlock-pdf': {
        'title': 'Unlock PDF Online Free - Remove PDF Password & Restrictions | Smart File Converter',
        'desc': 'Remove passwords and permissions from your protected PDF files online for free.'
    },
    'protect-pdf': {
        'title': 'Protect PDF Online Free - Encrypt PDF with Password | Smart File Converter',
        'desc': 'Secure your PDF files with strong password encryption online for free.'
    },
    'page-numbers': {
        'title': 'Add Page Numbers to PDF Free - Stamp PDF Pages | Smart File Converter',
        'desc': 'Add customized page numbers to PDF documents online for free.'
    },
    'translate-pdf': {
        'title': 'Translate PDF Online Free - PDF Document Translator | Smart File Converter',
        'desc': 'Translate PDF document text into English, Spanish, French, German, Chinese, Arabic, or Hindi online for free.'
    },
    'compress-image': {
        'title': 'Compress Image Online Free - Reduce JPG, PNG & WEBP Size | Smart File Converter',
        'desc': 'Compress JPG, PNG, and WEBP images online to target KB size for free without losing image quality.'
    },
    'convert-image-format': {
        'title': 'Convert Image Format Online Free - JPG, PNG, WEBP | Smart File Converter',
        'desc': 'Convert images between JPG, PNG, WEBP, and BMP formats online for free.'
    },
    'edit-pdf': {
        'title': 'Edit PDF Online Free - Text Editor & PDF Studio | Smart File Converter',
        'desc': 'Edit PDF text directly, replace text, add text annotations, or rotate PDF pages online for free with exact layout retention.'
    }
}

import threading

# Global Flask App cache for lazy loading & container warming
_FLASK_APP = None
_FLASK_APP_LOCK = threading.Lock()

def get_flask_app():
    """
    Thread-safe lazy load of Flask app.
    Ensures container warm-up is 100% safe across threads.
    """
    global _FLASK_APP
    if _FLASK_APP is None:
        with _FLASK_APP_LOCK:
            if _FLASK_APP is None:
                from app import app as flask_app
                flask_app.config['TESTING'] = True
                flask_app.config['WTF_CSRF_ENABLED'] = False
                _FLASK_APP = flask_app
    return _FLASK_APP

# Pre-warm Flask app at module import time (Appwrite container boot)
try:
    threading.Thread(target=get_flask_app, daemon=True).start()
except Exception:
    pass

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
    resp_headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    return status_code_box[0], resp_headers, response_bytes

def main(context):
    """
    Appwrite Function Entry Point
    Provides instant website load & handles API routing
    """
    req = context.req
    res = context.res

    headers = getattr(req, 'headers', {}) or {}
    req_path = getattr(req, 'path', '/') or '/'
    if req_path and req_path != '/':
        path = req_path
    else:
        fwd = headers.get('x-forwarded-uri') or headers.get('x-original-uri') or headers.get('x-rewrite-url') or headers.get('x-appwrite-path')
        path = fwd if fwd else req_path
    
    path = str(path).split('?')[0]
    if not path.startswith('/'):
        path = '/' + path

    method = (getattr(req, 'method', 'GET') or 'GET').upper()
    query = getattr(req, 'query', {}) or {}
    
    context.log(f"Processing: {method} {path}")

    # 301 Permanent Redirect for trailing slash URL normalization
    if path != '/' and path.endswith('/'):
        clean_url = f"https://officialali.dev{path.rstrip('/')}"
        return res.redirect(clean_url, 301)

    # 301 Permanent Redirect for www domain normalization
    host_val = str(headers.get('host') or headers.get('Host') or '').lower()
    if host_val.startswith('www.'):
        clean_url = f"https://officialali.dev{path}"
        return res.redirect(clean_url, 301)

    clean_path = path.strip('/')
    # Route: GET /robots.txt
    if path == '/robots.txt':
        robots_content = """User-agent: *
Allow: /
Allow: /sitemap.xml
Allow: /llms.txt
Allow: /llms-full.txt
Allow: /merge-pdf
Allow: /split-pdf
Allow: /compress-pdf
Allow: /pdf-to-word
Allow: /pdf-to-ppt
Allow: /pdf-to-excel
Allow: /word-to-pdf
Allow: /ppt-to-pdf
Allow: /excel-to-pdf
Allow: /pdf-to-jpg
Allow: /jpg-to-pdf
Allow: /unlock-pdf
Allow: /protect-pdf
Allow: /page-numbers
Allow: /translate-pdf
Allow: /compress-image
Allow: /convert-image-format
Allow: /edit-pdf
Disallow: /download/
Disallow: /upload

User-agent: Googlebot
Allow: /

User-agent: Googlebot-Image
Allow: /

Sitemap: https://officialali.dev/sitemap.xml
"""
        return res.text(robots_content, 200, {
            'content-type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET /llms.txt
    if path == '/llms.txt':
        llms_file = os.path.join(CURRENT_DIR, 'llms.txt')
        if os.path.exists(llms_file):
            with open(llms_file, 'r', encoding='utf-8') as f:
                llms_content = f.read()
            return res.text(llms_content, 200, {
                'content-type': 'text/markdown; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            })

    # Route: GET /llms-full.txt
    if path == '/llms-full.txt':
        llms_full_file = os.path.join(CURRENT_DIR, 'llms-full.txt')
        if os.path.exists(llms_full_file):
            with open(llms_full_file, 'r', encoding='utf-8') as f:
                llms_full_content = f.read()
            return res.text(llms_full_content, 200, {
                'content-type': 'text/markdown; charset=utf-8',
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

    # Route: GET /googleff8c761e6fbde718.html
    if path == '/googleff8c761e6fbde718.html':
        return res.text("google-site-verification: googleff8c761e6fbde718.html", 200, {
            'content-type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })

    # Route: GET / or GET /<tool-name> -> Render HTML Website UI INSTANTLY (< 50ms) without loading heavy python modules
    if method == 'GET' and (path == '/' or path == '/index.html' or clean_path in TOOLS_LIST):
        try:
            # Pre-warm Flask app asynchronously in background for 0-latency first upload
            import threading
            threading.Thread(target=get_flask_app, daemon=True).start()

            html_path = os.path.join(CURRENT_DIR, 'templates', 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Dynamic Canonical, OG URL & Title Injection for 100% Indexable Pages
                if clean_path and clean_path in TOOLS_SEO_DATA:
                    info = TOOLS_SEO_DATA[clean_path]
                    target_url = f"https://officialali.dev/{clean_path}"
                    
                    import re
                    html_content = re.sub(
                        r'<link rel="canonical" id="canonicalUrl"\s+href=".*?"\s*/>',
                        f'<link rel="canonical" id="canonicalUrl" href="{target_url}" />',
                        html_content
                    )
                    html_content = re.sub(
                        r'<meta property="og:url" id="ogUrl"\s+content=".*?"\s*>',
                        f'<meta property="og:url" id="ogUrl" content="{target_url}">',
                        html_content
                    )
                    html_content = re.sub(
                        r'<title id="pageTitle">.*?</title>',
                        f'<title id="pageTitle">{info["title"]}</title>',
                        html_content,
                        flags=re.DOTALL
                    )
                    html_content = re.sub(
                        r'<meta name="description" id="metaDescription"\s+content=".*?"',
                        f'<meta name="description" id="metaDescription" content="{info["desc"]}"',
                        html_content,
                        flags=re.DOTALL
                    )
                    html_content = re.sub(
                        r'<meta property="og:title" id="ogTitle"\s+content=".*?"',
                        f'<meta property="og:title" id="ogTitle" content="{info["title"]}"',
                        html_content,
                        flags=re.DOTALL
                    )
                    html_content = re.sub(
                        r'<meta name="twitter:title" id="twitterTitle"\s+content=".*?"',
                        f'<meta name="twitter:title" id="twitterTitle" content="{info["title"]}"',
                        html_content,
                        flags=re.DOTALL
                    )

                return res.text(html_content, 200, {
                    'content-type': 'text/html; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                })
        except Exception as e:
            context.error(f"Error reading index.html: {str(e)}")

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

        body_data = None
        try:
            body_data = getattr(req, 'body_raw', None)
        except Exception:
            body_data = None

        if not body_data:
            try:
                body_data = getattr(req, 'body_binary', None)
            except Exception:
                body_data = None

        if not body_data:
            try:
                body_data = getattr(req, 'body_text', None)
            except Exception:
                body_data = None

        if not body_data:
            try:
                body_data = getattr(req, 'body', '')
            except Exception:
                body_data = ''

        if isinstance(body_data, dict):
            body_bytes = json.dumps(body_data).encode('utf-8')
        elif isinstance(body_data, str):
            body_bytes = body_data.encode('utf-8', errors='ignore')
        elif isinstance(body_data, bytes):
            body_bytes = body_data
        else:
            body_bytes = str(body_data).encode('utf-8', errors='ignore')

        status_code, resp_headers, response_bytes = dispatch_wsgi(
            flask_app=flask_app,
            path=path,
            method=method,
            headers=headers,
            query=query,
            body_bytes=body_bytes
        )

        # Preserve exact Content-Type header from Flask WSGI response
        if hasattr(res, 'binary') and callable(getattr(res, 'binary')):
            return res.binary(response_bytes, status_code, resp_headers)
        elif hasattr(res, 'bytes') and callable(getattr(res, 'bytes')):
            return res.bytes(response_bytes, status_code, resp_headers)
        else:
            text_response = response_bytes.decode('utf-8', errors='replace')
            return res.text(text_response, status_code, resp_headers)

    except Exception as e:
        err_msg = f"Flask WSGI execution error: {str(e)}\n{traceback.format_exc()}"
        context.error(err_msg)
        return res.json({"error": f"Function execution error: {str(e)}"}, 500)
