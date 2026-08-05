import pikepdf

def protect_pdf(input_path, output_path, password):
    try:
        pdf = pikepdf.Pdf.open(input_path)
        pdf.save(output_path, encryption=pikepdf.Encryption(user=password, owner=password, allow=pikepdf.Permissions(extract=False, print=False)))
        pdf.close()
        return True, output_path
    except Exception as e:
        return False, str(e)

def unlock_pdf(input_path, output_path, password):
    try:
        pdf = pikepdf.Pdf.open(input_path, password=password)
        pdf.save(output_path)
        pdf.close()
        return True, output_path
    except Exception as e:
        return False, "Failed to unlock. Password might be incorrect or file is corrupted."
