// Trellis — minimal app JS
// HTMX is loaded via CDN in base.html

// Configure HTMX to send JSON content-type on JSON-like requests
document.addEventListener('htmx:configRequest', (evt) => {
  // If the element has data-json attribute, send as JSON
  if (evt.detail.elt.dataset.json) {
    evt.detail.headers['Content-Type'] = 'application/json';
  }
});

// Auto-dismiss flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  const flash = document.getElementById('flash-messages');
  if (flash) {
    setTimeout(() => {
      flash.style.transition = 'opacity 0.5s ease';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 500);
    }, 4000);
  }
});
