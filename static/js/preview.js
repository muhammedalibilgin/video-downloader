document.addEventListener('DOMContentLoaded', function() {
    const previewForm = document.getElementById('previewForm');
    const skeletonContainer = document.getElementById('skeletonContainer');
    const videoPreview = document.getElementById('videoPreview');
    const urlInput = document.querySelector('input[name="url"]');

    previewForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const url = urlInput.value.trim();
        if (!url) {
            return;
        }

        // Skeleton'ı göster
        showSkeleton();
        
        // Form verilerini gönder
        const formData = new FormData();
        formData.append('url', url);

        fetch('/preview', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(html => {
            // Gelen HTML'i parse et ve preview kısmını güncelle
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newVideoPreview = doc.getElementById('videoPreview');
            const newAlerts = doc.querySelector('.alert');
            
            // Skeleton'ı gizle
            hideSkeleton();
            
            // Alert varsa göster
            if (newAlerts) {
                // Mevcut alert'leri temizle
                document.querySelectorAll('.alert').forEach(alert => alert.remove());
                // Yeni alert'i ekle
                videoPreview.parentNode.insertBefore(newAlerts, videoPreview.nextSibling);
            }
            
            // Video preview varsa güncelle
            if (newVideoPreview && newVideoPreview.innerHTML.trim()) {
                videoPreview.innerHTML = newVideoPreview.innerHTML;
                videoPreview.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Preview hatası:', error);
            hideSkeleton();
            // Hata mesajı göster
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert';
            alertDiv.textContent = 'Video önizlenemedi. Lütfen tekrar deneyin.';
            videoPreview.parentNode.insertBefore(alertDiv, videoPreview.nextSibling);
        });
    });

    function showSkeleton() {
        if (skeletonContainer) {
            skeletonContainer.style.display = 'block';
        }
        if (videoPreview) {
            videoPreview.style.display = 'none';
        }
        // Mevcut alert'leri temizle
        document.querySelectorAll('.alert').forEach(alert => alert.remove());
    }

    function hideSkeleton() {
        if (skeletonContainer) {
            skeletonContainer.style.display = 'none';
        }
    }
});
