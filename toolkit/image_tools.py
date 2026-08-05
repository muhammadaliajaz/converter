import os
import io
import fitz
from PIL import Image

def pdf_to_jpg(input_path, output_dir, unique_batch_id):
    try:
        doc = fitz.open(input_path)
        output_files = []
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            out_name = f"{unique_batch_id}_page_{i+1}.jpg"
            out_path = os.path.join(output_dir, out_name)
            pix.save(out_path)
            output_files.append((out_name, out_name))
        return True, output_files
    except Exception as e:
        return False, str(e)

def jpg_to_pdf(input_paths, output_path):
    try:
        images = []
        first_image = None
        for path in input_paths:
            img = Image.open(path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            if first_image is None:
                first_image = img
            else:
                images.append(img)
                
        if first_image:
            first_image.save(output_path, save_all=True, append_images=images)
            return True, output_path
        else:
            return False, "No valid images provided."
    except Exception as e:
        return False, str(e)

def compress_image_to_kb(input_path, output_path, target_kb):
    try:
        target_bytes = int(target_kb) * 1024
        img = Image.open(input_path)
        if img.mode in ("RGBA", "P"):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert("RGB")
            
        low = 1
        high = 95
        best_quality = 1
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=high)
        if buffer.tell() <= target_bytes:
             best_quality = high
        else:
             while low <= high:
                 mid = (low + high) // 2
                 buffer = io.BytesIO()
                 img.save(buffer, format="JPEG", quality=mid)
                 if buffer.tell() <= target_bytes:
                     best_quality = mid
                     low = mid + 1
                 else:
                     high = mid - 1
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=best_quality)
        
        current_img = img.copy()
        while buffer.tell() > target_bytes and current_img.size[0] > 100:
            new_size = (int(current_img.size[0] * 0.9), int(current_img.size[1] * 0.9))
            current_img = current_img.resize(new_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            current_img.save(buffer, format="JPEG", quality=best_quality)
            
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
            
        return True, output_path
        
    except Exception as e:
        return False, str(e)

def convert_image_format(input_path, output_path, target_format):
    try:
        img = Image.open(input_path)
        format_mapping = {'JPG': 'JPEG', 'JPEG': 'JPEG', 'PNG': 'PNG', 'WEBP': 'WEBP', 'BMP': 'BMP', 'GIF': 'GIF'}
        t_format = format_mapping.get(target_format.upper(), 'JPEG')
        
        if t_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
        
        img.save(output_path, format=t_format)
        return True, output_path
    except Exception as e:
        return False, str(e)
