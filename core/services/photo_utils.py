from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
import sys


def process_profile_photo(photo, rotation=0):
    """
    Process uploaded photo: resize, rotate, and optimize

    Args:
        photo: UploadedFile object
        rotation: int - degrees to rotate (0, 90, 180, 270)

    Returns:
        InMemoryUploadedFile: processed image
    """
    # Open the image
    img = Image.open(photo)

    # Convert to RGB if necessary (handles RGBA, P, etc.)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')

    # Handle RGBA images
    if img.mode == 'RGBA':
        # Create a white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background

    # Rotate if needed
    if rotation in [90, 180, 270]:
        img = img.rotate(-rotation, expand=True)

    # Get target dimensions
    target_width, target_height = getattr(settings, 'PHOTO_DIMENSIONS', (400, 400))

    # Calculate aspect ratio and resize
    img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

    # Create a square canvas with white background
    canvas = Image.new('RGB', (target_width, target_height), (255, 255, 255))

    # Center the image on the canvas
    offset_x = (target_width - img.width) // 2
    offset_y = (target_height - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))

    # Save to BytesIO
    output = BytesIO()
    canvas.save(output, format='JPEG', quality=85, optimize=True)
    output.seek(0)

    # Create InMemoryUploadedFile
    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{photo.name.split('.')[0]}.jpg",
        'image/jpeg',
        sys.getsizeof(output),
        None
    )


def validate_photo(photo):
    """
    Validate photo file

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check file size
    max_size = getattr(settings, 'MAX_PHOTO_SIZE', 5 * 1024 * 1024)
    if photo.size > max_size:
        return False, f'Image file too large. Maximum size is {max_size / 1024 / 1024}MB.'

    # Check file type
    valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if photo.content_type not in valid_types:
        return False, 'Invalid file type. Please upload a JPG, PNG, GIF, or WebP image.'

    try:
        # Try to open as image
        img = Image.open(photo)
        img.verify()
        photo.seek(0)  # Reset file pointer
        return True, None
    except Exception as e:
        return False, f'Invalid image file: {str(e)}'