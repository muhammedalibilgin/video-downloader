document.addEventListener('DOMContentLoaded', function() {
    const previewForm = document.getElementById('previewForm');
    const skeletonContainer = document.getElementById('skeletonContainer');
    const videoPreview = document.getElementById('videoPreview');
    const urlInput = document.querySelector('input[name="url"]');

    // Mevcut download formu için event listener
    const existingDownloadForm = document.getElementById('downloadForm');
    if (existingDownloadForm) {
        setupDownloadHandler(existingDownloadForm);
    }

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
                
                // Yeni eklenen download formu için event listener ekle
                const newDownloadForm = videoPreview.querySelector('#downloadFormDynamic');
                if (newDownloadForm) {
                    setupDownloadHandler(newDownloadForm);
                }
                
                // Mevcut download formu için event listener (varsa)
                const existingForm = videoPreview.querySelector('#downloadForm');
                if (existingForm) {
                    setupDownloadHandler(existingForm);
                }
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

    function setupDownloadHandler(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const url = form.querySelector('input[name="url"]').value;
            const btn = form.querySelector('button[type="submit"]');
            const btnText = btn.querySelector('.btn-text');
            const loader = btn.querySelector('.download-loader');
            const progressContainer = form.parentElement.querySelector('.download-progress');
            const progressFill = progressContainer.querySelector('.progress-fill');
            const progressText = progressContainer.querySelector('.progress-text');
            
            if (!url) {
                return;
            }
            
            // Buton durumunu güncelle
            btnText.style.display = 'none';
            loader.classList.add('active');
            btn.disabled = true;
            
            // Progress bar'ı göster
            progressContainer.classList.add('active');
            progressFill.style.width = '0%';
            progressText.textContent = 'Hazırlanıyor...';
            
            // Form verilerini gönder
            const formData = new FormData();
            formData.append('url', url);
            
            fetch('/download', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('İndirme başarısız oldu');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Progress'i güncelle
                    progressFill.style.width = '25%';
                    progressText.textContent = 'Video bilgileri alınıyor...';
                    
                    // Dosya indirme linkini oluştur
                    return fetch('/get_file/' + data.file_id)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error('Dosya alınamadı');
                            }
                            return response.blob();
                        })
                        .then(blob => {
                            // Progress'i tamamla
                            progressFill.style.width = '100%';
                            progressText.textContent = 'İndirme tamamlandı!';
                            
                            // Dosyayı indir
                            const downloadUrl = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = downloadUrl;
                            a.download = data.filename || 'video.mp4';
                            document.body.appendChild(a);
                            a.click();
                            window.URL.revokeObjectURL(downloadUrl);
                            document.body.removeChild(a);
                            
                            // Butonu eski haline getir
                            btnText.style.display = 'inline';
                            loader.classList.remove('active');
                            btn.disabled = false;
                            
                            // Progress bar'ı gizle
                            setTimeout(() => {
                                progressContainer.classList.remove('active');
                            }, 2000);
                        });
                } else {
                    throw new Error(data.error || 'İndirme başarısız oldu');
                }
            })
            .catch(error => {
                console.error('Download hatası:', error);
                progressText.textContent = 'Hata: ' + error.message;
                
                // Butonu eski haline getir
                btnText.style.display = 'inline';
                loader.classList.remove('active');
                btn.disabled = false;
                
                // Progress bar'ı gizle
                setTimeout(() => {
                    progressContainer.classList.remove('active');
                }, 2000);
                
                // Hata mesajı göster
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert';
                alertDiv.textContent = error.message;
                videoPreview.parentNode.insertBefore(alertDiv, videoPreview.nextSibling);
                
                // Alert'i 5 saniye sonra kaldır
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.parentNode.removeChild(alertDiv);
                    }
                }, 5000);
            });
        });
    }

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
