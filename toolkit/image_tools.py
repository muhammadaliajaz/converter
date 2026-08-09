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
        doc.close()
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
            first_image.save(output_path, save_all=True, append_images=images, optimize=True)
            return True, output_path
        else:
            return False, "No valid images provided."
    except Exception as e:
        return False, str(e)

def compress_image_to_kb(input_path, output_path, target_kb):
    """
    Fast & High-reduction Image Compression
    """
    try:
        target_bytes = int(target_kb) * 1024
        img = Image.open(input_path)
        
        # Convert RGBA/Palette/CMYK images to RGB
        if img.mode in ("RGBA", "P", "LA", "CMYK"):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Fast binary search for JPEG quality
        low, high = 5, 90
        best_quality = 40
        best_data = None

        for _ in range(6):
            mid = (low + high) // 2
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=mid, optimize=True)
            size = buf.tell()

            if size <= target_bytes:
                best_quality = mid
                best_data = buf.getvalue()
                low = mid + 1
            else:
                high = mid - 1

        if best_data is None or len(best_data) > target_bytes:
            w, h = img.size
            scale = 0.8
            while scale >= 0.2:
                nw, nh = int(w * scale), int(h * scale)
                resized_img = img.resize((nw, nh), Image.Resampling.BILINEAR)
                buf = io.BytesIO()
                resized_img.save(buf, format="JPEG", quality=45, optimize=True)
                if buf.tell() <= target_bytes or scale <= 0.25:
                    best_data = buf.getvalue()
                    break
                scale -= 0.2

        with open(output_path, "wb") as f:
            f.write(best_data if best_data else buf.getvalue())
            
        return True, output_path
        
    except Exception as e:
        return False, str(e)

def convert_image_format(input_path, output_path, target_format):
    try:
        img = Image.open(input_path)
        fmt_upper = str(target_format).upper().strip()
        format_mapping = {'JPG': 'JPEG', 'JPEG': 'JPEG', 'PNG': 'PNG', 'WEBP': 'WEBP', 'BMP': 'BMP', 'GIF': 'GIF'}
        t_format = format_mapping.get(fmt_upper, 'JPEG')
        
        if t_format == 'JPEG':
            if img.mode in ('RGBA', 'LA', 'P', 'CMYK'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = img.convert('RGB')
        elif t_format in ('PNG', 'WEBP', 'BMP', 'GIF'):
            if img.mode == 'CMYK':
                img = img.convert('RGB')
            elif t_format == 'BMP' and img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
        
        save_kwargs = {}
        if t_format in ('JPEG', 'PNG', 'WEBP'):
            save_kwargs['optimize'] = True

        img.save(output_path, format=t_format, **save_kwargs)
        return True, output_path
    except Exception as e:
        return False, str(e)
