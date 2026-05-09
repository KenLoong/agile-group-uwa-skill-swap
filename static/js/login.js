/**
 * login.js – Login form client-side validation
 *
 * Validates email format and password presence before the form is
 * submitted, displaying Bootstrap-style inline error messages.
 * Server-side validation (Flask-WTF) remains the authoritative check.
 */

(function () {
    'use strict';

    var form   = document.getElementById('login-form');
    if (!form) { return; }

    var emailField    = document.getElementById('login-email');
    var passwordField = document.getElementById('login-password');
    var emailErr      = document.getElementById('login-email-err');
    var passwordErr   = document.getElementById('login-password-err');

    function clearErrors() {
        [emailField, passwordField].forEach(function (el) {
            if (el) { el.classList.remove('is-invalid'); }
        });
        [emailErr, passwordErr].forEach(function (el) {
            if (el) { el.classList.add('d-none'); }
        });
    }

    function showError(field, errEl, msg) {
        if (field)  { field.classList.add('is-invalid'); }
        if (errEl)  {
            errEl.textContent = msg;
            errEl.classList.remove('d-none');
        }
    }

    form.addEventListener('submit', function (ev) {
        clearErrors();
        var valid = true;

        var email = emailField ? emailField.value.trim() : '';
        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showError(emailField, emailErr, 'Enter a valid email address.');
            valid = false;
        }

        if (!passwordField || !passwordField.value) {
            showError(passwordField, passwordErr, 'Password is required.');
            valid = false;
        }

        if (!valid) { ev.preventDefault(); }
    });
}());
