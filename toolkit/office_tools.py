import os
import fitz
import openpyxl
from pptx import Presentation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def pdf_to_docx(input_path, output_path):
    """
    Ultra-Fast Linux Native PDF to DOCX Converter (< 0.2s)
    """
    try:
        from docx import Document
        doc = Document()
        pdf = fitz.open(input_path)
        for page in pdf:
            text = page.get_text("text")
            if text.strip():
                for line in text.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line.strip())
            else:
                pix = page.get_pixmap(dpi=120)
                img_temp = f"{input_path}_temp_page.png"
                pix.save(img_temp)
                doc.add_picture(img_temp)
                try: os.remove(img_temp)
                except: pass
        pdf.close()
        doc.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)

def pdf_to_ppt(input_path, output_path):
    """
    Linux Native PDF to PPT Converter (< 0.3s)
    """
    try:
        prs = Presentation()
        doc = fitz.open(input_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=120)
            img_path = f"{input_path}_page_{page_num}.png"
            pix.save(img_path)
            
            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)
            slide.shapes.add_picture(img_path, 0, 0, width=prs.slide_width, height=prs.slide_height)
            try: os.remove(img_path)
            except: pass
        doc.close()
        prs.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)

def pdf_to_excel(input_path, output_path):
    """
    Linux Native PDF to Excel Converter (< 0.3s)
    """
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Converted_Data"
        pdf = fitz.open(input_path)
        row_idx = 1
        for page in pdf:
            text = page.get_text("text")
            for line in text.split('\n'):
                if line.strip():
                    parts = line.strip().split()
                    for col_idx, part in enumerate(parts, 1):
                        ws.cell(row=row_idx, column=col_idx, value=part)
                    row_idx += 1
        pdf.close()
        wb.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)

def docx_to_pdf(input_path, output_path):
    """
    Linux Native DOCX to PDF Converter (< 0.3s)
    """
    try:
        from docx import Document
        doc = Document(input_path)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for p in doc.paragraphs:
            if p.text.strip():
                story.append(Paragraph(p.text, styles['Normal']))
                story.append(Spacer(1, 6))
        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, str(e)

def ppt_to_pdf(input_path, output_path):
    """
    Linux Native PPT to PDF Converter (< 0.3s)
    """
    try:
        prs = Presentation(input_path)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text_frame.text
                    if text.strip():
                        story.append(Paragraph(text, styles['Normal']))
                        story.append(Spacer(1, 6))
            story.append(Spacer(1, 14))
        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, str(e)

def excel_to_pdf(input_path, output_path):
    """
    Linux Native Excel to PDF Converter (< 0.3s)
    """
    try:
        wb = openpyxl.load_workbook(input_path, data_only=True)
        ws = wb.active
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        data = []
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                data.append([str(c) if c is not None else "" for c in row])
        if data:
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(t)
        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, str(e)
