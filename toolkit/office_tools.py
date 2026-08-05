import os
import fitz
from pptx import Presentation
import pdfplumber
import pandas as pd

def pdf_to_docx(input_path, output_path):
    try:
        from pdf2docx import Converter
        cv = Converter(input_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
        return True, output_path
    except Exception as e:
        return False, str(e)

def pdf_to_ppt(input_path, output_path):
    try:
        prs = Presentation()
        doc = fitz.open(input_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_path = f"{input_path}_page_{page_num}.png"
            pix.save(img_path)
            
            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)
            
            slide.shapes.add_picture(img_path, 0, 0, width=prs.slide_width, height=prs.slide_height)
            os.remove(img_path)
            
        prs.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)

def pdf_to_excel(input_path, output_path):
    try:
        all_tables = []
        with pdfplumber.open(input_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table and len(table) > 1:
                        headers = table[0]
                        headers = [h if h else f"Col_{j}" for j, h in enumerate(headers)]
                        df = pd.DataFrame(table[1:], columns=headers)
                        all_tables.append(df)
                    
        if not all_tables:
            return False, "No tables found in PDF to convert to Excel."
            
        with pd.ExcelWriter(output_path) as writer:
            for i, df in enumerate(all_tables):
                df.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
                
        return True, output_path
    except Exception as e:
        return False, str(e)

def ppt_to_pdf(input_path, output_path):
    try:
        import comtypes.client
        powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
        powerpoint.Visible = 1
        deck = powerpoint.Presentations.Open(os.path.abspath(input_path), WithWindow=False)
        deck.SaveAs(os.path.abspath(output_path), 32)
        deck.Close()
        powerpoint.Quit()
        return True, output_path
    except Exception as e:
        return False, "PPT to PDF conversion requires Windows MS Office."

def excel_to_pdf(input_path, output_path):
    try:
        import comtypes.client
        excel = comtypes.client.CreateObject("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(os.path.abspath(input_path))
        wb.ExportAsFixedFormat(0, os.path.abspath(output_path))
        wb.Close(False)
        excel.Quit()
        return True, output_path
    except Exception as e:
        return False, "Excel to PDF conversion requires Windows MS Office."

def docx_to_pdf(input_path, output_path):
    try:
        from docx2pdf import convert
        convert(os.path.abspath(input_path), os.path.abspath(output_path))
        return True, output_path
    except Exception as e:
        return False, "DOCX to PDF conversion requires Windows MS Office."
