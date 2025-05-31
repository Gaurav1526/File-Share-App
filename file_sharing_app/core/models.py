from django.db import models

# Create your models here.
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

def file_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', new_filename)

class File(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=file_upload_path)
    original_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    size = models.PositiveBigIntegerField()
    file_type = models.CharField(max_length=50)
    download_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.original_name
    
    def get_absolute_url(self):
        return reverse('download', args=[self.sharelink.token])
    
    @property
    def is_active(self):
        if hasattr(self, 'sharelink'):
            return self.sharelink.is_active
        return False
    
    def delete(self, *args, **kwargs):
        # Delete file from storage
        storage, path = self.file.storage, self.file.path
        super().delete(*args, **kwargs)
        storage.delete(path)

class ShareLink(models.Model):
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name='sharelink')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Share link for {self.file.original_name}"
    
    def save(self, *args, **kwargs):
        # Deactivate link if expired
        if self.expires_at and self.expires_at < timezone.now():
            self.is_active = False
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return self.expires_at and self.expires_at < timezone.now()
    
    def increment_download(self):
        self.download_count += 1
        self.save()
        self.file.download_count += 1
        self.file.save()

class DownloadLog(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='download_logs')
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Download of {self.file.original_name} at {self.downloaded_at}"