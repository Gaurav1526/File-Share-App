// share.js - Share functionality
document.addEventListener('DOMContentLoaded', function() {
    // Copy to clipboard
    const copyBtn = document.getElementById('copyBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const shareLink = document.getElementById('shareLink');
            shareLink.select();
            document.execCommand('copy');
            
            // Show feedback
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
            
            setTimeout(() => {
                copyBtn.innerHTML = originalHTML;
            }, 2000);
        });
    }
    
    // Download QR code
    const downloadQR = document.getElementById('downloadQR');
    if (downloadQR) {
        downloadQR.addEventListener('click', function() {
            const canvas = document.querySelector('#qrcode canvas');
            if (canvas) {
                const link = document.createElement('a');
                link.download = 'fileshare-qrcode.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }
        });
    }
});