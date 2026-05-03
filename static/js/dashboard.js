/**
 * dashboard.js — wanted-category toggles + notification unread badge
 */
(function () {
    'use strict';

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

    /* ---- Notifications (mark-all-read refreshes unread badge from API) ---- */
    var MARK_READ_URL = '/api/dashboard/notifications/mark-all-read';
    var $wrap = $('#notification-unread-wrap');
    var $badge = $('#notification-unread-badge');
    var $markBtn = $('#dashboard-mark-all-read');

    function syncBadgeFromCount(count) {
        var n = parseInt(String(count), 10);
        if (isNaN(n) || n < 0) {
            return;
        }
        if (!$wrap.length || !$badge.length) {
            return;
        }
        $badge.attr('data-count', String(n)).text(String(n));
        $wrap.toggleClass('d-none', n === 0).toggleClass('d-inline-flex', n > 0);
    }

    if ($wrap.length && $badge.length && $markBtn.length) {
        var initial = $badge.data('count');
        if (initial !== undefined && initial !== '') {
            syncBadgeFromCount(initial);
        } else if (parseInt($badge.text(), 10) <= 0) {
            syncBadgeFromCount(0);
        }

        $markBtn.on('click', function () {
            var hdr = csrfTokenFromMeta() ? { 'X-CSRFToken': csrfTokenFromMeta() } : {};
            $.ajax({
                url: MARK_READ_URL,
                method: 'POST',
                headers: hdr,
            }).done(function (data) {
                if (data && data.ok === true && data.unread_count !== undefined) {
                    syncBadgeFromCount(data.unread_count);
                }
            });
        });
    }

    /* ---- Wanted categories (optional block) ---- */
    var $catBar = $('#wanted-cat-bar');
    var $saveStatus = $('#wanted-save-status');
    var saveTimer = null;

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

        var tok = csrfTokenFromMeta();
        var catIds = [];
        $catBar.find('.wanted-cat-btn.btn-primary').each(function () {
            catIds.push(parseInt($(this).data('cat-id'), 10));
        });

        $.ajax({
            url: saveUrl,
            method: 'POST',
            contentType: 'application/json',
            headers: tok ? { 'X-CSRFToken': tok } : {},
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
