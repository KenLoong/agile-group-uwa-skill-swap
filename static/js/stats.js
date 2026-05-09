/**
 * stats.js – Public Platform Stats page
 *
 * Fetches /api/stats (AJAX) then renders three Chart.js charts:
 *  1. Posts by category   – vertical bar
 *  2. New posts trend     – line (toggle 7d / 30d)
 *  3. Top 5 users         – horizontal grouped bar
 */

(function () {
    'use strict';

    /* ------------------------------------------------------------------
       Colour palettes
    ------------------------------------------------------------------ */
    var UWA_NAVY    = '#003087';
    var UWA_TEAL    = '#0b4f6c';
    var PALETTE     = ['#003087', '#0b4f6c', '#1d6fa4', '#2b9f9f', '#5ac8a8', '#a8dadc'];
    var LIKE_COLOR  = 'rgba(239, 68, 68, 0.7)';
    var INT_COLOR   = 'rgba(59, 130, 246, 0.7)';

    /* ------------------------------------------------------------------
       Chart defaults
    ------------------------------------------------------------------ */
    Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
    Chart.defaults.font.size   = 13;

    /* ------------------------------------------------------------------
       State
    ------------------------------------------------------------------ */
    var allData      = null;
    var trendChart   = null;
    var activeDays   = 30;

    /* ------------------------------------------------------------------
       Helpers
    ------------------------------------------------------------------ */
    function shortDate(dateStr) {
        // '2024-04-15' → 'Apr 15'
        var d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' });
    }

    function setKpi(id, value) {
        var el = document.getElementById(id);
        if (el) { el.textContent = value; }
    }

    /* ------------------------------------------------------------------
       Chart builders
    ------------------------------------------------------------------ */

    function buildCategoryChart(data) {
        var ctx = document.getElementById('chart-categories');
        if (!ctx) { return; }
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(function (c) { return c.label; }),
                datasets: [{
                    label: 'Posts',
                    data:  data.map(function (c) { return c.count; }),
                    backgroundColor: PALETTE,
                    borderRadius:    6,
                    borderSkipped:   false,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend:  { display: false },
                    tooltip: { callbacks: {
                        label: function (ctx) { return ' ' + ctx.parsed.y + ' posts'; }
                    }},
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks:       { stepSize: 1, precision: 0 },
                        grid:        { color: 'rgba(0,0,0,0.05)' },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    function buildTrendChart(trend) {
        var ctx = document.getElementById('chart-trend');
        if (!ctx) { return; }
        var slice = (activeDays === 7) ? trend.slice(-7) : trend;
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: slice.map(function (d) { return shortDate(d.date); }),
                datasets: [{
                    label:           'New posts',
                    data:            slice.map(function (d) { return d.count; }),
                    borderColor:     UWA_NAVY,
                    backgroundColor: 'rgba(0, 48, 135, 0.1)',
                    fill:            true,
                    tension:         0.35,
                    pointRadius:     3,
                    pointHoverRadius: 6,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: {
                        label: function (ctx) { return ' ' + ctx.parsed.y + ' new posts'; }
                    }},
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks:       { stepSize: 1, precision: 0 },
                        grid:        { color: 'rgba(0,0,0,0.05)' },
                    },
                    x: {
                        ticks: { maxTicksLimit: 10 },
                        grid:  { display: false },
                    },
                },
            },
        });
    }

    function updateTrendChart(trend) {
        if (!trendChart) { return; }
        var slice = (activeDays === 7) ? trend.slice(-7) : trend;
        trendChart.data.labels        = slice.map(function (d) { return shortDate(d.date); });
        trendChart.data.datasets[0].data = slice.map(function (d) { return d.count; });
        trendChart.update();
    }

    function buildTopUsersChart(users) {
        var ctx = document.getElementById('chart-top-users');
        if (!ctx) { return; }
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: users.map(function (u) { return u.username; }),
                datasets: [
                    {
                        label:           'Posts',
                        data:            users.map(function (u) { return u.post_count; }),
                        backgroundColor: UWA_NAVY,
                        borderRadius:    4,
                    },
                    {
                        label:           'Likes received',
                        data:            users.map(function (u) { return u.total_likes; }),
                        backgroundColor: UWA_TEAL,
                        borderRadius:    4,
                    },
                ],
            },
            options: {
                indexAxis:           'y',    // horizontal bars
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels:   { boxWidth: 12, padding: 16 },
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks:       { stepSize: 1, precision: 0 },
                        grid:        { color: 'rgba(0,0,0,0.05)' },
                    },
                    y: { grid: { display: false } },
                },
            },
        });
    }

    /* ------------------------------------------------------------------
       Bootstrap: fetch data then paint
    ------------------------------------------------------------------ */

    var $loading = $('#stats-loading');
    var $error   = $('#stats-error');

    $.getJSON('/api/stats')
        .done(function (data) {
            allData = data;
            $loading.addClass('d-none');

            // KPI counters
            setKpi('kpi-posts',    data.totals.posts);
            setKpi('kpi-users',    data.totals.users);
            setKpi('kpi-comments', data.totals.comments);
            setKpi('kpi-tags',     data.totals.tags);

            buildCategoryChart(data.category_counts);
            buildTrendChart(data.trend_30);
            buildTopUsersChart(data.top_users);
        })
        .fail(function () {
            $loading.addClass('d-none');
            $error.removeClass('d-none');
        });

    /* ------------------------------------------------------------------
       Trend range toggle (7d / 30d)
    ------------------------------------------------------------------ */
    $(document).on('click', '.trend-range-btn', function () {
        var $btn = $(this);
        if ($btn.hasClass('active') || !allData) { return; }
        $('.trend-range-btn').removeClass('active');
        $btn.addClass('active');
        activeDays = parseInt($btn.data('days'), 10);
        updateTrendChart(allData.trend_30);
    });

}());
