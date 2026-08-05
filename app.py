import os
import io
import uuid
import datetime
import zipfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from database import db
from models import User, ConversionLog

from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from toolkit import pdf_manipulation, office_tools, image_tools, security_tools, translate_tools

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-for-converter'

# Dynamic directory selection for local vs serverless (Appwrite) execution
if os.access('/tmp', os.W_OK) and (os.environ.get('APPWRITE_FUNCTION_ID') or os.name != 'nt'):
    BASE_DIR = '/tmp'
else:
    BASE_DIR = os.path.dirname(__file__)

DB_PATH = os.path.join(BASE_DIR, 'converter.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security constraints
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # 50 MB
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'txt', 'jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'}

csp = {
    'default-src': ['\'self\'', '\'unsafe-inline\'', '\'unsafe-eval\'', 'https://cdn.tailwindcss.com', 'https://fonts.googleapis.com', 'https://fonts.gstatic.com'],
    'script-src': ['\'self\'', '\'unsafe-inline\'', '\'unsafe-eval\'', 'https://cdn.tailwindcss.com'],
    'style-src': ['\'self\'', '\'unsafe-inline\'', 'https://fonts.googleapis.com', 'https://cdn.tailwindcss.com'],
    'font-src': ['\'self\'', 'https://fonts.gstatic.com'],
    'connect-src': ['\'self\'', '*']
}
# Safe extension initialization for serverless execution
try:
    Talisman(app, content_security_policy=csp, force_https=False)
except Exception:
    pass

try:
    csrf = CSRFProtect(app)
except Exception:
    pass

try:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
except Exception:
    limiter = None

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
except Exception:
    pass

try:
    db.init_app(app)
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Database init notice: {e}")



import random

