/**
 * dashboard.js — wanted-category toggles (auto-save via AJAX)
 */
(function () {
    'use strict';

    var $catBar = $('#wanted-cat-bar');
    var $saveStatus = $('#wanted-save-status');
    var saveTimer = null;

    function csrfTokenFromMeta() {
        var el = document.querySelector('meta[name="csrf-token"]');
        if (!el) {
            return null;
        }
        var token = el.getAttribute('content');
        if (!token || token === 'empty' || token === 'fixme') {
            return null;
        }
        return token;
    }

    if (!$catBar.length) {
        return;
    }

    $catBar.on('click', '.wanted-cat-btn', function () {
        var $btn = $(this);
        var isActive = $btn.hasClass('btn-primary');

        $btn.toggleClass('btn-primary', !isActive)
            .toggleClass('btn-outline-secondary', isActive);

        clearTimeout(saveTimer);
        $saveStatus.addClass('d-none');
        saveTimer = setTimeout(saveWantedSkills, 600);
    });

    function saveWantedSkills() {
        var saveUrl = $catBar.data('url');
        if (!saveUrl) {
            return;
        }

        var catIds = [];
        $catBar.find('.wanted-cat-btn.btn-primary').each(function () {
            catIds.push(parseInt($(this).data('cat-id'), 10));
        });

        $.ajax({
            url: saveUrl,
            method: 'POST',
            contentType: 'application/json',
            headers: csrfTokenFromMeta() ? { 'X-CSRFToken': csrfTokenFromMeta() } : {},
            data: JSON.stringify({ category_ids: catIds }),
        }).done(function (data) {
            if (data && data.ok) {
                $saveStatus.removeClass('d-none');
                setTimeout(function () {
                    $saveStatus.addClass('d-none');
                }, 2000);
            }
        });
    }
}());
