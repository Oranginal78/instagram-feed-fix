from PIL import Image, ImageFilter
import os
import zipfile
import io
import uuid

def load_images_in_upload_order(image_dir):
    files = sorted(os.listdir(image_dir))
    images = []
    for filename in files:
        path = os.path.join(image_dir, filename)
        try:
            img = Image.open(path)
            images.append(img)
        except Exception as e:
            print(f"Erreur chargement {filename}: {str(e)}")
    return images

def create_instagram_grid(images, cols=3):
    n = len(images)
    rows = (n + cols - 1) // cols

    grid_width = 1080 * cols
    grid_height = 1080 * rows
    grid = Image.new("RGB", (grid_width, grid_height))

    for i in range(n):
        img = images[i]
        if img.width != 1080 or img.height != 1080:
            img = img.resize((1080, 1080))

        row = rows - 1 - (i // cols)
        col = cols - 1 - (i % cols)
        grid.paste(img, (col * 1080, row * 1080))

    return grid

def resize_to_3045(image):
    original_width, original_height = image.size
    target_width = 3045
    scale_factor = target_width / original_width
    new_height = int(original_height * scale_factor)
    resized = image.resize((target_width, new_height), Image.LANCZOS)

    remainder = resized.height % 1350
    pad_top = 1350 - remainder if remainder != 0 else 0
    final_img = Image.new("RGB", (3045, resized.height + pad_top), (0, 0, 0))
    final_img.paste(resized, (0, pad_top))
    return final_img

def slice_and_add_side_margins(image, slice_width=1015, slice_height=1350):
    slices = []
    num_rows = image.height // slice_height

    for row in range(num_rows):
        for col in range(3):
            left = col * slice_width
            top = row * slice_height
            right = left + slice_width
            bottom = top + slice_height

            cropped = image.crop((left, top, right, bottom))
            blurred_bg = cropped.resize((1081, 1350), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
            final = blurred_bg.copy()
            final.paste(cropped, (33, 0))
            slices.append(final)

    return slices

def export_zip(base_img, formatted_img, slices):
    zip_path = f"/tmp/result_{uuid.uuid4()}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        buf1 = io.BytesIO()
        base_img.convert("RGB").save(buf1, format="JPEG", quality=95)
        zipf.writestr("assembled_grid.jpg", buf1.getvalue())

        buf2 = io.BytesIO()
        formatted_img.convert("RGB").save(buf2, format="JPEG", quality=95)
        zipf.writestr("assembled_grid_formatted.jpg", buf2.getvalue())

        for i, img in enumerate(slices):
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=95)
            zipf.writestr(f"{i+1:02d}_1081x1350.jpg", buf.getvalue())

    return zip_path

def process_grid(image_dir):
    images = load_images_in_upload_order(image_dir)
    if not images:
        return None

    base_grid = create_instagram_grid(images)
    formatted_grid = resize_to_3045(base_grid)
    final_slices = slice_and_add_side_margins(formatted_grid)
    return export_zip(base_grid, formatted_grid, final_slices)

def process_assembled_image(image_path):
    try:
        base_img = Image.open(image_path)
    except Exception as e:
        print(f"Erreur ouverture image: {str(e)}")
        return None

    if base_img.width != 3240:
        print("L'image doit être de 3240px de large pour être considérée comme assemblée.")
        return None

    formatted_grid = resize_to_3045(base_img)
    final_slices = slice_and_add_side_margins(formatted_grid)
    return export_zip(base_img, formatted_grid, final_slices)

def process_images(image_dir, mode="grid"):
    if mode == "grid":
        return process_grid(image_dir)
    else:
        print(f"Mode non pris en charge: {mode}")
        return None
