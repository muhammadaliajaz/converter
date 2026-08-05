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

def compress_pdf(input_path, output_path, level='medium'):
    """
    High-performance PDF Compression using PyMuPDF and PIL image stream optimization
    """
    try:
        doc = fitz.open(input_path)
        
        # Set quality level
        if level == 'high':
            quality = 40
        elif level == 'low':
            quality = 75
        else:
            quality = 55 # medium

        # Optimize embedded images in PDF
        for page in doc:
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        image_bytes = base_image["image"]
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        
                        # Convert RGBA/Palette to RGB
                        if pil_img.mode in ("RGBA", "P", "LA"):
                            pil_img = pil_img.convert("RGB")
                        
                        # Downscale very large images
                        if pil_img.width > 1600 or pil_img.height > 1600:
                            pil_img.thumbnail((1600, 1600), Image.Resampling.BILINEAR)

                        img_out = io.BytesIO()
                        pil_img.save(img_out, format="JPEG", quality=quality, optimize=True)
                        doc.update_stream(xref, img_out.getvalue())
                except Exception:
                    pass

        # Save with garbage collection, stream deflation, and compacting
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        return True, output_path
    except Exception as e:
        return False, str(e)
