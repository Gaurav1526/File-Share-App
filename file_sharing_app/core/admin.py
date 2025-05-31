
# Register your models here.
from django.contrib import admin
from .models import File, ShareLink, DownloadLog

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'owner', 'file_type', 'size', 'upload_date')
    list_filter = ('file_type', 'upload_date')
    search_fields = ('original_name', 'owner__username')
    readonly_fields = ('size', 'file_type')

@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ('file', 'token', 'is_active', 'download_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('file__original_name', 'token')

@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('file', 'downloaded_at', 'ip_address')
    list_filter = ('downloaded_at',)
    search_fields = ('file__original_name', 'ip_address')