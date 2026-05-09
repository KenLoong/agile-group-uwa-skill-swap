/**
 * conversation.js – Private messaging conversation page
 *
 *  - Sends messages via POST /api/messages/<username>  (AJAX JSON)
 *  - Polls for new messages via GET /api/messages/poll/<username>?after=<id>
 *    every 4 seconds
 *  - Auto-grows the textarea, auto-scrolls to latest message
 *  - Enter to send, Shift+Enter for a newline
 */

(function () {
    'use strict';

    var form     = document.getElementById('send-form');
    if (!form) { return; }

    var input    = document.getElementById('msg-input');
    var sendBtn  = document.getElementById('send-btn');
    var errEl    = document.getElementById('send-error');
    var chatBox  = document.getElementById('chat-messages');
    var emptyEl  = document.getElementById('chat-empty-hint');

    var sendUrl  = form.dataset.sendUrl;
    var pollUrl  = form.dataset.pollUrl;
    var lastId   = parseInt(form.dataset.lastId || '0', 10);
    var myName   = form.dataset.myUsername || '';

    /* ------------------------------------------------------------------
       Helpers
    ------------------------------------------------------------------ */

    function esc(s) {
        return $('<div>').text(s == null ? '' : String(s)).html();
    }

    function scrollBottom() {
        if (chatBox) { chatBox.scrollTop = chatBox.scrollHeight; }
    }

    function showError(msg) {
        if (!errEl) { return; }
        errEl.textContent = msg || '';
        errEl.classList.toggle('d-none', !msg);
    }

    function autoGrow(el) {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }

    /* Build a single chat bubble element */
    function makeBubble(msg) {
        var isMine = msg.is_mine || msg.sender === myName;
        var wrap   = document.createElement('div');
        wrap.className = 'd-flex ' + (isMine ? 'justify-content-end' : 'justify-content-start');
        wrap.dataset.msgId = msg.id;

        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + (isMine ? 'chat-bubble-mine' : 'chat-bubble-theirs');

        if (!isMine) {
            var senderEl = document.createElement('span');
            senderEl.className   = 'chat-sender';
            senderEl.textContent = msg.sender;
            bubble.appendChild(senderEl);
        }

        var body = document.createElement('p');
        body.style.cssText  = 'white-space:pre-wrap;margin-bottom:0.15rem;';
        body.textContent    = msg.content;
        bubble.appendChild(body);

        var time = document.createElement('span');
        time.className   = 'chat-time';
        time.textContent = msg.timestamp;
        bubble.appendChild(time);

        wrap.appendChild(bubble);
        return wrap;
    }

    function appendMessages(msgs) {
        if (!msgs || !msgs.length) { return; }
        if (emptyEl) { emptyEl.remove(); emptyEl = null; }
        msgs.forEach(function (m) {
            chatBox.appendChild(makeBubble(m));
            if (m.id > lastId) { lastId = m.id; }
        });
        scrollBottom();
    }

    /* ------------------------------------------------------------------
       Send message
    ------------------------------------------------------------------ */

    function sendMessage() {
        var text = input ? input.value.trim() : '';
        if (!text) { input && input.focus(); return; }

        showError('');
        sendBtn.disabled = true;

        $.ajax({
            url:         sendUrl,
            method:      'POST',
            contentType: 'application/json',
            data:        JSON.stringify({ content: text }),
        })
            .done(function (data) {
                if (!data.ok) { showError(data.message || 'Could not send.'); return; }
                appendMessages([data]);
                input.value    = '';
                input.style.height = 'auto';
                input.focus();
            })
            .fail(function (xhr) {
                var msg = (xhr.responseJSON && xhr.responseJSON.message)
                    ? xhr.responseJSON.message : 'Failed to send message.';
                showError(msg);
            })
            .always(function () { sendBtn.disabled = false; });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        sendMessage();
    });

    if (input) {
        /* Enter = send, Shift+Enter = newline */
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        /* Auto-grow textarea */
        input.addEventListener('input', function () { autoGrow(this); });
    }

    /* ------------------------------------------------------------------
       Polling (every 4 s)
    ------------------------------------------------------------------ */

    function poll() {
        $.getJSON(pollUrl, { after: lastId })
            .done(function (msgs) {
                appendMessages(msgs);
            });
    }

    var pollInterval = setInterval(poll, 4000);

    /* Stop polling when page is hidden (battery-friendly) */
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            clearInterval(pollInterval);
        } else {
            poll();   // immediate refresh on return
            pollInterval = setInterval(poll, 4000);
        }
    });

    /* ------------------------------------------------------------------
       Initial scroll to bottom
    ------------------------------------------------------------------ */
    scrollBottom();
    if (input) { input.focus(); }

}());
