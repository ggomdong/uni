// static/wtm/js/modal_log.js
(function () {
  if (window.__wtmLogModalInitialized) return;
  window.__wtmLogModalInitialized = true;

  function digits6ToHHMMSS(d6) {
    if (!/^\d{6}$/.test(d6)) return null;
    const hh = Number(d6.slice(0,2));
    const mm = Number(d6.slice(2,4));
    const ss = Number(d6.slice(4,6));
    if (hh > 23 || mm > 59 || ss > 59) return null;
    return `${String(hh).padStart(2,'0')}:${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
  }

  document.addEventListener('DOMContentLoaded', function () {
    const logModal = document.getElementById('logModal');
    if (!logModal) return;

    const form        = logModal.querySelector('form');
    const modalTitle  = logModal.querySelector('.modal-title');
    const logIdInput  = document.getElementById('logIdInput');
    const userSelect  = document.getElementById('logUserSelect');
    const workCodeI = document.getElementById('workCodeI');
    const workCodeO = document.getElementById('workCodeO');
    const recordTime  = document.getElementById('logRecordTimeInput');

    // 핵심: work_log에선 버튼(data-*)로 열리고, index에선 JS로 열리므로
    // relatedTarget이 없을 때는 logModal.dataset을 fallback으로 사용
    logModal.addEventListener('show.bs.modal', function (event) {
      const btn = event.relatedTarget;

      const mode = (btn && btn.getAttribute('data-mode')) || logModal.dataset.mode || 'create';

      // 버튼에서 읽거나(dataset fallback)
      const data = {
        id:        (btn && btn.getAttribute('data-id')) || logModal.dataset.id || '',
        userId:    (btn && btn.getAttribute('data-user-id')) || logModal.dataset.userId || '',
        workCode:  (btn && btn.getAttribute('data-work-code')) || logModal.dataset.workCode || '',
        recordTime:(btn && btn.getAttribute('data-record-time')) || logModal.dataset.recordTime || '',
      };

      if (mode === 'create') {
        if (modalTitle) modalTitle.textContent = '근태기록 등록';
        if (logIdInput) logIdInput.value = '';
        if (userSelect) { userSelect.disabled = false; }
        if (workCodeI) workCodeI.checked = false;
        if (workCodeO) workCodeO.checked = false;
        if (recordTime) recordTime.value = '';
      } else {
        if (modalTitle) modalTitle.textContent = '근태기록 수정';
        if (logIdInput) logIdInput.value = data.id;
        if (userSelect) { userSelect.value = data.userId; userSelect.disabled = true; }

        const wc = (data.workCode || '').trim();
        if (workCodeI) workCodeI.checked = (wc === 'I');
        if (workCodeO) workCodeO.checked = (wc === 'O');
        if (recordTime) recordTime.value = (data.recordTime || '').substring(0, 8); // "14:56:01"
      }

      // dataset fallback 값은 1회성으로 쓰고 정리
      logModal.dataset.mode = '';
      logModal.dataset.id = '';
      logModal.dataset.userId = '';
      logModal.dataset.workCode = '';
      logModal.dataset.recordTime = '';
    });

    // 숫자 6자리 입력 지원: 145601 -> 14:56:01
    if (recordTime) {
      recordTime.addEventListener('input', function () {
        const raw = this.value.trim();
        if (/^\d{2}:\d{2}:\d{2}$/.test(raw)) return;

        const digits = raw.replace(/\D/g, '').slice(0, 6);
        this.value = digits.length === 6 ? (digits6ToHHMMSS(digits) || digits) : digits;
      });
    }

    // submit 시 최종 검증
    if (form && recordTime) {
      form.addEventListener('submit', function (e) {
        const v = (recordTime.value || '').trim();

        // 숫자 6자리면 변환
        if (/^\d{6}$/.test(v)) {
          const hhmmss = digits6ToHHMMSS(v);
          if (!hhmmss) {
            e.preventDefault();
            showToast('시간이 올바르지 않습니다. 예: 145601 (14:56:01)', 'error');
            recordTime.focus();
            return;
          }
          recordTime.value = hhmmss;
        }

        // 최종적으로 HH:MM:SS만 허용
        if (!/^\d{2}:\d{2}:\d{2}$/.test(recordTime.value)) {
          e.preventDefault();
          showToast('시간은 HH:MM:SS 또는 숫자 6자리(HHMMSS)로 입력하세요.', 'error');
          recordTime.focus();
        }
      });
    }
  });
})();
