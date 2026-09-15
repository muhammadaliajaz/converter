import os
import io
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import fitz
from reportlab.pdfgen import canvas
from PIL import Image

def merge_pdfs(input_paths, output_path):
    try:
        merger = PdfMerger()
        for path in input_paths:
            merger.append(path)
        merger.write(output_path)
        merger.close()
        return True, output_path
    except Exception as e:
        return False, str(e)

def split_pdf(input_path, output_dir, unique_batch_id):
    try:
        reader = PdfReader(input_path)
        output_files = []
        for i in range(len(reader.pages)):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            out_name = f"{unique_batch_id}_page_{i+1}.pdf"
            out_path = os.path.join(output_dir, out_name)
            with open(out_path, "wb") as f:
                writer.write(f)
            output_files.append((out_name, out_name))
        return True, output_files
    except Exception as e:
        return False, str(e)

def add_page_numbers(input_path, output_path):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for i, page in enumerate(reader.pages):
            temp_num_path = f"{input_path}_temp_num_{i}.pdf"
            c = canvas.Canvas(temp_num_path, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
            c.setFont("Helvetica", 12)
            c.drawString(float(page.mediabox.width) / 2, 20, str(i + 1))
            c.save()
            
            num_pdf = PdfReader(temp_num_path)
            num_page = num_pdf.pages[0]
            page.merge_page(num_page)
            writer.add_page(page)
            
            os.remove(temp_num_path)
            
        with open(output_path, "wb") as f:
            writer.write(f)
        return True, output_path
    except Exception as e:
        return False, str(e)

def compress_pdf(input_path, output_path, level='medium', target_kb=None):
    """
    Robust & High-Reduction PDF Compression targeting exact KB size if requested.
    """
    try:
        orig_size = os.path.getsize(input_path)
        
        target_bytes = None
        if target_kb:
            try:
                val = float(target_kb)
                if val > 0:
                    target_bytes = val * 1024
            except ValueError:
                pass

        if target_bytes and orig_size <= target_bytes:
            doc = fitz.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
            return True, output_path

        def _try_image_stream_compression(quality, max_dim, out_file):
            doc = fitz.open(input_path)
            for page in doc:
                image_list = page.get_images(full=True)
                for img in image_list:
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            pil_img = Image.open(io.BytesIO(image_bytes))
                            if pil_img.mode in ("RGBA", "P", "LA"):
                                pil_img = pil_img.convert("RGB")
                            if pil_img.width > max_dim or pil_img.height > max_dim:
                                pil_img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)
                            img_out = io.BytesIO()
                            pil_img.save(img_out, format="JPEG", quality=quality, optimize=True)
                            doc.update_stream(xref, img_out.getvalue())
                    except Exception:
                        pass
            doc.save(out_file, garbage=4, deflate=True, clean=True)
            doc.close()

        def _try_page_rasterization(dpi, quality, out_file):
            src_doc = fitz.open(input_path)
            out_doc = fitz.open()
            for page in src_doc:
                pix = page.get_pixmap(dpi=dpi)
                img_data = pix.tobytes("jpeg", jpg_quality=quality)
                img_doc = fitz.open("jpeg", img_data)
                rect = page.rect
                pdf_bytes = img_doc.convert_to_pdf()
                img_pdf = fitz.open("pdf", pdf_bytes)
                page_inst = out_doc.new_page(width=rect.width, height=rect.height)
                page_inst.show_pdf_page(rect, img_pdf, 0)
                img_doc.close()
                img_pdf.close()
            src_doc.close()
            out_doc.save(out_file, garbage=4, deflate=True, clean=True)
            out_doc.close()

        best_size = float('inf')

        if target_bytes:
            passes = [
                ('stream', 45, 900),
                ('stream', 25, 600),
                ('raster', 80, 40)
            ]
            temp_path = f"{output_path}_temp.pdf"
            for pass_type, p1, p2 in passes:
                try:
                    if pass_type == 'stream':
                        _try_image_stream_compression(quality=p1, max_dim=p2, out_file=temp_path)
                    else:
                        _try_page_rasterization(dpi=p1, quality=p2, out_file=temp_path)

                    if os.path.exists(temp_path):
                        sz = os.path.getsize(temp_path)
                        if sz < best_size:
                            best_size = sz
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            os.rename(temp_path, output_path)
                        else:
                            os.remove(temp_path)

                        if sz <= target_bytes:
                            break
                except Exception:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        else:
            if level == 'high':
                quality, max_dim = 30, 800
            elif level == 'low':
                quality, max_dim = 75, 1400
            else:
                quality, max_dim = 50, 1000
            _try_image_stream_compression(quality=quality, max_dim=max_dim, out_file=output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, output_path

        return False, "Compression failed"
    except Exception as e:
        return False, str(e)

def edit_pdf(input_path, output_path, edit_type='add_text', text='', find_text='', replace_text='', page_num=0, font_size=14, color='#000000', rotation_angle=0, visual_annotations=None):
    """
    Comprehensive PDF Editing Engine.
    Supports:
    1. Visual Studio Annotations: Text placement, freehand overlay drawings, redact privacy boxes, page rotations.
    2. 'add_text': Add custom text / annotations / watermark to PDF.
    3. 'replace_text': Find and replace / overwrite text in PDF.
    4. 'rotate': Rotate PDF pages (90°, 180°, 270°).
    """
    try:
        doc = fitz.open(input_path)
        
        def parse_color(c_str):
            try:
                c_str = str(c_str).lstrip('#')
                if len(c_str) == 6:
                    r = int(c_str[0:2], 16) / 255.0
                    g = int(c_str[2:4], 16) / 255.0
                    b = int(c_str[4:6], 16) / 255.0
                    return (r, g, b)
            except Exception:
                pass
            return (0, 0, 0)

        rgb_color = parse_color(color)
        page_idx_target = int(page_num) if page_num else 0

        # Handle Visual Studio Annotations if provided
        if visual_annotations and isinstance(visual_annotations, (dict, list)):
            if isinstance(visual_annotations, list):
                items = visual_annotations
            else:
                items = visual_annotations.get('items', [])
                rotations = visual_annotations.get('rotations', {})
                # Apply page rotations first
                for p_str, ang in rotations.items():
                    try:
                        p_idx = int(p_str)
                        if 0 <= p_idx < len(doc):
                            page = doc[p_idx]
                            page.set_rotation((page.rotation + int(ang)) % 360)
                    except Exception:
                        pass

            import base64
            for item in items:
                try:
                    p_idx = int(item.get('page', 0))
                    if not (0 <= p_idx < len(doc)):
                        continue
                    page = doc[p_idx]
                    rect = page.rect
                    item_type = item.get('type')

                    if item_type == 'text':
                        txt = str(item.get('text', '')).strip()
                        if txt:
                            x_ratio = float(item.get('x_ratio', 0))
                            y_ratio = float(item.get('y_ratio', 0))
                            fs = float(item.get('font_size', font_size))
                            col = parse_color(item.get('color', color))
                            pt = fitz.Point(x_ratio * rect.width, y_ratio * rect.height + fs)
                            page.insert_text(pt, txt, fontsize=fs, color=col)

                    elif item_type == 'redact':
                        xr = float(item.get('x_ratio', 0))
                        yr = float(item.get('y_ratio', 0))
                        wr = float(item.get('w_ratio', 0))
                        hr = float(item.get('h_ratio', 0))
                        fill_col = parse_color(item.get('fill_color', '#000000'))
                        r_box = fitz.Rect(xr * rect.width, yr * rect.height, (xr + wr) * rect.width, (yr + hr) * rect.height)
                        page.add_redact_annot(r_box, fill=fill_col)
                        page.apply_redactions()

                    elif item_type == 'overlay_image':
                        b64_data = item.get('image_data', '')
                        if ',' in b64_data:
                            b64_data = b64_data.split(',', 1)[1]
                        img_bytes = base64.b64decode(b64_data)
                        page.insert_image(rect, stream=img_bytes)
                except Exception as ex:
                    print(f"Annotation item error: {ex}")

        # Legacy / direct form options fallback
        if edit_type == 'add_text' and text.strip():
            target_pages = [page_idx_target - 1] if (1 <= page_idx_target <= len(doc)) else list(range(len(doc)))
            for p_idx in target_pages:
                page = doc[p_idx]
                rect = page.rect
                point = fitz.Point(50, rect.height - 50)
                page.insert_text(point, text.strip(), fontsize=float(font_size), color=rgb_color)

        elif edit_type == 'replace_text' and find_text.strip():
            target_pages = [page_idx_target - 1] if (1 <= page_idx_target <= len(doc)) else list(range(len(doc)))
            for p_idx in target_pages:
                page = doc[p_idx]
                areas = page.search_for(find_text.strip())
                for r in areas:
                    page.add_redact_annot(r, fill=(1, 1, 1))
                page.apply_redactions()
                
                for r in areas:
                    page.insert_textbox(r, replace_text.strip(), fontsize=float(font_size), color=rgb_color)

        elif edit_type == 'rotate':
            angle = int(rotation_angle) % 360
            target_pages = [page_idx_target - 1] if (1 <= page_idx_target <= len(doc)) else list(range(len(doc)))
            for p_idx in target_pages:
                page = doc[p_idx]
                page.set_rotation((page.rotation + angle) % 360)

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return True, output_path
    except Exception as e:
        return False, f"PDF Edit Error: {str(e)}"

