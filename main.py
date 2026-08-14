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

TOOLS_SEO_DATA = {
    'merge-pdf': {
        'title': 'Merge PDF Online - Combine PDF Files Free | Smart File Converter',
        'desc': 'Merge multiple PDF files into one combined document online for free. Reorder PDF pages and combine files instantly with 100% privacy.'
    },
    'split-pdf': {
        'title': 'Split PDF Online - Extract Pages from PDF Free | Smart File Converter',
        'desc': 'Split PDF pages or extract page ranges from PDF files online for free. Separate multi-page PDFs into individual PDF documents instantly.'
    },
    'compress-pdf': {
        'title': 'Compress PDF Online - Reduce PDF File Size Free | Smart File Converter',
        'desc': 'Compress PDF file size online for free while maintaining original document quality. Choose compression levels or target KB size.'
    },
    'pdf-to-word': {
        'title': 'PDF to Word Converter - Convert PDF to DOCX Online Free | Smart File Converter',
        'desc': 'Convert PDF to editable Word (.docx) documents online for free. Preserves document layout, fonts, bold/italic formatting, tables, and images.'
    },
    'pdf-to-ppt': {
        'title': 'PDF to PowerPoint Converter - PDF to PPTX Online Free | Smart File Converter',
        'desc': 'Convert PDF documents into editable Microsoft PowerPoint (.pptx) presentation slides online for free. High-quality PDF to PPT converter.'
    },
    'pdf-to-excel': {
        'title': 'PDF to Excel Converter - Extract PDF Tables to XLSX Free | Smart File Converter',
        'desc': 'Convert PDF files into Microsoft Excel (.xlsx) spreadsheets online for free. Extract tables and structured data from PDF into clean Excel cells.'
    },
    'word-to-pdf': {
        'title': 'Word to PDF Converter - Convert DOCX to PDF Online Free | Smart File Converter',
        'desc': 'Convert Microsoft Word (.docx) documents to PDF online for free. Preserve original typography, tables, and document layout.'
    },
    'ppt-to-pdf': {
        'title': 'PowerPoint to PDF Converter - Convert PPTX to PDF Free | Smart File Converter',
        'desc': 'Convert PowerPoint (.pptx) presentations to PDF format online for free. Fast, reliable PPT to PDF document converter.'
    },
    'excel-to-pdf': {
        'title': 'Excel to PDF Converter - Convert XLSX to PDF Online Free | Smart File Converter',
        'desc': 'Convert Excel (.xlsx) spreadsheets into formatted PDF tables online for free. Convert Excel workbooks into PDF documents.'
    },
    'pdf-to-jpg': {
        'title': 'PDF to JPG Converter - Convert PDF Pages to Images Free | Smart File Converter',
        'desc': 'Convert PDF pages into high-resolution JPG images online for free. Save PDF pages as image files instantly.'
    },
    'jpg-to-pdf': {
        'title': 'JPG to PDF Converter - Convert Images to PDF Online Free | Smart File Converter',
        'desc': 'Convert JPG, PNG, WEBP, and BMP images into a single PDF file online for free. Fast image to PDF converter.'
    },
    'unlock-pdf': {
        'title': 'Unlock PDF Online - Remove PDF Password & Restrictions Free | Smart File Converter',
        'desc': 'Unlock password-protected PDF files online for free. Remove owner and user passwords to print, copy, or edit PDFs.'
    },
    'protect-pdf': {
        'title': 'Protect PDF Online - Encrypt PDF with Password Free | Smart File Converter',
        'desc': 'Encrypt PDF files with strong password protection online for free. Prevent unauthorized opening, copying, or printing.'
    },
    'page-numbers': {
        'title': 'Add Page Numbers to PDF - Stamp PDF Pages Free | Smart File Converter',
        'desc': 'Add page numbers to your PDF documents easily online for free. Choose position, font style, and number formatting.'
    },
    'translate-pdf': {
        'title': 'Translate PDF Online - Free PDF Document Translator | Smart File Converter',
        'desc': 'Translate PDF document text into English, Spanish, French, German, Chinese, Arabic, or Hindi online for free.'
    },
    'compress-image': {
        'title': 'Compress Image Online - Reduce JPG & PNG Size Free | Smart File Converter',
        'desc': 'Compress JPG, PNG, and WEBP images online to target KB size for free. Optimize images for faster web page loading.'
    },
    'convert-image-format': {
        'title': 'Convert Image Format - JPG, PNG, WEBP Converter Free | Smart File Converter',
        'desc': 'Convert image files between JPG, PNG, WEBP, and BMP formats online for free. Fast batch image format converter.'
    }
}

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
            html_path = os.path.join(CURRENT_DIR, 'templates', 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Dynamic Canonical, OG URL & Title Injection for 100% Indexable Pages
                if clean_path and clean_path in TOOLS_SEO_DATA:
                    info = TOOLS_SEO_DATA[clean_path]
                    target_url = f"https://officialali.dev/{clean_path}"
                    
                    html_content = html_content.replace(
                        'href="https://officialali.dev/"',
                        f'href="{target_url}"'
                    ).replace(
                        'content="https://officialali.dev/"',
                        f'content="{target_url}"'
                    )
                    
                    if '<title id="pageTitle">' in html_content:
                        import re
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

        if hasattr(res, 'binary') and callable(getattr(res, 'binary')):
            return res.binary(response_bytes, status_code, resp_headers)
        elif hasattr(res, 'send'):
            return res.send(response_bytes, status_code, resp_headers)
        else:
            text_response = response_bytes.decode('utf-8', errors='replace')
            return res.text(text_response, status_code, resp_headers)

    except Exception as e:
        err_msg = f"Flask WSGI execution error: {str(e)}\n{traceback.format_exc()}"
        context.error(err_msg)
        return res.json({"error": f"Function execution error: {str(e)}"}, 500)
