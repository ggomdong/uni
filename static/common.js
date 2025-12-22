(function (global) {
  function showToast(message, level = 'info') {
    const bgClass =
      level === 'success' ? 'text-bg-success' :
      level === 'error'   ? 'text-bg-danger'  :
      level === 'warning' ? 'text-bg-warning' :
                            'text-bg-info';

    let container = document.querySelector('.toast-container.position-fixed.top-0.start-50.translate-middle-x');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container position-fixed top-0 start-50 translate-middle-x p-3';
      container.style.zIndex = '1100';
      container.style.marginTop = '60px';
      document.body.appendChild(container);
    }

    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <div class="toast align-items-center border-0 ${bgClass}"
           role="alert" aria-live="assertive" aria-atomic="true"
           data-bs-delay="3000" data-bs-autohide="true">
        <div class="d-flex">
          <div class="toast-body"></div>
          <button type="button"
                  class="btn-close btn-close-white me-2 m-auto"
                  data-bs-dismiss="toast"
                  aria-label="Close"></button>
        </div>
      </div>
    `;
    const toastEl = wrapper.firstElementChild;
    toastEl.querySelector('.toast-body').textContent = message;
    container.appendChild(toastEl);

    if (!global.bootstrap || !global.bootstrap.Toast) {
      // Bootstrap JS가 없으면 안전하게 fallback
      console.warn('Bootstrap Toast not found. Falling back to alert().');
      alert(message);
      return;
    }

    const toast = global.bootstrap.Toast.getOrCreateInstance(toastEl);
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }

  // 전역에 노출
  global.showToast = showToast;
})(window);