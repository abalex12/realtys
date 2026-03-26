// Addis Realty - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // Fade-up animation
  const fadeEls = document.querySelectorAll('.fade-up');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add('visible'), i * 80);
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });
  fadeEls.forEach(el => observer.observe(el));

  // Media Gallery
  initGallery();

  // Upload preview
  initUploadPreview('id_images', 'images-preview', 'image');
  initUploadPreview('id_videos', 'videos-preview', 'video');

  // Type-based form toggle
  initListingFormToggle();

  // Search form live
  initLiveSearch();

  // Delete media
  initDeleteMedia();
});

// ---- GALLERY ----
function initGallery() {
  const gallery = document.querySelector('.media-gallery');
  if (!gallery) return;

  const mediaItems = Array.from(document.querySelectorAll('.gallery-media-item'));
  const thumbs = document.querySelectorAll('.gallery-thumb');
  const counter = gallery.querySelector('.gallery-counter');
  let current = 0;

  function show(idx) {
    current = (idx + mediaItems.length) % mediaItems.length;
    mediaItems.forEach((m, i) => m.style.display = i === current ? 'block' : 'none');
    thumbs.forEach((t, i) => t.classList.toggle('active', i === current));
    if (counter) counter.textContent = `${current + 1} / ${mediaItems.length}`;
    // Pause videos when not active
    mediaItems.forEach((m, i) => {
      const vid = m.querySelector('video');
      if (vid && i !== current) vid.pause();
    });
  }

  const prev = gallery.querySelector('.gallery-nav.prev');
  const next = gallery.querySelector('.gallery-nav.next');
  if (prev) prev.addEventListener('click', () => show(current - 1));
  if (next) next.addEventListener('click', () => show(current + 1));
  thumbs.forEach((t, i) => t.addEventListener('click', () => show(i)));

  // Keyboard nav
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });

  // Touch/swipe
  let startX = 0;
  gallery.addEventListener('touchstart', e => startX = e.touches[0].clientX);
  gallery.addEventListener('touchend', e => {
    const diff = startX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) show(diff > 0 ? current + 1 : current - 1);
  });

  show(0);
}

// ---- UPLOAD PREVIEW ----
function initUploadPreview(inputId, previewId, type) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  if (!input || !preview) return;

  input.addEventListener('change', function() {
    preview.innerHTML = '';
    Array.from(this.files).forEach(file => {
      const item = document.createElement('div');
      item.className = 'preview-item';
      const removeBtn = document.createElement('button');
      removeBtn.className = 'preview-remove';
      removeBtn.innerHTML = '✕';
      removeBtn.type = 'button';
      if (type === 'image') {
        const img = document.createElement('img');
        const reader = new FileReader();
        reader.onload = e => img.src = e.target.result;
        reader.readAsDataURL(file);
        item.appendChild(img);
      } else {
        const vid = document.createElement('video');
        vid.src = URL.createObjectURL(file);
        item.appendChild(vid);
      }
      item.appendChild(removeBtn);
      preview.appendChild(item);
    });
  });

  // Drag over
  const zone = input.closest('.upload-zone');
  if (zone) {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over'); input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); });
  }
}

// ---- FORM TOGGLE ----
function initListingFormToggle() {
  const typeSelect = document.getElementById('id_listing_type');
  if (!typeSelect) return;
  const houseFields = document.getElementById('house-fields');
  const carFields = document.getElementById('car-fields');

  function toggle() {
    if (!houseFields || !carFields) return;
    const v = typeSelect.value;
    houseFields.style.display = v === 'house' ? '' : 'none';
    carFields.style.display = v === 'car' ? '' : 'none';
  }
  typeSelect.addEventListener('change', toggle);
  toggle();
}

// ---- LIVE SEARCH ----
function initLiveSearch() {
  const form = document.getElementById('search-form');
  if (!form) return;
  const selects = form.querySelectorAll('select');
  selects.forEach(s => {
    s.addEventListener('change', () => {
      // Visual feedback
    });
  });
}

// ---- DELETE MEDIA ----
function initDeleteMedia() {
  document.querySelectorAll('.btn-delete-media').forEach(btn => {
    btn.addEventListener('click', async function() {
      const mediaId = this.dataset.id;
      const item = this.closest('.existing-media-item');
      if (!confirm('Remove this media?')) return;

      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      const token = csrfToken ? csrfToken.value : '';

      const resp = await fetch(`/media/delete/${mediaId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': token, 'Content-Type': 'application/json' }
      });
      const data = await resp.json();
      if (data.success && item) item.remove();
    });
  });
}

// ---- DISMISS ALERTS ----
setTimeout(() => {
  document.querySelectorAll('.auto-dismiss').forEach(el => {
    el.style.transition = 'opacity 0.5s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  });
}, 4000);

// ---- REJECT MODAL ----
function openRejectModal(slug) {
  document.getElementById('reject-slug').value = slug;
  const modal = new bootstrap.Modal(document.getElementById('rejectModal'));
  modal.show();
}
