/**
 * post_detail.js – Post detail page
 *
 * Handles:
 *  - "I'm interested" button → POST /interest/<id>
 *  - Like toggle button      → POST /post/<id>/like
 *  - Bookmark toggle button  → POST /post/<id>/bookmark
 *  - Comment form submit     → AJAX POST, then appends new comment to DOM
 *  - @mention autocomplete   → dropdown while typing @username in comment box
 *
 * All POST endpoints are protected by a global CSRF header set up in base.html.
 */

(function () {
    'use strict';

    /* ------------------------------------------------------------------
       Interest button
    ------------------------------------------------------------------ */
    var interestBtn = document.getElementById('interest-btn');
    if (interestBtn && !interestBtn.disabled) {
        var interestCountEl = document.getElementById('interest-count-label');

        interestBtn.addEventListener('click', function () {
            if (interestBtn.disabled) { return; }
            var url = interestBtn.getAttribute('data-url');

            $.ajax({ url: url, method: 'POST' })
                .done(function () {
                    interestBtn.disabled    = true;
                    interestBtn.textContent = 'Request sent';
                    if (interestCountEl) {
                        var n = parseInt(interestCountEl.textContent, 10);
                        interestCountEl.textContent = isNaN(n) ? '1' : String(n + 1);
                    }
                })
                .fail(function (xhr) {
                    var msg = (xhr.responseJSON && xhr.responseJSON.message)
                        ? xhr.responseJSON.message : 'Something went wrong.';
                    alert(msg);
                });
        });
    }

    /* ------------------------------------------------------------------
       Like toggle
    ------------------------------------------------------------------ */
    var likeBtn = document.getElementById('like-btn');
    if (likeBtn) {
        likeBtn.addEventListener('click', function () {
            $.ajax({ url: likeBtn.getAttribute('data-url'), method: 'POST' })
                .done(function (data) {
                    if (!data.ok) { return; }
                    likeBtn.innerHTML = data.liked ? '♥ Liked' : '♡ Like';
                    likeBtn.setAttribute('data-liked', data.liked ? 'true' : 'false');
                    var likeCountEl = document.getElementById('like-count-label');
                    if (likeCountEl) { likeCountEl.textContent = String(data.like_count); }
                })
                .fail(function (xhr) {
                    var msg = (xhr.responseJSON && xhr.responseJSON.message)
                        ? xhr.responseJSON.message : 'Could not update like.';
                    alert(msg);
                });
        });
    }

    /* ------------------------------------------------------------------
       Bookmark toggle
    ------------------------------------------------------------------ */
    var bookmarkBtn = document.getElementById('bookmark-btn');
    if (bookmarkBtn) {
        bookmarkBtn.addEventListener('click', function () {
            $.ajax({ url: bookmarkBtn.getAttribute('data-url'), method: 'POST' })
                .done(function (data) {
                    if (!data.ok) { return; }
                    bookmarkBtn.textContent = data.saved ? 'Saved' : 'Save for later';
                    bookmarkBtn.setAttribute('data-saved', data.saved ? 'true' : 'false');
                })
                .fail(function (xhr) {
                    var msg = (xhr.responseJSON && xhr.responseJSON.message)
                        ? xhr.responseJSON.message : 'Could not update bookmark.';
                    alert(msg);
                });
        });
    }

    /* ------------------------------------------------------------------
       @mention autocomplete
    ------------------------------------------------------------------ */

    var commentInput = document.getElementById('comment-content');
    var dropdown     = null;
    var debounceT    = null;

    /** Deterministic hue from a string – same as avatar colours. */
    function avatarHue(str) {
        var h = 0;
        for (var i = 0; i < str.length; i++) {
            h = str.charCodeAt(i) + ((h << 5) - h);
        }
        return Math.abs(h) % 360;
    }

    /**
     * Check if the text before the cursor ends with @<partial>.
     * Returns { query, atPos } or null.
     */
    function getMentionCtx(textarea) {
        var pos    = textarea.selectionStart;
        var before = textarea.value.slice(0, pos);
        var match  = before.match(/@(\w*)$/);
        if (!match) { return null; }
        return { query: match[1], atPos: pos - match[0].length };
    }

    function removeDrop() {
        if (dropdown) { dropdown.remove(); dropdown = null; }
    }

    function insertMention(username) {
        if (!commentInput) { return; }
        var ctx = getMentionCtx(commentInput);
        if (!ctx) { removeDrop(); return; }
        var text   = commentInput.value;
        var before = text.slice(0, ctx.atPos);
        var after  = text.slice(commentInput.selectionStart);
        commentInput.value = before + '@' + username + ' ' + after;
        var newPos = ctx.atPos + username.length + 2;
        commentInput.setSelectionRange(newPos, newPos);
        removeDrop();
        commentInput.focus();
    }

    function buildDrop(users) {
        removeDrop();
        if (!users.length || !commentInput) { return; }

        var rect = commentInput.getBoundingClientRect();
        var div  = document.createElement('div');
        div.id        = 'mention-dropdown';
        div.className = 'mention-dropdown shadow border rounded bg-white py-1';
        div.setAttribute('role', 'listbox');
        div.style.cssText = [
            'position:fixed',
            'left:'  + Math.round(rect.left) + 'px',
            'top:'   + Math.round(rect.bottom + 4) + 'px',
            'width:' + Math.min(Math.round(rect.width), 260) + 'px',
            'z-index:2000',
            'max-height:240px',
            'overflow-y:auto',
        ].join(';');

        users.forEach(function (u) {
            var btn  = document.createElement('button');
            var hue  = avatarHue(u.username);
            var init = u.username.charAt(0).toUpperCase();
            btn.type      = 'button';
            btn.className = 'mention-item d-flex align-items-center gap-2 w-100 px-3 py-2 border-0 bg-transparent text-start';
            btn.setAttribute('role', 'option');
            btn.setAttribute('data-username', u.username);
            btn.innerHTML  =
                '<span class="mention-avatar flex-shrink-0" style="background:hsl(' + hue + ',55%,42%)">' + init + '</span>' +
                '<span class="small fw-semibold">@' + u.username + '</span>';

            btn.addEventListener('mousedown', function (e) {
                e.preventDefault();        // prevent textarea blur before click fires
                insertMention(u.username);
            });
            div.appendChild(btn);
        });

        document.body.appendChild(div);
        dropdown = div;
    }

    function navigateDrop(direction) {
        if (!dropdown) { return false; }
        var items   = Array.from(dropdown.querySelectorAll('.mention-item'));
        var focused = dropdown.querySelector('.mention-item:focus');
        var idx     = items.indexOf(focused);
        var next    = direction === 'down'
            ? items[(idx + 1) % items.length]
            : items[(idx - 1 + items.length) % items.length];
        if (next) { next.focus(); }
        return true;
    }

    if (commentInput) {
        commentInput.addEventListener('input', function () {
            var ctx = getMentionCtx(this);
            if (!ctx) { removeDrop(); return; }

            clearTimeout(debounceT);
            debounceT = setTimeout(function () {
                $.getJSON('/api/users', { q: ctx.query })
                    .done(function (users) {
                        if (getMentionCtx(commentInput)) { buildDrop(users); }
                    });
            }, 150);
        });

        commentInput.addEventListener('keydown', function (e) {
            if (!dropdown) { return; }
            if (e.key === 'ArrowDown') { e.preventDefault(); navigateDrop('down'); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); navigateDrop('up'); }
            else if (e.key === 'Escape') { e.preventDefault(); removeDrop(); commentInput.focus(); }
            else if (e.key === 'Enter') {
                var focused = dropdown && dropdown.querySelector('.mention-item:focus');
                if (focused) { e.preventDefault(); focused.click(); }
            }
        });

        commentInput.addEventListener('blur', function () {
            // Delay to allow mousedown on dropdown item to fire first
            setTimeout(removeDrop, 220);
        });

        /* Reposition on scroll/resize so the dropdown tracks the textarea */
        window.addEventListener('scroll', function () {
            if (!dropdown || !commentInput) { return; }
            var r = commentInput.getBoundingClientRect();
            dropdown.style.left = Math.round(r.left) + 'px';
            dropdown.style.top  = Math.round(r.bottom + 4) + 'px';
        }, { passive: true });
    }

    /* ------------------------------------------------------------------
       Comment form (AJAX submit + DOM append)
    ------------------------------------------------------------------ */
    var commentForm  = document.getElementById('comment-form');
    if (!commentForm) { return; }

    var commentErr   = document.getElementById('comment-client-error');
    var commentList  = document.getElementById('comment-list');
    var emptyHint    = document.getElementById('comment-empty-hint');

    function showCommentError(msg) {
        if (!commentErr) { return; }
        commentErr.textContent = msg || '';
        commentErr.classList.toggle('d-none', !msg);
        if (commentInput) { commentInput.classList.toggle('is-invalid', !!msg); }
    }

    commentForm.addEventListener('submit', function (e) {
        e.preventDefault();
        removeDrop();

        var text = commentInput ? commentInput.value.trim() : '';
        if (!text) { showCommentError('Please enter a comment.'); return; }
        showCommentError('');

        var fd = new FormData(commentForm);
        $.ajax({
            url:         commentForm.action,
            method:      'POST',
            data:        fd,
            processData: false,
            contentType: false,
            headers:     { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .done(function (data) {
                if (!data.ok) { return; }

                if (commentList) {
                    commentList.classList.remove('d-none');
                    var li = document.createElement('li');
                    li.className = 'list-group-item py-3';
                    /* Render @mentions in the newly posted comment */
                    var safeContent = data.content
                        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                        .replace(/@(\w+)/g, '<a href="/user/$1" class="mention-link">@$1</a>');
                    li.innerHTML =
                        '<div class="d-flex justify-content-between align-items-baseline gap-2 mb-1">' +
                            '<strong class="small"></strong>' +
                            '<span class="small text-muted"></span>' +
                        '</div>' +
                        '<p class="mb-0 small comment-text" style="white-space:pre-wrap;">' + safeContent + '</p>';
                    li.querySelector('strong').textContent      = data.username;
                    li.querySelector('.text-muted').textContent = data.timestamp;
                    commentList.appendChild(li);
                }

                if (emptyHint) { emptyHint.classList.add('d-none'); }
                commentInput.value = '';

                if (typeof data.comment_count === 'number') {
                    var hc = document.getElementById('comment-count-label');
                    var sc = document.getElementById('comments-section-count');
                    if (hc) { hc.textContent = String(data.comment_count); }
                    if (sc) { sc.textContent = String(data.comment_count); }
                }
            })
            .fail(function (xhr) {
                var msg = (xhr.responseJSON && xhr.responseJSON.message)
                    ? xhr.responseJSON.message : 'Could not post comment.';
                showCommentError(msg);
            });
    });
}());
