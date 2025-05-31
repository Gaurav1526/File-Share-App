document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const uploadForm = document.getElementById('uploadForm');
    const passwordProtection = document.getElementById('passwordProtection');
    const passwordField = document.getElementById('passwordField');
    const selectFilesBtn = document.getElementById('selectFilesBtn');
    const uploadBtn = document.getElementById('uploadBtn');
  
    // Toggle password field
    if (passwordProtection) {
      passwordProtection.addEventListener('change', function() {
        passwordField.classList.toggle('d-none', !this.checked);
      });
    }
  
    // File selection handling
    if (selectFilesBtn) {
      selectFilesBtn.addEventListener('click', function(e) {
        e.preventDefault();
        fileInput.click();
      });
    }
  
    // Drag and drop handling
    if (dropZone) {
      // Event handlers
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
      });
  
      ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
      });
  
      ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
      });
  
      dropZone.addEventListener('drop', handleDrop, false);
    }
  
    // File input change handling
    if (fileInput) {
      fileInput.addEventListener('change', function() {
        handleFiles(this.files);
      });
    }
  
    // Form submission handling
    if (uploadForm && uploadBtn) {
      uploadForm.addEventListener('submit', handleFormSubmit);
    }
  
    // Helper functions
    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }
  
    function highlight() {
      dropZone.classList.add('border-primary');
    }
  
    function unhighlight() {
      dropZone.classList.remove('border-primary');
    }
  
    function handleDrop(e) {
      const dt = e.dataTransfer;
      const files = dt.files;
      handleFiles(files);
    }
  
    function handleFiles(files) {
      if (!filePreview) return;
      
      filePreview.innerHTML = '';
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item d-flex align-items-center mb-2';
        fileElement.innerHTML = `
          <div class="flex-grow-1">
            <div class="file-name">${escapeHtml(file.name)}</div>
            <div class="file-size text-muted">${formatFileSize(file.size)}</div>
          </div>
        `;
        filePreview.appendChild(fileElement);
      }
    }
  
    function formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  
    function escapeHtml(unsafe) {
      return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }
  
    function handleFormSubmit(e) {
      e.preventDefault();
      
      // Show loading state
      const originalText = uploadBtn.innerHTML;
      uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Uploading...';
      uploadBtn.disabled = true;
  
      const formData = new FormData(uploadForm);
      const files = fileInput.files;
      
      // Append files to form data
      for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
      }
  
      // Get upload URL
      const uploadUrl = uploadForm.getAttribute('data-upload-url');
  
      // Send request
      fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        }
      })
      .then(response => {
        // First get content type
        const contentType = response.headers.get('content-type');
        
        // Handle JSON response
        if (contentType && contentType.includes('application/json')) {
          return response.json();
        }
        
        // Handle HTML response (server error page)
        return response.text().then(text => {
          // Create a temporary DOM element to parse the HTML
          const parser = new DOMParser();
          const doc = parser.parseFromString(text, 'text/html');
          
          // Try to extract error message from common elements
          const errorElement = doc.querySelector('.error') || 
                               doc.querySelector('.exception_value') ||
                               doc.querySelector('h1');
          
          const errorMessage = errorElement ? errorElement.textContent.trim() : 
                               `Server error: ${response.status} ${response.statusText}`;
          
          throw new Error(errorMessage.substring(0, 200));
        });
      })
      .then(data => {
        if (data.success && data.redirect_url) {
          window.location.href = data.redirect_url;
        } else if (data.error) {
          throw new Error(data.error);
        } else {
          throw new Error('Invalid server response format');
        }
      })
      .catch(error => {
        console.error('Upload error:', error);
        
        // More user-friendly error message
        let errorMessage = error.message;
        
        // Clean up Django debug messages
        if (errorMessage.includes('You have error')) {
          errorMessage = 'Server error: Please try again later';
        }
        else if (errorMessage.includes('CSRF')) {
          errorMessage = 'Session expired. Please refresh the page and try again.';
        }
        else if (errorMessage.includes('<!DOCTYPE')) {
          errorMessage = 'Server error: Please check the console for details';
        }
        
        // Show error in UI instead of alert
        showErrorToast(`Upload failed: ${errorMessage}`);
      })
      .finally(() => {
        // Reset button state
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
      });
    }
  
    function showErrorToast(message) {
      // Create or use existing toast container
      let toastContainer = document.getElementById('toast-container');
      if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.position = 'fixed';
        toastContainer.style.bottom = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '10000';
        document.body.appendChild(toastContainer);
      }
  
      // Create toast element
      const toast = document.createElement('div');
      toast.className = 'toast bg-danger text-white show';
      toast.style.maxWidth = '350px';
      toast.innerHTML = `
        <div class="toast-header bg-danger text-white">
          <strong class="me-auto">Error</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${escapeHtml(message)}</div>
      `;
  
      // Add close functionality
      toast.querySelector('.btn-close').addEventListener('click', () => {
        toast.remove();
      });
  
      // Auto-remove after 5 seconds
      setTimeout(() => {
        if (toast.parentNode) toast.remove();
      }, 5000);
  
      toastContainer.appendChild(toast);
    }
  });