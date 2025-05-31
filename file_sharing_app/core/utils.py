from django.core.exceptions import ValidationError
from django.conf import settings

def validate_file(file):
    # Size validation
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"File too large. Max size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # File type validation
    ext = file.name.split('.')[-1].lower()
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise ValidationError(
            f"Unsupported file type. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
        )