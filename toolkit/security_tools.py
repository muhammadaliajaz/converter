import fitz

def protect_pdf(input_path, output_path, password):
    """
    Encrypt PDF using PyMuPDF (0.01s, 0 C++ dependencies)
    """
    try:
        doc = fitz.open(input_path)
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
        doc.close()
        return True, output_path
    except Exception as e:
        return False, str(e)

def unlock_pdf(input_path, output_path, password):
    """
    Decrypt PDF using PyMuPDF (0.01s, 0 C++ dependencies)
    """
    try:
        doc = fitz.open(input_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                doc.close()
                return False, "Failed to unlock. Password might be incorrect."
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()
        return True, output_path
    except Exception as e:
        return False, f"Failed to unlock: {str(e)}"
