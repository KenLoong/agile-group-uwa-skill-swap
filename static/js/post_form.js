/**
 * post_form.js – Create / Edit post form
 *
 * Responsibilities:
 *  1. Client-side validation of title and description
 *  2. Tag-pill input widget (type → Enter/comma adds pill; click × removes)
 *     The final tag list is synced back to a hidden <input name="tags"> before submit.
 */

(function () {
    'use strict';

    var form = document.getElementById('post-form');
    if (!form) { return; }

    /* ------------------------------------------------------------------
       1. Validation helpers
    ------------------------------------------------------------------ */

    var titleField = document.getElementById('post-title');
    var descField  = document.getElementById('post-description');
    var titleErr   = document.getElementById('post-title-err');
    var descErr    = document.getElementById('post-desc-err');

    function clearErrors() {
        [titleField, descField].forEach(function (el) {
            if (el) { el.classList.remove('is-invalid'); }
        });
        [titleErr, descErr].forEach(function (el) {
            if (el) {
                el.textContent = '';
                el.classList.add('d-none');
            }
        });
    }

    function showError(field, errEl, msg) {
        if (field)  { field.classList.add('is-invalid'); }
        if (errEl)  {
            errEl.textContent = msg;
            errEl.classList.remove('d-none');
        }
    }

    /* ------------------------------------------------------------------
       2. Tag input widget
    ------------------------------------------------------------------ */

    var wrap         = document.getElementById('tag-input-wrap');
    var pillsBox     = document.getElementById('tag-pills-container');
    var tagTextInput = document.getElementById('tag-text-input');
    var tagsHidden   = document.getElementById('tags-hidden');

    /* Active slug set – preserves insertion order via array */
    var activeSlugs  = [];
    var activeLabels = {};   // slug → display label

    function slugify(raw) {
        return raw.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9\-]/g, '').slice(0, 50);
    }

    function syncHidden() {
        if (tagsHidden) { tagsHidden.value = activeSlugs.join(','); }
    }

    function removePill(slug) {
        activeSlugs = activeSlugs.filter(function (s) { return s !== slug; });
        delete activeLabels[slug];
        var pill = pillsBox ? pillsBox.querySelector('[data-slug="' + slug + '"]') : null;
        if (pill) { pill.remove(); }
        syncHidden();
    }

    function addTagPill(rawLabel) {
        var slug = slugify(rawLabel);
        if (!slug || activeSlugs.indexOf(slug) !== -1) { return; }
        if (activeSlugs.length >= 10) { return; }   // cap at 10 tags

        activeSlugs.push(slug);
        activeLabels[slug] = rawLabel.trim().slice(0, 80);
        syncHidden();

        if (!pillsBox) { return; }
        var span  = document.createElement('span');
        span.className   = 'tag-pill tag-pill-removable d-inline-flex align-items-center gap-1';
        span.dataset.slug = slug;
        span.innerHTML   = '#' + rawLabel.trim().slice(0, 50).replace(/</g, '&lt;') +
                           ' <button type="button" class="tag-remove-btn btn-close btn-close-sm" aria-label="Remove tag"></button>';
        span.querySelector('.tag-remove-btn').addEventListener('click', function () {
            removePill(slug);
        });
        pillsBox.appendChild(span);
    }

    /* Restore existing tags (edit mode) from data attributes */
    if (wrap) {
        var initSlugs  = (wrap.dataset.initSlugs  || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        var initLabels = (wrap.dataset.initLabels || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        initSlugs.forEach(function (slug, i) {
            var label = initLabels[i] || slug;
            addTagPill(label);
        });
    }

    /* Keyboard handling: Enter or comma commits the tag */
    if (tagTextInput) {
        tagTextInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                var raw = tagTextInput.value.replace(/,/g, '').trim();
                if (raw) { addTagPill(raw); }
                tagTextInput.value = '';
            }
        });
        /* Also handle pasting comma-separated values */
        tagTextInput.addEventListener('paste', function (e) {
            e.preventDefault();
            var pasted = (e.clipboardData || window.clipboardData).getData('text');
            pasted.split(',').forEach(function (chunk) {
                var raw = chunk.trim();
                if (raw) { addTagPill(raw); }
            });
            tagTextInput.value = '';
        });
        /* Commit on blur if there's leftover text */
        tagTextInput.addEventListener('blur', function () {
            var raw = tagTextInput.value.trim();
            if (raw) { addTagPill(raw); tagTextInput.value = ''; }
        });
    }

    /* ------------------------------------------------------------------
       3. Markdown Write / Preview toggle
    ------------------------------------------------------------------ */

    var writePaneEl   = document.getElementById('md-write-pane');
    var previewPaneEl = document.getElementById('md-preview-pane');
    var writeBtnEl    = document.getElementById('md-write-btn');
    var previewBtnEl  = document.getElementById('md-preview-btn');

    if (writeBtnEl && previewBtnEl && writePaneEl && previewPaneEl) {
        writeBtnEl.addEventListener('click', function () {
            writePaneEl.classList.remove('d-none');
            previewPaneEl.classList.add('d-none');
            writeBtnEl.classList.add('active');
            previewBtnEl.classList.remove('active');
        });

        previewBtnEl.addEventListener('click', function () {
            var md   = descField ? descField.value : '';
            var html = (typeof marked !== 'undefined')
                ? marked.parse(md || '*Nothing to preview yet…*')
                : '<em>Markdown renderer not loaded.</em>';
            previewPaneEl.innerHTML = html;
            previewPaneEl.classList.remove('d-none');
            writePaneEl.classList.add('d-none');
            previewBtnEl.classList.add('active');
            writeBtnEl.classList.remove('active');
        });
    }

    /* ------------------------------------------------------------------
       4. Form submit validation
    ------------------------------------------------------------------ */

    form.addEventListener('submit', function (ev) {
        clearErrors();
        /* Commit any uncommitted tag text before submit */
        if (tagTextInput) {
            var raw = tagTextInput.value.trim();
            if (raw) { addTagPill(raw); tagTextInput.value = ''; }
        }

        var valid = true;

        var title = titleField ? titleField.value.trim() : '';
        if (!title) {
            showError(titleField, titleErr, 'Title is required.');
            valid = false;
        } else if (title.length > 100) {
            showError(titleField, titleErr, 'Title must be at most 100 characters.');
            valid = false;
        }

        var desc = descField ? descField.value.trim() : '';
        if (!desc) {
            showError(descField, descErr, 'Description is required.');
            valid = false;
        }

        if (!valid) { ev.preventDefault(); }
    });
}());