def cleanup_old_files():
    # Only run file cleanup on 10% of requests to eliminate disk I/O latency
    if random.random() > 0.1:
        return
    try:
        now = datetime.datetime.now().timestamp()
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath) and not filename.startswith('.'):
                        if os.stat(filepath).st_mtime < now - 1800:
                            try: os.remove(filepath)
                            except: pass
    except Exception:
        pass

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:5000/sitemap.xml\n", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>http://127.0.0.1:5000/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/upload', methods=['POST'])
def upload_file():
    cleanup_old_files()
    
    unique_batch_id = str(uuid.uuid4())
    output_files = [] # list of tuples: (actual_filename_on_disk, clean_filename_for_zip)
    error_msgs = []
    saved_inputs = []

    ip_addr = request.remote_addr or '127.0.0.1'
    try:
        user = User.query.filter_by(ip_address=ip_addr).first()
        if not user:
            user = User(ip_address=ip_addr)
            db.session.add(user)
            db.session.commit()
    except Exception:
        pass

    # Support JSON Base64 payload for Serverless / Appwrite UTF-8 safety
    if request.is_json or (request.content_type and 'application/json' in request.content_type):
        data = request.get_json() or {}
        conversion_type = data.get('conversion_type')
        files_json = data.get('files', [])
        
        if not conversion_type:
            return jsonify({'error': 'No conversion type selected'}), 400
        if not files_json:
            return jsonify({'error': 'No selected files'}), 400

        for idx, item in enumerate(files_json):
            orig_name = secure_filename(item.get('name', 'file.pdf'))
            if not orig_name or not allowed_file(orig_name):
                error_msgs.append(f"{orig_name} extension not authorized")
                continue
                
            file_data_str = item.get('data', '')
            if ',' in file_data_str:
                _, base64_str = file_data_str.split(',', 1)
            else:
                base64_str = file_data_str
                
            try:
                import base64
                raw_bytes = base64.b64decode(base64_str)
                _, ext = os.path.splitext(orig_name)
                input_filename = f"{unique_batch_id}_{idx}_input{ext}"
                input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
                with open(input_path, 'wb') as f:
                    f.write(raw_bytes)
                saved_inputs.append((input_path, orig_name))
            except Exception as e:
                error_msgs.append(f"Failed decoding {orig_name}: {str(e)}")

        req_form = data
    else:
        files = request.files.getlist('files[]')
        if not files and 'file' in request.files:
            files = [request.files['file']]
            
        if not files or files[0].filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        conversion_type = request.form.get('conversion_type')
        if not conversion_type:
            return jsonify({'error': 'No conversion type selected'}), 400

        for idx, file in enumerate(files):
            if file.filename == '': continue
            if not allowed_file(file.filename):
                error_msgs.append(f"{file.filename} extension not authorized")
                continue
                
            filename = secure_filename(file.filename)
            _, ext = os.path.splitext(filename)
            input_filename = f"{unique_batch_id}_{idx}_input{ext}"
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
            file.save(input_path)
            saved_inputs.append((input_path, filename))

        req_form = request.form

    if not saved_inputs:
        return jsonify({'error': f'No valid files uploaded. Errors: {" | ".join(error_msgs)}'}), 400


    # Many-to-One behaviors:
    if conversion_type == 'merge-pdf':
        paths = [p[0] for p in saved_inputs]
        out_filename = f"{unique_batch_id}_merged.pdf"
        out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_filename)
        success, res = pdf_manipulation.merge_pdfs(paths, out_path)
        if success: output_files.append((out_filename, "Merged_Document.pdf"))
        else: error_msgs.append(res)
        
    elif conversion_type == 'jpg-to-pdf':
        paths = [p[0] for p in saved_inputs]
        out_filename = f"{unique_batch_id}_combined.pdf"
        out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_filename)
        success, res = image_tools.jpg_to_pdf(paths, out_path)
        if success: output_files.append((out_filename, "Combined_Images.pdf"))
        else: error_msgs.append(res)
        
    else:
        # One-to-One or One-to-Many
        for idx, (input_path, orig_filename) in enumerate(saved_inputs):
            original_name, ext = os.path.splitext(orig_filename)
            success = False
            error_msg = ""
            
            if conversion_type == 'pdf-to-word':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.docx"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.pdf_to_docx(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.docx"))
                
            elif conversion_type == 'pdf-to-text':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.txt"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = translate_tools.extract_text_from_pdf(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.txt"))
                
            elif conversion_type == 'image-to-text':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.txt"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = translate_tools.extract_text_from_image(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.txt"))
                
            elif conversion_type == 'compress-pdf':
                lvl = req_form.get('compression_level', 'medium')
                out_name = f"{unique_batch_id}_{idx}_{original_name}_compressed.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = pdf_manipulation.compress_pdf(input_path, out_path, level=lvl)
                if success: output_files.append((out_name, f"{original_name}_compressed.pdf"))
                
            elif conversion_type == 'word-to-pdf':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.docx_to_pdf(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.pdf"))
                
            elif conversion_type == 'compress-image':
                kb = req_form.get('target_kb', '500')
                out_name = f"{unique_batch_id}_{idx}_{original_name}_compressed.jpg"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = image_tools.compress_image_to_kb(input_path, out_path, kb)
                if success: output_files.append((out_name, f"{original_name}_compressed.jpg"))
                
            elif conversion_type == 'convert-image-format':
                fmt = req_form.get('target_format', 'JPG')
                out_name = f"{unique_batch_id}_{idx}_{original_name}.{fmt.lower()}"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = image_tools.convert_image_format(input_path, out_path, fmt)
                if success: output_files.append((out_name, f"{original_name}.{fmt.lower()}"))
                
            # NEW FEATURES
            elif conversion_type == 'split-pdf':
                success, out_list = pdf_manipulation.split_pdf(input_path, app.config['OUTPUT_FOLDER'], f"{unique_batch_id}_{idx}")
                if success:
                    for f_disk, f_zip in out_list:
                        output_files.append((f_disk, f"{original_name}_{f_zip.split('_page_')[1]}"))
                else: res = out_list
                
            elif conversion_type == 'pdf-to-ppt':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.pptx"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.pdf_to_ppt(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.pptx"))
                
            elif conversion_type == 'pdf-to-excel':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.xlsx"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.pdf_to_excel(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.xlsx"))
                
            elif conversion_type == 'ppt-to-pdf':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.ppt_to_pdf(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.pdf"))
                
            elif conversion_type == 'excel-to-pdf':
                out_name = f"{unique_batch_id}_{idx}_{original_name}.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = office_tools.excel_to_pdf(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}.pdf"))
                
            elif conversion_type == 'pdf-to-jpg':
                success, out_list = image_tools.pdf_to_jpg(input_path, app.config['OUTPUT_FOLDER'], f"{unique_batch_id}_{idx}")
                if success:
                    for f_disk, f_zip in out_list:
                        output_files.append((f_disk, f"{original_name}_{f_zip.split('_page_')[1]}"))
                else: res = out_list
                
            elif conversion_type == 'unlock-pdf':
                pwd = req_form.get('password', '')
                out_name = f"{unique_batch_id}_{idx}_{original_name}_unlocked.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = security_tools.unlock_pdf(input_path, out_path, pwd)
                if success: output_files.append((out_name, f"{original_name}_unlocked.pdf"))
                
            elif conversion_type == 'protect-pdf':
                pwd = req_form.get('password', '')
                out_name = f"{unique_batch_id}_{idx}_{original_name}_protected.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = security_tools.protect_pdf(input_path, out_path, pwd)
                if success: output_files.append((out_name, f"{original_name}_protected.pdf"))
                
            elif conversion_type == 'page-numbers':
                out_name = f"{unique_batch_id}_{idx}_{original_name}_numbered.pdf"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = pdf_manipulation.add_page_numbers(input_path, out_path)
                if success: output_files.append((out_name, f"{original_name}_numbered.pdf"))
                
            elif conversion_type == 'translate-pdf':
                lang = request.form.get('target_lang', 'en')
                out_name = f"{unique_batch_id}_{idx}_{original_name}_{lang}.txt"
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_name)
                success, res = translate_tools.translate_pdf_to_txt(input_path, out_path, lang)
                if success: output_files.append((out_name, f"{original_name}_{lang}.txt"))
                
            else:
                return jsonify({'error': 'Invalid conversion type'}), 400

            if not success:
                error_msgs.append(f"{orig_filename}: {res}")
            else:
                log = ConversionLog(user_id=user.id, file_type=ext.replace('.', ''), conversion_type=conversion_type)
                db.session.add(log)
                
    db.session.commit()
    
    if not output_files:
        return jsonify({'error': f'Conversion failed for all files: {" | ".join(error_msgs)}'}), 500

    if len(output_files) > 1:
        zip_filename = f"{unique_batch_id}_converted_files.zip"
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for out_f, arc_name in output_files:
                out_path = os.path.join(app.config['OUTPUT_FOLDER'], out_f)
                zipf.write(out_path, arcname=arc_name)
                # Cleanup individual output parts after zipping
                try: os.remove(out_path)
                except: pass
        final_download = zip_filename
    else:
        final_download = output_files[0][0]

    # Cleanup origin inputs immediately
    for path, _ in saved_inputs:
        try: os.remove(path)
        except: pass

    return jsonify({
        'success': True, 
        'download_url': f'/download/{final_download}',
        'partial_errors': error_msgs if error_msgs else None
    })

@app.route('/download/<filename>')
def download_file(filename):
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
    if os.path.exists(file_path):
        # Read the file to memory, then delete from disk immediately
        with open(file_path, 'rb') as f:
            data = f.read()
        try: os.remove(file_path)
        except: pass
        return_data = io.BytesIO(data)
        return send_file(return_data, download_name=safe_filename, as_attachment=True)
    return "File not found or expired.", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
