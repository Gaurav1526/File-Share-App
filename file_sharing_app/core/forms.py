from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import File, ShareLink
from django.core.exceptions import ValidationError
from django.conf import settings

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['file']
    
    def clean_file(self):
        file = self.cleaned_data['file']
        self.validate_file(file)
        return file
    
    def validate_file(self, file):
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

class ShareSettingsForm(forms.ModelForm):
    class Meta:
        model = ShareLink
        fields = ['expires_at', 'password', 'max_downloads']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'password': forms.PasswordInput(render_value=True),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].required = False