"""Helpers for validated post image uploads (stored under static/uploads/posts/)."""
import os
import uuid

from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'webp', 'gif'})
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MiB


def save_post_image(upload_file, upload_folder: str) -> str | None:
    """
    Save uploaded image with a random filename. Returns stored filename or None if no file.
    Raises ValueError on invalid type or size.
    """
    if not upload_file or not getattr(upload_file, 'filename', None):
        return None
    raw = secure_filename(upload_file.filename)
    if not raw or '.' not in raw:
        raise ValueError('Please choose a valid image file.')
    ext = raw.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Allowed types: PNG, JPG, JPEG, WebP, GIF.')
    upload_file.seek(0, os.SEEK_END)
    size = upload_file.tell()
    upload_file.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise ValueError('Image is too large (maximum 2 MB).')
    os.makedirs(upload_folder, exist_ok=True)
    name = f'{uuid.uuid4().hex}.{ext}'
    upload_file.save(os.path.join(upload_folder, name))
    return name


def delete_post_image(upload_folder: str, filename: str | None) -> None:
    if not filename:
        return
    path = os.path.join(upload_folder, filename)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def save_avatar_image(upload_file, upload_folder: str) -> str | None:
    """
    Save uploaded avatar with a random filename. Returns stored filename or None if no file.
    Raises ValueError on invalid type or size.
    """
    return save_post_image(upload_file, upload_folder)


def delete_avatar_image(upload_folder: str, filename: str | None) -> None:
    delete_post_image(upload_folder, filename)
