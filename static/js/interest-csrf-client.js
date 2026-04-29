/**
 * UWA Skill-Swap — Interest + CSRF client helpers (dashboard & post detail)
 * -------------------------------------------------------------------------
 * Flask-WTF sends CSRF in forms; AJAX POSTs must send X-CSRFToken (or body field).
 * When the token is missing or stale, the API may return JSON like:
 *   { "message": "The CSRF token is missing." }
 * End users should never see raw JSON — this module maps responses to toasts.
 *
 * @fileoverview Coursework demo; wire to real routes when app.py lands.
 */
(function (global) {
  'use strict';

  var CONFIG = {
    /** Max length of user-visible error string (avoid overflow in small toasts) */
    maxMessageLen: 420,
    /** Attribute on buttons that trigger interest POST */
    interestButtonSelector: '[data-uwa-interest-post-id]',
    /** Header name Flask-WTF expects for AJAX (see Flask docs) */
    csrfHeaderName: 'X-CSRFToken',
    /** Meta tag name for embedded token (Jinja: {{ csrf_token() }} in production) */
    csrfMetaName: 'csrf-token',
  };

  function trimMessage(s) {
    if (!s || typeof s !== 'string') { return 'Something went wrong. Please try again.'; }
    s = s.trim();
    if (s.length > CONFIG.maxMessageLen) {
      return s.slice(0, CONFIG.maxMessageLen - 1) + '…';
    }
    return s;
  }

  /**
   * Read CSRF from <meta name="csrf-token" content="..."> — pattern used with
   * {% block head %} in base template after backend merge.
   */
  function getCsrfTokenFromMeta() {
    var el = document.querySelector('meta[name="' + CONFIG.csrfMetaName + '"]');
    if (!el || !el.content) { return null; }
    var c = el.getAttribute('content');
    if (!c || c === 'empty' || c === 'fixme') { return null; }
    return c;
  }

  function getCookie(name) {
    var parts = document.cookie.split(';');
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i].trim();
      if (p.indexOf(name + '=') === 0) { return decodeURIComponent(p.slice(name.length + 1)); }
    }
    return null;
  }

  /**
   * Fallback: some teams expose CSRF only in cookie; Flask can set `csrf` cookie
   * when that pattern is enabled (not default). Kept for forward compatibility.
   */
  function getCsrfTokenFromCookie() {
    return getCookie('csrftoken') || getCookie('csrf_token');
  }

  function resolveCsrfToken() {
    return getCsrfTokenFromMeta() || getCsrfTokenFromCookie();
  }

  /**
   * Map HTTP status + JSON / text body to a user-facing string.
   * @param {Response} res fetch Response
   * @param {string} fallbackText body text if not JSON
   */
  function parseInterestErrorBody(res, fallbackText) {
    var defaultMsg = 'We could not record your interest. Please refresh and try again.';

    if (res.status === 403) {
      return 'Your session may have expired, or a security check failed. Log in again and retry.';
    }
    if (res.status === 400 || res.status === 401) {
      try {
        var j = JSON.parse(fallbackText);
        if (j && (j.message || j.msg || j.error)) {
          return trimMessage(j.message || j.msg || j.error);
        }
      } catch (e) { /* not JSON */ }
      if (fallbackText && /csrf/i.test(fallbackText)) {
        return 'The page was open too long. Refresh the page, then try “Express interest” again.';
      }
      return defaultMsg;
    }
    if (res.status >= 500) {
      return 'The server is busy. Please try again in a moment.';
    }
    return defaultMsg;
  }

  // --------------------------------------------------------------------------
  // User-visible feedback (Bootstrap 5 toasts, non-blocking)
  // --------------------------------------------------------------------------

  function ensureToastContainer() {
    var id = 'uwa-interest-toast-container';
    var c = document.getElementById(id);
    if (c) { return c; }
    c = document.createElement('div');
    c.id = id;
    c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    c.setAttribute('style', 'z-index: 11000;');
    c.setAttribute('aria-live', 'polite');
    c.setAttribute('aria-atomic', 'true');
    document.body.appendChild(c);
    return c;
  }

  function showToast(variant, title, body) {
    var container = ensureToastContainer();
    var el = document.createElement('div');
    el.className = 'toast align-items-center text-bg-' + variant + ' border-0';
    el.setAttribute('role', 'alert');
    el.innerHTML =
      '<div class="d-flex">' +
        '<div class="toast-body">' +
          '<strong class="d-block">' + title + '</strong>' +
          '<span class="small">' + body + '</span>' +
        '</div>' +
        '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      '</div>';
    container.appendChild(el);
    if (global.bootstrap && global.bootstrap.Toast) {
      var t = new global.bootstrap.Toast(el, { autohide: true, delay: 9000 });
      t.show();
    } else {
      el.classList.add('show');
      setTimeout(function () { el.remove(); }, 8000);
    }
  }

  function announceStatus(message) {
    var live = document.getElementById('uwa-dashboard-interest-live');
    if (live) { live.textContent = message; }
  }

  /**
   * @param {'ok'|'warn'|'err'} level
   */
  function showInterestFeedback(level, userMessage) {
    announceStatus(userMessage);
    if (level === 'ok') {
      showToast('success', 'Interest sent', userMessage);
    } else if (level === 'warn') {
      showToast('warning', 'Action needed', userMessage);
    } else {
      showToast('danger', 'Could not send interest', userMessage);
    }
  }

  // --------------------------------------------------------------------------
  // Network: POST /interest/<id>  (Flask route name may differ in merge)
  // --------------------------------------------------------------------------

  function buildInterestUrl(postId) {
    return '/interest/' + encodeURIComponent(String(postId));
  }

  /**
   * Perform interest POST. Caller must pass CSRF; if missing, we short-circuit
   * and show a clear message (never hit the network with a doomed request for UX demos).
   */
  function postInterestRequest(postId, options) {
    options = options || {};
    var token = resolveCsrfToken();
    if (!token) {
      showInterestFeedback('warn', 'This page is missing a security token. Refresh the page, then try again. If the problem continues, open the site in a new tab and log in once more.');
      return Promise.resolve({ ok: false, local: 'missing_csrf' });
    }
    var headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
    };
    headers[CONFIG.csrfHeaderName] = token;
    if (options.headers) { Object.assign(headers, options.headers); }

    return fetch(buildInterestUrl(postId), {
      method: 'POST',
      credentials: 'same-origin',
      headers: headers,
      body: options.body || 'submit=1',
    }).then(function (res) {
      return res.text().then(function (text) {
        return { res: res, text: text };
      });
    });
  }

  function handleInterestResponse(postId, result) {
    if (result && result.local === 'missing_csrf') { return; }
    if (!result || !result.res) { return; }
    var res = result.res;
    var text = result.text || '';

    if (res.ok) {
      var okMsg = 'Your interest was sent to the skill owner. They can see it on their dashboard.';
      try {
        var j = JSON.parse(text);
        if (j && j.message) { okMsg = trimMessage(String(j.message)); }
      } catch (e) { /* ignore */ }
      showInterestFeedback('ok', okMsg);
      return;
    }
    var errMsg = parseInterestErrorBody(res, text);
    showInterestFeedback('err', errMsg);
  }

  function bindInterestButtons(root) {
    root = root || document;
    var nodes = root.querySelectorAll(CONFIG.interestButtonSelector);
    for (var i = 0; i < nodes.length; i++) {
      (function (btn) {
        btn.addEventListener('click', function (ev) {
          ev.preventDefault();
          var pid = btn.getAttribute('data-uwa-interest-post-id');
          if (!pid) { return; }
          if (btn.getAttribute('data-uwa-mock-broken-csrf') === '1') {
            var fakeRes = { status: 400, ok: false };
            var body = JSON.stringify({ message: 'The CSRF token is missing.' });
            handleInterestResponse(pid, { res: fakeRes, text: body });
            return;
          }
          postInterestRequest(pid).then(function (r) { handleInterestResponse(pid, r); });
        });
      })(nodes[i]);
    }
  }

  // Static demo: simulate server JSON without a backend
  function mockRunCsrfMissingDemo() {
    var fake = { status: 400, ok: false };
    var txt = JSON.stringify({ message: 'The CSRF token is missing.' });
    showInterestFeedback('err', parseInterestErrorBody(fake, txt));
  }

  if (global.document) {
    document.addEventListener('DOMContentLoaded', function () {
      bindInterestButtons(document);
    });
  }

  global.UWAInterestClient = {
    config: CONFIG,
    getCsrfTokenFromMeta: getCsrfTokenFromMeta,
    resolveCsrfToken: resolveCsrfToken,
    postInterestRequest: postInterestRequest,
    showInterestFeedback: showInterestFeedback,
    bindInterestButtons: bindInterestButtons,
    parseInterestErrorBody: parseInterestErrorBody,
    mockRunCsrfMissingDemo: mockRunCsrfMissingDemo,
  };
})(typeof window !== 'undefined' ? window : this);
