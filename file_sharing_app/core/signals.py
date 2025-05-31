
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import DownloadLog

@receiver(post_save, sender=DownloadLog)
def send_download_notification(sender, instance, created, **kwargs):
    if created:
        subject = f"Your file was downloaded: {instance.file.original_name}"
        message = f"File '{instance.file.original_name}' was downloaded at {instance.downloaded_at}"
        recipient_list = [instance.file.owner.email]
        send_mail(subject, message, 'noreply@fileshare.com', recipient_list)