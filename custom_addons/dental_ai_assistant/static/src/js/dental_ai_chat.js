/** Dental AI chat frontend (Odoo 18, website) */
(function () {
  // Ensure Odoo globals exist
  const getCSRFToken = () => (window.odoo && window.odoo.csrf_token) || '';

  // Elements
  const onReady = (fn) => {
    if (document.readyState !== 'loading') return fn();
    document.addEventListener('DOMContentLoaded', fn);
  };

  onReady(() => {
    const chatBtn   = document.getElementById('dentalAiChatBtn');
    const modalEl   = document.getElementById('dentalAiChatModal');
    const chatWin   = document.getElementById('dentalAiChatWindow');
    const inputEl   = document.getElementById('dentalAiInput');
    const sendBtn   = document.getElementById('dentalAiSend');
    const loadingEl = document.getElementById('dentalAiLoading');

    if (!chatBtn || !modalEl || !chatWin || !inputEl || !sendBtn) return;

    // Bootstrap modal
    let bsModal = null;
    const ensureModal = () => {
      if (!bsModal) {
        bsModal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });
      }
      return bsModal;
    };

    // UI helpers
    const scrollToBottom = () => chatWin.scrollTop = chatWin.scrollHeight;

    const addMessage = (who, html) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'dental-ai-msg ' + (who === 'user' ? 'from-user' : 'from-ai');
      wrapper.innerHTML = html;
      chatWin.appendChild(wrapper);
      scrollToBottom();
    };

    const setLoading = (isLoading) => {
      loadingEl.classList.toggle('d-none', !isLoading);
      sendBtn.disabled = isLoading;
      inputEl.disabled = isLoading;
    };

    // Open modal on button click
    chatBtn.addEventListener('click', () => {
      ensureModal().show();
      setTimeout(() => inputEl.focus(), 250);
    });

    // Send action
    const send = async () => {
      const text = (inputEl.value || '').trim();
      if (!text) return;

      addMessage('user', `<div class="bubble"><strong>You:</strong> ${escapeHtml(text)}</div>`);
      inputEl.value = '';
      setLoading(true);

      try {
        const res = await fetch('/dental-ai/ask', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
          },
          body: JSON.stringify({ query: text }),
          credentials: 'same-origin',
        });

        const data = await res.json();
        if (!data || !data.success) {
          const err = (data && data.error) ? data.error : 'Something went wrong.';
          addMessage('ai', `<div class="bubble error"><strong>AI:</strong> ${escapeHtml(err)}</div>`);
          setLoading(false);
          return;
        }

        // Render AI reply (recommendation can be HTML-ish; we’ll trust minimal markup)
        const recHtml = (data.recommendation || '').trim() || 'No recommendation returned.';
        const sources = (data.sources || []).join(', ');
        const sourcesHtml = sources ? `<div class="ai-sources"><em>Sources:</em> ${escapeHtml(sources)}</div>` : '';

        addMessage('ai', `<div class="bubble">
          <strong>AI:</strong><div class="ai-content">${recHtml}</div>${sourcesHtml}
        </div>`);
      } catch (e) {
        addMessage('ai', `<div class="bubble error"><strong>AI:</strong> ${escapeHtml(e.message || 'Network error')}</div>`);
      } finally {
        setLoading(false);
      }
    };

    // Button + Enter to send
    sendBtn.addEventListener('click', send);
    inputEl.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && !ev.shiftKey) {
        ev.preventDefault();
        send();
      }
    });

    // Basic HTML escape
    function escapeHtml(str) {
      return String(str)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }
  });
})();
