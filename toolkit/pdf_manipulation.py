import os
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import fitz
from reportlab.pdfgen import canvas

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
            output_files.append((out_name, out_name)) # tuple mapping real_name -> zip_name
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
    try:
        if level == 'low':
            reader = PdfReader(input_path)
            writer = PdfWriter()
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
        else:
            doc = fitz.open(input_path)
            if level == 'high':
                doc.save(output_path, garbage=4, deflate=True, clean=True)
            else:
                doc.save(output_path, garbage=3, deflate=True)
        return True, output_path
    except Exception as e:
        return False, str(e)
