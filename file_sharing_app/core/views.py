from django.shortcuts import render
from django.db import models
from django.core.cache import cache
from django.http import HttpResponse
import os
import uuid
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.urls import reverse
from .models import File, ShareLink, DownloadLog
from .forms import UserRegistrationForm, FileUploadForm, ShareSettingsForm
from .utils import validate_file
from datetime import timedelta
import qrcode
from io import BytesIO

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'core/login.html', {'error': 'Invalid credentials'})
    return render(request, 'core/login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    files = File.objects.filter(owner=request.user).order_by('-upload_date')[:5]
    total_files = File.objects.filter(owner=request.user).count()
    active_shares = ShareLink.objects.filter(file__owner=request.user, is_active=True).count()
    total_downloads = sum(file.download_count for file in File.objects.filter(owner=request.user))
    
    # Calculate storage used
    storage_used = File.objects.filter(owner=request.user).aggregate(
        total_size=models.Sum('size')
    )['total_size'] or 0
    
    return render(request, 'core/dashboard.html', {
        'recent_files': files,
        'total_files': total_files,
        'active_shares': active_shares,
        'total_downloads': total_downloads,
        'storage_used': storage_used,
    })

@login_required
def file_list(request):
    files = File.objects.filter(owner=request.user).order_by('-upload_date')
    return render(request, 'core/file_list.html', {'files': files})

@login_required
def file_upload(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_instance = form.save(commit=False)
            file_instance.owner = request.user
            file_instance.original_name = file_instance.file.name
            file_instance.size = file_instance.file.size
            file_instance.file_type = file_instance.file.name.split('.')[-1].lower()
            file_instance.save()
            
            # Create share link
            expires_at = None
            if request.POST.get('expires_at'):
                days = int(request.POST.get('expires_at'))
                expires_at = timezone.now() + timedelta(days=days)
            
            password = request.POST.get('password') or None
            max_downloads = request.POST.get('max_downloads') or None
            
            ShareLink.objects.create(
                file=file_instance,
                expires_at=expires_at,
                password=password,
                max_downloads=max_downloads
            )
            
            return redirect('generate_share_link', file_id=file_instance.id)
    else:
        form = FileUploadForm()
    return render(request, 'core/upload.html', {'form': form})

@login_required
def generate_share_link(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    
    if request.method == 'POST':
        form = ShareSettingsForm(request.POST)
        if form.is_valid():
            # Update existing share link or create new
            share_link, created = ShareLink.objects.update_or_create(
                file=file,
                defaults={
                    'expires_at': form.cleaned_data['expires_at'],
                    'password': form.cleaned_data['password'],
                    'max_downloads': form.cleaned_data['max_downloads'],
                    'is_active': True
                }
            )
            return redirect('share_link', file_id=file.id)
    else:
        try:
            share_link = ShareLink.objects.get(file=file)
            form = ShareSettingsForm(instance=share_link)
        except ShareLink.DoesNotExist:
            form = ShareSettingsForm()
    
    return render(request, 'core/share_settings.html', {
        'form': form, 
        'file': file
    })

@login_required
def share_link(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    share_link = get_object_or_404(ShareLink, file=file)
    
    # Generate absolute URL for sharing
    share_url = request.build_absolute_uri(
        reverse('download', args=[share_link.token])
    )
    
    # Check cache for existing QR code
    qr_img_data = cache.get(f'qr_{share_link.token}')
    
    if not qr_img_data:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer and encode as base64
        buffer = BytesIO()
        img.save(buffer, "PNG")
        qr_img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Cache for 1 hour (3600 seconds)
        cache.set(f'qr_{share_link.token}', qr_img_data, 3600)
    return render(request, 'core/share_link.html', {
        'file': file,
        'share_link': share_link,
        'share_url': share_url,  # Make sure this exists
        'qr_img_data': qr_img_data  # And this too
    })

def download_qr(request, token):
    # Get share link
    share_link = get_object_or_404(ShareLink, token=token)
    
    # Generate absolute URL for sharing
    share_url = request.build_absolute_uri(
        reverse('download', args=[share_link.token])
    )
    
    # Check cache for existing QR code
    qr_data = cache.get(f'qr_{token}')
    
    if not qr_data:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, "PNG")
        qr_data = buffer.getvalue()
        
        # Cache for 1 hour (3600 seconds)
        cache.set(f'qr_{token}', qr_data, 3600)
    
    # Create HTTP response
    response = HttpResponse(qr_data, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="fileshare_qr_{token}.png"'
    return response

def protected_download(request, token):
    share_link = get_object_or_404(ShareLink, token=token)
    file = share_link.file
    
    # Check if link is active
    if not share_link.is_active:
        return render(request, 'core/download.html', {
            'error': 'This link has expired'
        })
    
    # Check password
    if share_link.password:
        if request.method == 'POST':
            if request.POST.get('password') != share_link.password:
                return render(request, 'core/password_prompt.html', {
                    'error': 'Invalid password'
                })
        else:
            return render(request, 'core/password_prompt.html')
    
    # Check download limits
    if share_link.max_downloads and share_link.download_count >= share_link.max_downloads:
        share_link.is_active = False
        share_link.save()
        return render(request, 'core/download.html', {
            'error': 'Download limit reached'
        })
    
    # Check expiration
    if share_link.expires_at and share_link.expires_at < timezone.now():
        share_link.is_active = False
        share_link.save()
        return render(request, 'core/download.html', {
            'error': 'Link has expired'
        })
    
    # Increment download counts
    share_link.download_count += 1
    share_link.save()
    file.download_count += 1
    file.save()
    
    # Log download
    DownloadLog.objects.create(
        file=file,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Serve file
    response = FileResponse(file.file.open(), as_attachment=True, filename=file.original_name)
    return response

@login_required
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    file.delete()
    return redirect('file_list')