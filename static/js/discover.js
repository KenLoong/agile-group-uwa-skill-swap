/**
 * discover.js – Home / Discovery page
 *
 * Handles:
 *  - Category pill click → AJAX filter via /api/filter
 *  - Tag pill click      → AJAX filter by tag
 *  - Sort-select change  → AJAX filter
 *  - Search form submit  → AJAX filter
 *  - Pager button click  → AJAX paginated fetch
 *  - Renders post cards (with status badge + tags) and pagination controls
 */

(function () {
    'use strict';

    var $grid  = $('#post-grid');
    var $pager = $('#pager-wrap');

    var currentCategory = 'all';
    var currentTag      = '';
    var currentQuery    = '';
    var currentSort     = $('#sort-select').val() || 'newest';
    var currentPage     = 1;

    /* ------------------------------------------------------------------
       Helpers
    ------------------------------------------------------------------ */

    function avatarHue(str) {
        var h = 0;
        for (var i = 0; i < str.length; i++) {
            h = str.charCodeAt(i) + ((h << 5) - h);
        }
        return Math.abs(h) % 360;
    }

    function esc(s) {
        return $('<div>').text(s == null ? '' : String(s)).html();
    }

    /* ------------------------------------------------------------------
       Rendering
    ------------------------------------------------------------------ */

    function statusBadgeHtml(status) {
        var map = {
            open:    '🟢 Open',
            matched: '🤝 Matched',
            closed:  '⭕ Closed'
        };
        var label = map[status] || status;
        return '<span class="badge status-badge status-' + esc(status) + '">' + label + '</span>';
    }

    function tagsHtml(tags) {
        if (!tags || !tags.length) { return ''; }
        return tags.slice(0, 4).map(function (t) {
            return '<span class="tag-pill">#' + esc(t.label) + '</span>';
        }).join('');
    }

    function renderPosts(payload) {
        var items = payload.posts || [];
        if (!items.length) {
            $grid.html('<div class="col-12"><p class="text-muted mb-0" id="empty-hint">No posts match your filters.</p></div>');
            renderPager(payload);
            return;
        }

        var html = items.map(function (p) {
            var initial    = (p.author && p.author.charAt(0)) ? p.author.charAt(0).toUpperCase() : '?';
            var hue        = avatarHue(p.author || '');
            var detailUrl  = '/post/' + p.id;
            var profileUrl = p.author_profile || ('/user/' + encodeURIComponent(p.author));
            var imgHtml    = p.image_url
                ? '<a href="' + esc(detailUrl) + '" class="d-block"><img src="' + esc(p.image_url) + '" class="w-100 object-fit-cover" alt="" style="height:140px"></a>'
                : '';
            var footerTags = tagsHtml(p.tags);

            return (
                '<div class="col-md-6 col-xl-4">' +
                    '<div class="card h-100 shadow-sm border-0 post-card overflow-hidden">' +
                        imgHtml +
                        '<div class="card-body d-flex flex-column">' +
                            '<div class="d-flex align-items-start gap-3 mb-2">' +
                                '<span class="avatar-circle flex-shrink-0" style="background:hsl(' + hue + ',55%,42%)">' + esc(initial) + '</span>' +
                                '<div class="min-w-0">' +
                                    '<span class="badge bg-primary bg-opacity-75 mb-1">' + esc(p.category_label) + '</span>' +
                                    '<h2 class="h5 card-title text-truncate mb-1">' +
                                        '<a href="' + detailUrl + '" class="text-reset text-decoration-none">' + esc(p.title) + '</a>' +
                                    '</h2>' +
                                    '<p class="small text-muted mb-0">' +
                                        '<a href="' + profileUrl + '" class="text-muted">' + esc(p.author) + '</a> · ' + esc(p.timestamp) +
                                    '</p>' +
                                '</div>' +
                            '</div>' +
                            '<p class="card-text text-body-secondary small flex-grow-1 mb-1">' +
                                '<a href="' + detailUrl + '" class="text-body-secondary text-decoration-none">' + esc(p.snippet) + '</a>' +
                            '</p>' +
                            '<div class="d-flex align-items-center justify-content-between mt-1">' +
                                '<p class="small text-muted mb-0">' +
                                    (p.comment_count != null ? p.comment_count : 0) + ' comments · ' +
                                    (p.like_count    != null ? p.like_count    : 0) + ' likes' +
                                '</p>' +
                                statusBadgeHtml(p.status) +
                            '</div>' +
                            (footerTags ? '<div class="d-flex flex-wrap gap-1 mt-2">' + footerTags + '</div>' : '') +
                        '</div>' +
                    '</div>' +
                '</div>'
            );
        }).join('');

        $grid.html(html);
        renderPager(payload);
    }

    function renderPager(payload) {
        if (!payload.pages || payload.pages <= 1) {
            $pager.addClass('d-none');
            return;
        }
        $pager.removeClass('d-none');
        var parts = [];
        if (payload.has_prev) {
            parts.push('<li class="page-item"><button type="button" class="page-link" data-page="' + (payload.page - 1) + '">Previous</button></li>');
        }
        parts.push('<li class="page-item disabled"><span class="page-link">Page ' + payload.page + ' / ' + payload.pages + '</span></li>');
        if (payload.has_next) {
            parts.push('<li class="page-item"><button type="button" class="page-link" data-page="' + (payload.page + 1) + '">Next</button></li>');
        }
        $('#pager-list').html(parts.join(''));
    }

    /* ------------------------------------------------------------------
       Data fetching
    ------------------------------------------------------------------ */

    function syncCategoryPills() {
        $('#category-bar .category-pill').removeClass('active');
        $('#category-bar .category-pill').filter(function () {
            return $(this).data('category') === currentCategory;
        }).addClass('active');
    }

    function syncTagPills() {
        $('#tag-bar .tag-filter-btn').removeClass('active');
        if (currentTag) {
            $('#tag-bar .tag-filter-btn').filter(function () {
                return $(this).data('tag') === currentTag;
            }).addClass('active');
        }
    }

    function fetchPosts(page) {
        currentPage = page || 1;
        $grid.addClass('opacity-50');
        $.getJSON('/api/filter', {
            category: currentCategory,
            tag:      currentTag,
            query:    currentQuery,
            sort:     currentSort,
            page:     currentPage
        })
            .done(renderPosts)
            .fail(function () {
                $grid.html('<div class="col-12"><div class="alert alert-danger">Could not load posts. Please try again.</div></div>');
            })
            .always(function () { $grid.removeClass('opacity-50'); });
    }

    /* ------------------------------------------------------------------
       Event listeners
    ------------------------------------------------------------------ */

    $('#category-bar').on('click', '.category-pill', function () {
        currentCategory = $(this).data('category');
        syncCategoryPills();
        fetchPosts(1);
    });

    /* Tag bar – clicking an active tag deselects it */
    $('#tag-bar').on('click', '.tag-filter-btn', function () {
        var slug = $(this).data('tag');
        currentTag = (currentTag === slug) ? '' : slug;
        syncTagPills();
        fetchPosts(1);
    });

    $('#sort-select').on('change', function () {
        currentSort = $(this).val();
        fetchPosts(1);
    });

    $('#search-form').on('submit', function (e) {
        e.preventDefault();
        currentQuery = $('#search-input').val().trim();
        fetchPosts(1);
    });

    $('#pager-wrap').on('click', '.page-link[data-page]', function (e) {
        e.preventDefault();
        var p = $(this).data('page');
        if (p) { fetchPosts(p); }
    });

    /* Initialise active pill from server-rendered state */
    var $activePill = $('#category-bar .category-pill.active');
    if ($activePill.length) {
        currentCategory = $activePill.data('category') || 'all';
    }
    syncCategoryPills();
}());
