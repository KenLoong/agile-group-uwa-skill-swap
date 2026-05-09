/**
 * register.js – Registration form client-side validation
 *
 * Validates username length, UWA email format, password strength and
 * password confirmation before the form is submitted.
 * Server-side validation (Flask-WTF) remains the authoritative check.
 */

(function () {
    'use strict';

    var form = document.getElementById('register-form');
    if (!form) { return; }

    function pair(fieldId, errId) {
        return {
            field: document.getElementById(fieldId),
            err:   document.getElementById(errId)
        };
    }

    var username = pair('reg-username', 'reg-username-err');
    var email    = pair('reg-email',    'reg-email-err');
    var password = pair('reg-password', 'reg-password-err');
    var confirm  = pair('reg-confirm',  'reg-confirm-err');

    function clearAll() {
        [username, email, password, confirm].forEach(function (p) {
            if (p.field) { p.field.classList.remove('is-invalid'); }
            if (p.err)   {
                p.err.textContent = '';
                p.err.classList.add('d-none');
            }
        });
    }

    function showError(p, msg) {
        if (p.field) { p.field.classList.add('is-invalid'); }
        if (p.err)   {
            p.err.textContent = msg;
            p.err.classList.remove('d-none');
        }
    }

    form.addEventListener('submit', function (ev) {
        clearAll();
        var valid = true;

        var uname = username.field ? username.field.value.trim() : '';
        if (uname.length < 2 || uname.length > 20) {
            showError(username, 'Username must be 2–20 characters.');
            valid = false;
        }

        var em = email.field ? email.field.value.trim().toLowerCase() : '';
        if (!em.endsWith('@student.uwa.edu.au') || em.indexOf('@') < 1) {
            showError(email, 'Use your @student.uwa.edu.au email address.');
            valid = false;
        }

        var pw = password.field ? password.field.value : '';
        if (pw.length < 6) {
            showError(password, 'Password must be at least 6 characters.');
            valid = false;
        }

        if (confirm.field && pw !== confirm.field.value) {
            showError(confirm, 'Passwords do not match.');
            valid = false;
        }

        if (!valid) { ev.preventDefault(); }
    });
}());
