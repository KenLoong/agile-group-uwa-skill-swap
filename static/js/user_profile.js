/**
 * user_profile.js – Owner-only profile page interactions
 *
 * Handles the "What I want to learn" category toggles on the profile page.
 * Reuses the same /dashboard/wanted-skills AJAX endpoint as the dashboard.
 */

(function () {
    'use strict';

    var $bar       = $('#profile-wanted-bar');
    var $status    = $('#profile-save-status');
    var saveTimer  = null;

    if (!$bar.length) { return; }

    $bar.on('click', '.wanted-cat-btn', function () {
        var $btn     = $(this);
        var isActive = $btn.hasClass('btn-primary');

        $btn.toggleClass('btn-primary', !isActive)
            .toggleClass('btn-outline-secondary', isActive);

        clearTimeout(saveTimer);
        $status.addClass('d-none');
        saveTimer = setTimeout(saveWanted, 600);
    });

    function saveWanted() {
        var url = $bar.data('url');
        if (!url) { return; }

        var catIds = [];
        $bar.find('.wanted-cat-btn.btn-primary').each(function () {
            catIds.push(parseInt($(this).data('cat-id'), 10));
        });

        $.ajax({
            url:         url,
            method:      'POST',
            contentType: 'application/json',
            data:        JSON.stringify({ category_ids: catIds }),
        }).done(function (data) {
            if (data.ok) {
                $status.removeClass('d-none');
                setTimeout(function () { $status.addClass('d-none'); }, 2500);
            }
        });
    }

}());
