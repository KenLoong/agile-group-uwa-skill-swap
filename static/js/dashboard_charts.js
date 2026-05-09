/**
 * dashboard_charts.js – Personal analytics charts (My Stats tab)
 *
 * Lazily loads /api/dashboard/charts only when the "My Stats" tab is
 * opened for the first time, then renders:
 *  1. Doughnut – my skills by category
 *  2. Line      – 30-day likes + interests received on my posts
 */

(function () {
    'use strict';

    var PALETTE = ['#003087', '#0b4f6c', '#1d6fa4', '#2b9f9f', '#5ac8a8', '#a8dadc'];
    var loaded  = false;

    function shortDate(dateStr) {
        var d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' });
    }

    function buildDonut(dist) {
        var ctx   = document.getElementById('my-chart-donut');
        var empty = document.getElementById('my-stats-empty');
        if (!ctx) { return; }

        if (!dist || !dist.length) {
            if (empty) { empty.classList.remove('d-none'); }
            return;
        }

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: dist.map(function (c) { return c.label; }),
                datasets: [{
                    data:            dist.map(function (c) { return c.count; }),
                    backgroundColor: PALETTE,
                    borderWidth:     2,
                    hoverOffset:     8,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels:   { boxWidth: 12, padding: 14 },
                    },
                    tooltip: { callbacks: {
                        label: function (ctx) {
                            return ' ' + ctx.label + ': ' + ctx.parsed + ' posts';
                        }
                    }},
                },
                cutout: '60%',
            },
        });
    }

    function buildActivityLine(activity) {
        var ctx = document.getElementById('my-chart-activity');
        if (!ctx) { return; }

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: activity.map(function (d) { return shortDate(d.date); }),
                datasets: [
                    {
                        label:           'Likes received',
                        data:            activity.map(function (d) { return d.likes; }),
                        borderColor:     'rgba(239, 68, 68, 0.85)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill:            true,
                        tension:         0.35,
                        pointRadius:     3,
                        pointHoverRadius: 6,
                    },
                    {
                        label:           'Interests received',
                        data:            activity.map(function (d) { return d.interests; }),
                        borderColor:     'rgba(59, 130, 246, 0.85)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill:            true,
                        tension:         0.35,
                        pointRadius:     3,
                        pointHoverRadius: 6,
                    },
                ],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                interaction:         { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'top',
                        labels:   { boxWidth: 12, padding: 14 },
                    },
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

    /* ------------------------------------------------------------------
       Lazy load: only fetch on first tab activation
    ------------------------------------------------------------------ */
    var $tab = document.getElementById('tab-my-stats');
    if (!$tab) { return; }

    $tab.addEventListener('shown.bs.tab', function () {
        if (loaded) { return; }
        loaded = true;

        $.getJSON('/api/dashboard/charts')
            .done(function (data) {
                buildDonut(data.category_distribution);
                buildActivityLine(data.daily_activity);
            })
            .fail(function () {
                var pane = document.getElementById('pane-my-stats');
                if (pane) {
                    var err = document.createElement('div');
                    err.className   = 'alert alert-danger mt-3';
                    err.textContent = 'Could not load your stats. Please try again.';
                    pane.prepend(err);
                }
            });
    });

}());
