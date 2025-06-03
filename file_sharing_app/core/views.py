from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import File, ShareLink, DownloadLog
from .forms import UserRegistrationForm, FileUploadForm, ShareSettingsForm
from .utils import validate_file
from datetime import timedelta
from io import BytesIO
import base64
import qrcode
import uuid
import os





from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse, FileResponse, Http404
from django.db.models.query_utils import Q
from django.utils import timezone




# -------------------------
# User Authentication Views
# -------------------------

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


# -------------------------
# Dashboard and File Views
# -------------------------

@login_required
def dashboard(request):
    files = File.objects.filter(owner=request.user).order_by('-upload_date')[:5]
    total_files = files.count()
    active_shares = ShareLink.objects.filter(file__owner=request.user, is_active=True).count()
    total_downloads = sum(file.download_count for file in files)
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
            ShareLink.objects.update_or_create(
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

    return render(request, 'core/share_settings.html', {'form': form, 'file': file})


@login_required
def share_link(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    share_link = get_object_or_404(ShareLink, file=file)

    share_url = request.build_absolute_uri(reverse('download', args=[share_link.token]))
    qr_img_data = cache.get(f'qr_{share_link.token}')

    if not qr_img_data:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, "PNG")
        qr_img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        cache.set(f'qr_{share_link.token}', qr_img_data, 3600)

    return render(request, 'core/share_link.html', {
        'file': file,
        'share_link': share_link,
        'share_url': share_url,
        'qr_img_data': qr_img_data
    })


def download_qr(request, token):
    share_link = get_object_or_404(ShareLink, token=token)
    share_url = request.build_absolute_uri(reverse('download', args=[token]))
    qr_data = cache.get(f'qr_{token}')

    if not qr_data:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, "PNG")
        qr_data = buffer.getvalue()
        cache.set(f'qr_{token}', qr_data, 3600)

    response = HttpResponse(qr_data, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="fileshare_qr_{token}.png"'
    return response


def protected_download(request, token):
    share_link = get_object_or_404(ShareLink, token=token)
    file = share_link.file

    if not share_link.is_active:
        return render(request, 'core/download.html', {'error': 'This link has expired'})

    if share_link.password:
        if request.method == 'POST':
            if request.POST.get('password') != share_link.password:
                return render(request, 'core/password_prompt.html', {'error': 'Invalid password'})
        else:
            return render(request, 'core/password_prompt.html')

    if share_link.max_downloads and share_link.download_count >= share_link.max_downloads:
        share_link.is_active = False
        share_link.save()
        return render(request, 'core/download.html', {'error': 'Download limit reached'})

    if share_link.expires_at and share_link.expires_at < timezone.now():
        share_link.is_active = False
        share_link.save()
        return render(request, 'core/download.html', {'error': 'Link has expired'})

    share_link.download_count += 1
    share_link.save()
    file.download_count += 1
    file.save()

    DownloadLog.objects.create(
        file=file,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    return FileResponse(file.file.open(), as_attachment=True, filename=file.original_name)


@login_required
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    file.delete()
    return redirect('file_list')

from .models import File, DownloadLog

@login_required
def view_download_logs(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user)
    logs = DownloadLog.objects.filter(file=file).order_by('-downloaded_at')
    return render(request, 'core/download_logs.html', {'logs': logs})



# -------------------------
# Password Reset (Function-Based Views)
# -------------------------

def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "core/password_reset_email.html"
                    context = {
                        "email": user.email,
                        "domain": request.META['HTTP_HOST'],
                        "site_name": "SecureShare",
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        "token": default_token_generator.make_token(user),
                        "protocol": 'https',
                    }
                    email = render_to_string(email_template_name, context)
                    try:
                        send_mail(subject, email, 'admin@secureshare.com', [user.email], fail_silently=False)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                return redirect('password_reset_done')
    password_reset_form = PasswordResetForm()
    return render(request, 'core/password_reset.html', {'form': password_reset_form})

def password_reset_done(request):
    return render(request, 'core/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        return render(request, 'core/password_reset_confirm.html', {'form': form})
    else:
        return HttpResponse('Password reset link is invalid!')

def password_reset_complete(request):
    return render(request, 'core/password_reset_complete.html')


