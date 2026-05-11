/**
 * conversation.js – Private messaging conversation page
 *
 * WebSocket is used as the primary path through Flask-SocketIO.
 * Existing AJAX polling remains as a fallback when Socket.IO is unavailable.
 */

(function () {
    'use strict';

    var form = document.getElementById('send-form');
    if (!form) { return; }

    var input = document.getElementById('msg-input');
    var sendBtn = document.getElementById('send-btn');
    var errEl = document.getElementById('send-error');
    var chatBox = document.getElementById('chat-messages');
    var emptyEl = document.getElementById('chat-empty-hint');

    var sendUrl = form.dataset.sendUrl;
    var pollUrl = form.dataset.pollUrl;
    var lastId = parseInt(form.dataset.lastId || '0', 10);
    var myName = form.dataset.myUsername || '';
    var partnerName = form.dataset.partnerUsername || '';

    var socket = null;
    var socketReady = false;
    var pollInterval = null;

    function scrollBottom() {
        if (chatBox) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
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

    function makeBubble(msg) {
        var isMine = msg.is_mine || msg.sender === myName;

        var wrap = document.createElement('div');
        wrap.className = 'd-flex ' + (isMine ? 'justify-content-end' : 'justify-content-start');
        wrap.dataset.msgId = msg.id;

        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble ' + (isMine ? 'chat-bubble-mine' : 'chat-bubble-theirs');

        if (!isMine) {
            var senderEl = document.createElement('span');
            senderEl.className = 'chat-sender';
            senderEl.textContent = msg.sender || partnerName;
            bubble.appendChild(senderEl);
        }

        var body = document.createElement('p');
        body.style.cssText = 'white-space:pre-wrap;margin-bottom:0.15rem;';
        body.textContent = msg.content || '';
        bubble.appendChild(body);

        var time = document.createElement('span');
        time.className = 'chat-time';
        time.textContent = msg.timestamp || '';
        bubble.appendChild(time);

        wrap.appendChild(bubble);
        return wrap;
    }

    function appendMessages(msgs) {
        if (!msgs || !msgs.length) { return; }

        if (emptyEl) {
            emptyEl.remove();
            emptyEl = null;
        }

        msgs.forEach(function (m) {
            if (!m || !m.id) { return; }

            if (chatBox.querySelector('[data-msg-id="' + m.id + '"]')) {
                return;
            }

            chatBox.appendChild(makeBubble(m));

            if (m.id > lastId) {
                lastId = m.id;
            }
        });

        scrollBottom();
    }

    function sendViaAjax(text) {
        $.ajax({
            url: sendUrl,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ content: text })
        })
            .done(function (data) {
                if (!data.ok) {
                    showError(data.message || 'Could not send.');
                    return;
                }

                appendMessages([data]);
                input.value = '';
                input.style.height = 'auto';
                input.focus();
            })
            .fail(function (xhr) {
                var msg = (xhr.responseJSON && xhr.responseJSON.message)
                    ? xhr.responseJSON.message
                    : 'Failed to send message.';
                showError(msg);
            })
            .always(function () {
                sendBtn.disabled = false;
            });
    }

    function sendViaSocket(text) {
        socket.emit(
            'messages:send',
            {
                username: partnerName,
                content: text
            },
            function (ack) {
                sendBtn.disabled = false;

                if (!ack || !ack.ok) {
                    showError((ack && ack.message) || 'Could not send message.');
                    return;
                }

                input.value = '';
                input.style.height = 'auto';
                input.focus();
            }
        );
    }

    function sendMessage() {
        var text = input ? input.value.trim() : '';

        if (!text) {
            input && input.focus();
            return;
        }

        showError('');
        sendBtn.disabled = true;

        if (socketReady && socket) {
            sendViaSocket(text);
        } else {
            sendViaAjax(text);
        }
    }

    function poll() {
        $.getJSON(pollUrl, { after: lastId })
            .done(function (msgs) {
                appendMessages(msgs);
            });
    }

    function startPollingFallback() {
        if (pollInterval) { return; }

        pollInterval = setInterval(poll, 4000);
    }

    function stopPollingFallback() {
        if (!pollInterval) { return; }

        clearInterval(pollInterval);
        pollInterval = null;
    }

    function initSocket() {
        if (!window.io || !partnerName) {
            startPollingFallback();
            return;
        }

        socket = window.io('/messages');

        socket.on('connect', function () {
            socketReady = true;
            stopPollingFallback();

            socket.emit('messages:join', {
                username: partnerName
            });
        });

        socket.on('disconnect', function () {
            socketReady = false;
            startPollingFallback();
        });

        socket.on('connect_error', function () {
            socketReady = false;
            startPollingFallback();
        });

        socket.on('messages:ready', function () {
            // Server accepted the socket connection.
        });

        socket.on('messages:joined', function () {
            // Joined the private conversation room.
        });

        socket.on('messages:new', function (msg) {
            appendMessages([msg]);
        });

        socket.on('messages:error', function (payload) {
            showError((payload && payload.message) || 'Realtime messaging error.');
        });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        sendMessage();
    });

    if (input) {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        input.addEventListener('input', function () {
            autoGrow(this);
        });
    }

    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopPollingFallback();
        } else if (!socketReady) {
            poll();
            startPollingFallback();
        }
    });

    scrollBottom();
    if (input) { input.focus(); }

    initSocket();
}());