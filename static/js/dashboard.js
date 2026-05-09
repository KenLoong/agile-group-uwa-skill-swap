/**
 * dashboard.js – User dashboard interactions
 *
 *  - "Match Found" banner → click jumps to Matches tab
 *  - Auto-open Matches tab when URL hash is #pane-matches
 *  - "Save for later" removal (unsave-btn)
 *  - Wanted-skill category toggles (auto-save via AJAX)
 *  - Post status inline dropdown (auto-save via AJAX)
 */

(function () {
    'use strict';

    /* ------------------------------------------------------------------
       0. Match banner → switch to Matches tab
    ------------------------------------------------------------------ */

    function openTab(tabId) {
        var tabEl = document.getElementById(tabId);
        if (tabEl) {
            var bsTab = new bootstrap.Tab(tabEl);
            bsTab.show();
            tabEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    /* Banner click */
    $(document).on('click', '#match-banner', function (e) {
        e.preventDefault();
        openTab('tab-matches');
    });

    /* Auto-open Matches tab if URL hash points there */
    if (window.location.hash === '#pane-matches' || window.location.hash === '#matches') {
        openTab('tab-matches');
    }

    /* Auto-open Mentions tab if URL hash points there */
    if (window.location.hash === '#pane-notif' || window.location.hash === '#mentions') {
        openTab('tab-notif');
    }

    /* Mark all notifications as read when the Mentions tab is opened */
    var notifTab = document.getElementById('tab-notif');
    if (notifTab) {
        notifTab.addEventListener('shown.bs.tab', function () {
            $.ajax({ url: '/api/notifications/read', method: 'POST' })
                .done(function () {
                    /* Remove unread styling from the list */
                    document.querySelectorAll('.notif-unread').forEach(function (el) {
                        el.classList.remove('notif-unread');
                    });
                    document.querySelectorAll('.notif-unread-dot').forEach(function (el) {
                        el.remove();
                    });
                    /* Remove badge from the tab */
                    var badge = notifTab.querySelector('.badge');
                    if (badge) { badge.remove(); }
                    /* Remove red dot from nav */
                    document.querySelectorAll('.notif-dot').forEach(function (el) { el.remove(); });
                });
        });
    }

    /* ------------------------------------------------------------------
       1. Remove saved bookmark
    ------------------------------------------------------------------ */

    $(document).on('click', '.unsave-btn', function () {
        var url  = $(this).data('url');
        var item = $(this).closest('li');
        $.ajax({ url: url, method: 'POST' })
            .done(function (data) {
                if (data.ok && !data.saved) { item.remove(); }
            });
    });

    /* ------------------------------------------------------------------
       2. Wanted-skill category toggles
    ------------------------------------------------------------------ */

    var $catBar    = $('#wanted-cat-bar');
    var $saveStatus = $('#wanted-save-status');
    var saveTimer  = null;

    $catBar.on('click', '.wanted-cat-btn', function () {
        var $btn = $(this);
        var isActive = $btn.hasClass('btn-primary');

        $btn.toggleClass('btn-primary', !isActive)
            .toggleClass('btn-outline-secondary', isActive);

        /* Debounce: save 600 ms after last click */
        clearTimeout(saveTimer);
        $saveStatus.addClass('d-none');
        saveTimer = setTimeout(saveWantedSkills, 600);
    });

    function saveWantedSkills() {
        var saveUrl = $catBar.data('url');
        if (!saveUrl) { return; }

        var catIds = [];
        $catBar.find('.wanted-cat-btn.btn-primary').each(function () {
            catIds.push(parseInt($(this).data('cat-id'), 10));
        });

        $.ajax({
            url:         saveUrl,
            method:      'POST',
            contentType: 'application/json',
            data:        JSON.stringify({ category_ids: catIds }),
        }).done(function (data) {
            if (data.ok) {
                $saveStatus.removeClass('d-none');
                setTimeout(function () { $saveStatus.addClass('d-none'); }, 2000);
            }
        });
    }

    /* ------------------------------------------------------------------
       2b. Mark all as read button
    ------------------------------------------------------------------ */

    $(document).on('click', '#mark-all-read-btn', function () {
        $.ajax({ url: '/api/notifications/read', method: 'POST' })
            .done(function () {
                document.querySelectorAll('.notif-unread').forEach(function (el) {
                    el.classList.remove('notif-unread');
                });
                document.querySelectorAll('.notif-unread-dot').forEach(function (el) {
                    el.remove();
                });
                var tabBadge = document.querySelector('#tab-notif .badge');
                if (tabBadge) { tabBadge.remove(); }
                document.querySelectorAll('.notif-dot').forEach(function (el) { el.remove(); });
            });
    });

    /* ------------------------------------------------------------------
       3. Post status inline dropdown (My Skills tab)
    ------------------------------------------------------------------ */

    $(document).on('change', '.post-status-select', function () {
        var $sel    = $(this);
        var url     = $sel.data('url');
        var status  = $sel.val();

        $.ajax({
            url:         url,
            method:      'POST',
            contentType: 'application/json',
            data:        JSON.stringify({ status: status }),
        }).done(function (data) {
            if (!data.ok) {
                /* Revert to previous value on failure */
                $sel.val($sel.data('current'));
            } else {
                $sel.data('current', data.status);
            }
        }).fail(function () {
            $sel.val($sel.data('current'));
        });
    });

}());
