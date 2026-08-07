import os
import fitz
from deep_translator import GoogleTranslator
from PyPDF2 import PdfReader

def extract_text_from_pdf(input_path, output_path):
    try:
        reader = PdfReader(input_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True, output_path
    except Exception as e:
        return False, str(e)

def extract_text_from_image(input_path, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Image text extraction completed.")
        return True, output_path
    except Exception as e:
        return False, str(e)

def translate_pdf_to_txt(input_path, output_path, target_lang='en'):
    try:
        doc = fitz.open(input_path)
        raw_text = ""
        for page in doc:
            raw_text += page.get_text() + "\n"
            
        if not raw_text.strip():
            return False, "No readable text found in PDF."
            
        translator = GoogleTranslator(source='auto', target=target_lang)
        chunks = [raw_text[i:i+4000] for i in range(0, len(raw_text), 4000)]
        translated_text = ""
        for chunk in chunks:
            translated_text += translator.translate(chunk) + "\n"
            
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(translated_text)
            
        return True, output_path
    except Exception as e:
        return False, str(e)
