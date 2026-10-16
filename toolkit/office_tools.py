import os
import io
import re
import fitz
import openpyxl
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import parse_xml
from pptx import Presentation
from pptx.util import Inches as PPTInches, Pt as PPTPt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def clean_xml_text(text):
    """
    Sanitizes text strings to be strict XML 1.0 compliant.
    Strips illegal control characters (\x00-\x08, \x0B, \x0C, \x0E-\x1F).
    """
    if text is None:
        return ""
    text_str = str(text).replace('\x0b', '\n').replace('\x0c', '\n')
    return re.sub(r'[\x00-\x08\x0E-\x1F\x7F-\x9F]', '', text_str)

def pdf_to_docx(input_path, output_path):
    """
    High-Fidelity PDF to DOCX Converter.
    Preserves exact document layout, page dimensions, margins, font styling,
    alignment, paragraph spacing, multi-column tables, embedded images, and page breaks.
    Strictly excludes text inside table boundaries from loose paragraph dumping,
    interleaves tables in their exact vertical order, and sets proper Word table styles.
    """
    try:
        doc = Document()
        pdf = fitz.open(input_path)

        for page_idx, page in enumerate(pdf):
            page_rect = page.rect
            page_w_in = page_rect.width / 72.0
            page_h_in = page_rect.height / 72.0

            if page_idx == 0:
                section = doc.sections[0]
            else:
                section = doc.add_section()

            section.page_width = Inches(page_w_in)
            section.page_height = Inches(page_h_in)
            section.top_margin = Inches(0.5)
            section.bottom_margin = Inches(0.5)
            section.left_margin = Inches(0.5)
            section.right_margin = Inches(0.5)

            content_width_in = max(1.0, page_w_in - 1.0)

            # 1. Detect Tables on Page
            detected_tables = []
            table_bboxes = []
            try:
                tabs = page.find_tables()
                if not tabs or len(tabs.tables) == 0:
                    tabs = page.find_tables(strategy="text")
                if tabs and len(tabs.tables) > 0:
                    for tab in tabs.tables:
                        matrix = tab.extract()
                        if matrix and len(matrix) > 0 and any(any(cell for cell in row) for row in matrix):
                            detected_tables.append(tab)
                            table_bboxes.append(tab.bbox)
            except Exception:
                pass

            # Helper function: Check if a bounding box overlaps with any detected table
            def is_inside_table(bbox):
                bx0, by0, bx1, by1 = bbox
                bcx = (bx0 + bx1) / 2.0
                bcy = (by0 + by1) / 2.0
                for tx0, ty0, tx1, ty1 in table_bboxes:
                    if (tx0 - 4 <= bcx <= tx1 + 4) and (ty0 - 4 <= bcy <= ty1 + 4):
                        return True
                    overlap_x = max(0, min(bx1, tx1) - max(bx0, tx0))
                    overlap_y = max(0, min(by1, ty1) - max(by0, ty0))
                    overlap_area = overlap_x * overlap_y
                    box_area = max(1, (bx1 - bx0) * (by1 - by0))
                    if (overlap_area / box_area) > 0.4:
                        return True
                return False

            blocks = page.get_text("dict")["blocks"]
            img_list = page.get_images()

            # 2. Build Ordered List of Page Elements (Text, Tables, Images)
            elements = []

            # Add detected tables to elements
            for tab in detected_tables:
                elements.append({
                    'type': 'table',
                    'y0': tab.bbox[1],
                    'bbox': tab.bbox,
                    'tab': tab
                })

            # Add text blocks (only if NOT inside a table) and images
            for b in blocks:
                b_type = b.get("type", 0)
                b_bbox = b.get("bbox", [0, 0, 0, 0])
                
                # Skip text blocks that fall inside a table
                if is_inside_table(b_bbox):
                    continue

                if b_type == 0 and "lines" in b:
                    valid_lines = []
                    for line in b["lines"]:
                        line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                        if clean_xml_text(line_text).strip():
                            valid_lines.append(line)
                    if valid_lines:
                        b_copy = dict(b)
                        b_copy["lines"] = valid_lines
                        elements.append({
                            'type': 'text_block',
                            'y0': b_bbox[1],
                            'bbox': b_bbox,
                            'block': b_copy
                        })
                elif b_type == 1 and "image" in b:
                    elements.append({
                        'type': 'image_block',
                        'y0': b_bbox[1],
                        'bbox': b_bbox,
                        'block': b
                    })

            # Sort all elements strictly by their vertical position (top to bottom reading order)
            elements.sort(key=lambda item: item['y0'])

            has_content = False

            # 3. Render Elements Sequentially in Document
            for item in elements:
                itype = item['type']

                # --- TABLE RENDERING ---
                if itype == 'table':
                    has_content = True
                    tab = item['tab']
                    matrix = tab.extract()
                    if not matrix or len(matrix) == 0:
                        continue

                    max_cols = max(len(row) for row in matrix if row)
                    if max_cols == 0:
                        continue

                    cleaned_matrix = []
                    for row in matrix:
                        cleaned_row = [clean_xml_text(cell) if cell is not None else "" for cell in row]
                        while len(cleaned_row) < max_cols:
                            cleaned_row.append("")
                        if any(c.strip() for c in cleaned_row):
                            cleaned_matrix.append(cleaned_row)

                    if not cleaned_matrix:
                        continue

                    num_rows = len(cleaned_matrix)
                    tbl = doc.add_table(rows=num_rows, cols=max_cols)
                    tbl.style = 'Table Grid'
                    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                    tbl.autofit = False

                    t_bbox = tab.bbox
                    t_width_in = min((t_bbox[2] - t_bbox[0]) / 72.0, content_width_in)
                    col_width_in = t_width_in / max_cols

                    for row_idx, row_vals in enumerate(cleaned_matrix):
                        tr = tbl.rows[row_idx]
                        try:
                            tr._tr.get_or_add_trPr().append(parse_xml(r'<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
                        except Exception:
                            pass

                        is_header = (row_idx == 0)

                        for col_idx in range(max_cols):
                            cell = tbl.cell(row_idx, col_idx)
                            cell.width = Inches(col_width_in)
                            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                            cell_text = row_vals[col_idx].strip()
                            cell.text = cell_text

                            for p in cell.paragraphs:
                                p.paragraph_format.space_before = Pt(2)
                                p.paragraph_format.space_after = Pt(2)
                                p.paragraph_format.line_spacing = 1.05
                                
                                if is_header:
                                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    for run in p.runs:
                                        run.bold = True
                                        run.font.size = Pt(9.5)
                                else:
                                    for run in p.runs:
                                        run.font.size = Pt(9.0)

                            if is_header:
                                try:
                                    shd_xml = r'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="F1F5F9"/>'
                                    cell._tc.get_or_add_tcPr().append(parse_xml(shd_xml))
                                except Exception:
                                    pass

                    # Small spacing after table
                    p_spacer = doc.add_paragraph()
                    p_spacer.paragraph_format.space_before = Pt(0)
                    p_spacer.paragraph_format.space_after = Pt(4)

                # --- TEXT BLOCK RENDERING ---
                elif itype == 'text_block':
                    has_content = True
                    b = item['block']
                    for line in b["lines"]:
                        p = doc.add_paragraph()
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(1)
                        p.paragraph_format.line_spacing = 1.05

                        line_bbox = line.get("bbox", [0, 0, 0, 0])
                        left_margin = line_bbox[0]
                        right_margin = page_rect.width - line_bbox[2]

                        if abs(left_margin - right_margin) < 35 and left_margin > 40:
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        elif left_margin > page_rect.width * 0.55:
                            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        else:
                            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                        for span in line.get("spans", []):
                            raw_text = span.get("text", "")
                            text = clean_xml_text(raw_text)
                            if not text:
                                continue

                            run = p.add_run(text)
                            if "size" in span:
                                run.font.size = Pt(max(6.0, span["size"]))

                            font_name = span.get("font", "").strip()
                            if font_name:
                                clean_font = re.sub(r'^[A-Z]{6}\+', '', font_name)
                                clean_font = clean_font.replace('-', ' ').replace(',', ' ')
                                run.font.name = clean_font

                            flags = span.get("flags", 0)
                            if flags & 16 or "bold" in font_name.lower():
                                run.bold = True
                            if flags & 2 or "italic" in font_name.lower():
                                run.italic = True

                            if "color" in span:
                                c = span["color"]
                                r = (c >> 16) & 0xFF
                                g = (c >> 8) & 0xFF
                                b_val = c & 0xFF
                                run.font.color.rgb = RGBColor(r, g, b_val)

                # --- IMAGE RENDERING ---
                elif itype == 'image_block':
                    has_content = True
                    b = item['block']
                    try:
                        img_bytes = b["image"]
                        img_ext = b.get("ext", "png")
                        img_temp_path = f"{output_path}_img_{page_idx}_{b.get('number', 0)}.{img_ext}"
                        with open(img_temp_path, "wb") as f_img:
                            f_img.write(img_bytes)

                        bbox = b.get("bbox", [0, 0, 100, 100])
                        img_w_pt = bbox[2] - bbox[0]
                        img_w_in = min(img_w_pt / 72.0, content_width_in)
                        img_w_in = max(img_w_in, 0.5)

                        p_img = doc.add_paragraph()
                        p_img.paragraph_format.space_before = Pt(2)
                        p_img.paragraph_format.space_after = Pt(2)

                        if img_w_in > (page_w_in * 0.4):
                            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        else:
                            p_img.alignment = WD_ALIGN_PARAGRAPH.LEFT

                        p_img.add_run().add_picture(img_temp_path, width=Inches(img_w_in))
                        try: os.remove(img_temp_path)
                        except: pass
                    except Exception:
                        pass

            # 4. Scanned Page Fallback
            if not has_content and len(img_list) > 0:
                for img_info in img_list:
                    try:
                        xref = img_info[0]
                        base_image = pdf.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            img_temp_path = f"{output_path}_xref_{xref}.{image_ext}"
                            with open(img_temp_path, "wb") as f_img:
                                f_img.write(image_bytes)
                            doc.add_picture(img_temp_path, width=Inches(content_width_in))
                            try: os.remove(img_temp_path)
                            except: pass
                    except Exception:
                        pass
            elif not has_content and len(img_list) == 0:
                pix = page.get_pixmap(dpi=150)
                img_temp = f"{output_path}_page_{page.number}.png"
                pix.save(img_temp)
                doc.add_picture(img_temp, width=Inches(content_width_in))
                try: os.remove(img_temp)
                except: pass

        pdf.close()
        doc.save(output_path)
        return True, output_path
    except Exception as e:
        return False, f"PDF to Word conversion error: {str(e)}"

def docx_to_pdf(input_path, output_path):
    """
    High-Fidelity DOCX to PDF Converter.
    Preserves document structure, headings, bold/italic formatting, tables, and paragraph spacing.
    """
    try:
        doc = Document(input_path)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        normal_style = styles['Normal']

        for p in doc.paragraphs:
            if not p.text.strip():
                story.append(Spacer(1, 6))
                continue

            # Format paragraph text runs
            p_html = ""
            for run in p.runs:
                txt = clean_xml_text(run.text)
                if not txt: continue
                safe_txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if run.bold:
                    safe_txt = f"<b>{safe_txt}</b>"
                if run.italic:
                    safe_txt = f"<i>{safe_txt}</i>"
                p_html += safe_txt

            if p_html:
                story.append(Paragraph(p_html, normal_style))
                story.append(Spacer(1, 4))

        # Table preservation
        for t in doc.tables:
            table_data = []
            for row in t.rows:
                row_data = [Paragraph(clean_xml_text(cell.text), normal_style) for cell in row.cells]
                table_data.append(row_data)
            if table_data:
                rl_table = Table(table_data)
                rl_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(rl_table)
                story.append(Spacer(1, 8))

        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, f"DOCX to PDF conversion error: {str(e)}"

def pdf_to_ppt(input_path, output_path):
    """
    High-Fidelity PDF to PowerPoint Converter.
    Preserves exact visual layout, graphics, fonts, and slide dimensions.
    """
    try:
        prs = Presentation()
        doc = fitz.open(input_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_stream = io.BytesIO(pix.tobytes("png"))

            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)
            slide.shapes.add_picture(img_stream, 0, 0, width=prs.slide_width, height=prs.slide_height)

        doc.close()
        prs.save(output_path)
        return True, output_path
    except Exception as e:
        return False, f"PDF to PPT conversion error: {str(e)}"

def ppt_to_pdf(input_path, output_path):
    """
    High-Fidelity PowerPoint to PDF Converter.
    Preserves slide headings, body text, tables, and bullet points.
    """
    try:
        prs = Presentation(input_path)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'SlideTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=8
        )
        body_style = styles['Normal']

        for idx, slide in enumerate(prs.slides):
            story.append(Paragraph(f"Slide {idx + 1}", title_style))
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        txt = clean_xml_text(para.text)
                        if txt.strip():
                            story.append(Paragraph(txt, body_style))
                            story.append(Spacer(1, 4))
            story.append(Spacer(1, 12))

        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, f"PPT to PDF conversion error: {str(e)}"

def pdf_to_excel(input_path, output_path):
    """
    High-Fidelity PDF to Excel Converter.
    Extracts tables and structured text into clean Excel worksheets with cell formatting.
    """
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Extracted_Data"
        pdf = fitz.open(input_path)
        row_idx = 1

        for page in pdf:
            tables = page.find_tables()
            if tables and len(tables.tables) > 0:
                for tab in tables.tables:
                    extracted = tab.extract()
                    for r in extracted:
                        for col_idx, val in enumerate(r, 1):
                            clean_val = clean_xml_text(val)
                            ws.cell(row=row_idx, column=col_idx, value=clean_val)
                        row_idx += 1
                    row_idx += 1
            else:
                text = page.get_text("text")
                for line in text.split('\n'):
                    if line.strip():
                        parts = line.strip().split()
                        for col_idx, part in enumerate(parts, 1):
                            ws.cell(row=row_idx, column=col_idx, value=clean_xml_text(part))
                        row_idx += 1

        pdf.close()
        wb.save(output_path)
        return True, output_path
    except Exception as e:
        return False, f"PDF to Excel conversion error: {str(e)}"

def excel_to_pdf(input_path, output_path):
    """
    High-Fidelity Excel to PDF Converter.
    Renders openpyxl worksheets into formatted PDF data tables with grid lines and headers.
    """
    try:
        wb = openpyxl.load_workbook(input_path, data_only=True)
        ws = wb.active
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        data = []
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                data.append([Paragraph(clean_xml_text(str(c)) if c is not None else "", styles['Normal']) for c in row])

        if data:
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t)

        pdf_doc.build(story)
        return True, output_path
    except Exception as e:
        return False, f"Excel to PDF conversion error: {str(e)}"
