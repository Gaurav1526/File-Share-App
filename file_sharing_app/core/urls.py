from django.urls import path
from . import views


urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    # Authentication
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.user_login, name='login'),
    path('auth/logout/', views.user_logout, name='logout'),
    # Files
    path('files/', views.file_list, name='file_list'),
    path('files/upload/', views.file_upload, name='upload'),
    # Consistent file actions
    path('files/<int:file_id>/share/', views.generate_share_link, name='generate_share_link'),
    path('files/<int:file_id>/delete/', views.delete_file, name='delete_file'),  # Fixed
    path('files/<int:file_id>/share-link/', views.share_link, name='share_link'),  # Fixed
    # Download
    path('d/<uuid:token>/', views.protected_download, name='download'),
    # Add the new QR download route
path('qr/<uuid:token>/', views.download_qr, name='download_qr'),
  path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete, name='password_reset_complete'),
     path('download-logs/<int:file_id>/', views.view_download_logs, name='download_logs'),
]