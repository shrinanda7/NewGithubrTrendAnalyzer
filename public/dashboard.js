/* ================================================================
   GitHub Trend Analyzer — Dashboard JavaScript
   ================================================================ */

const COLORS = [
    '#63b3ed','#68d391','#b794f4','#f687b3','#76e4f7',
    '#fbd38d','#fc8181','#4fd1c5','#f6ad55','#a3bffa',
    '#9ae6b4','#d6bcfa','#81e6d9','#feb2b2','#bee3f8',
    '#c6f6d5','#fefcbf','#fbb6ce','#b2f5ea','#e9d8fd'
];

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { labels: { color: '#8896ab', font: { family: 'DM Sans, sans-serif', size: 11 }, padding: 16 } }
    },
    scales: {
        x: { ticks: { color: '#5a6578', font: { family: 'DM Sans', size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
        y: { ticks: { color: '#5a6578', font: { family: 'DM Sans', size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } }
    }
};

let chartInstances = {};
let DATA = {};

// ---- Navigation ----
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        link.classList.add('active');
        document.getElementById(link.dataset.section).classList.add('active');
    });
});

function destroyChart(id) {
    if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

function createChart(id, config) {
    destroyChart(id);
    // Replace the canvas element to guarantee a clean rendering context
    const oldCanvas = document.getElementById(id);
    if (oldCanvas) {
        const parent = oldCanvas.parentNode;
        const newCanvas = document.createElement('canvas');
        newCanvas.id = id;
        parent.replaceChild(newCanvas, oldCanvas);
        chartInstances[id] = new Chart(newCanvas, config);
    }
}

function statCard(value, label) {
    return `<div class="stat-card"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
}

function fmt(n) {
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
    return n.toString();
}

// ---- Data Loading ----
async function loadAll() {
    const endpoints = [
        ['langPop', '/data/1_language_popularity.json'],
        ['topRepos', '/data/2_top_repos_by_stars.json'],
        ['topics', '/data/3_topic_trends.json'],
        ['growth', '/data/4_yoy_growth.json'],
        ['starDist', '/data/5_star_distribution.json'],
        ['activity', '/data/6_activity_index.json'],
        ['ecosystem', '/data/7_ecosystem_health.json'],
        ['perf', '/data/performance_timing.json']
    ];
    const results = await Promise.all(endpoints.map(([,url]) => fetch(url).then(r => r.json())));
    endpoints.forEach(([key], i) => DATA[key] = results[i]);
    renderAll();
}

// ---- Render All ----
function renderAll() {
    renderOverview();
    renderLangPop();
    renderTopRepos();
    renderTopics();
    renderGrowth();
    renderStarDist();
    renderActivity();
    renderEcosystem();
    renderPerformance();
}

// ---- 0. Overview ----
function renderOverview() {
    const perf = DATA.perf || {};
    const langs = [...new Set((DATA.langPop||[]).map(d => d.language))];
    const years = [...new Set((DATA.langPop||[]).map(d => d.year))].sort();

    document.getElementById('overview-stats').innerHTML =
        statCard(fmt(perf.total_records_processed || 0), 'Events Processed') +
        statCard(langs.length, 'Languages') +
        statCard(years.length, 'Years Covered') +
        statCard((perf.total_pipeline_seconds || 0).toFixed(1) + 's', 'Spark Runtime');

    // Line chart: top 10 languages over time
    const top10 = langs.slice(0, 10);
    createChart('overviewChart', {
        type: 'line',
        data: {
            labels: years,
            datasets: top10.map((lang, i) => ({
                label: lang,
                data: years.map(y => { const e = (DATA.langPop||[]).find(d => d.language===lang && d.year===y); return e ? e.event_count : 0; }),
                borderColor: COLORS[i], backgroundColor: COLORS[i]+'20',
                tension: 0.4, fill: false, pointRadius: 3, borderWidth: 2
            }))
        },
        options: { ...chartDefaults }
    });
}

// ---- 1. Language Popularity ----
function renderLangPop(selectedYear) {
    const data = DATA.langPop || [];
    const years = [...new Set(data.map(d => d.year))].sort((a,b) => a-b);
    const sel = document.getElementById('langYearSelect');

    if (!sel.dataset.initialized) {
        sel.innerHTML = '';
        years.forEach(y => { const o = document.createElement('option'); o.value = y; o.text = y; sel.appendChild(o); });
        sel.value = years[years.length - 1];
        sel.onchange = function() { renderLangPop(Number(this.value)); };
        sel.dataset.initialized = 'true';
    }

    const yr = selectedYear != null ? selectedYear : Number(sel.value);
    if (selectedYear != null) sel.value = yr;
    const filtered = data.filter(d => d.year === yr).sort((a,b) => b.event_count - a.event_count).slice(0, 15);

    createChart('langBarChart', {
        type: 'bar',
        data: {
            labels: filtered.map(d => d.language),
            datasets: [{ label: `Events in ${yr}`, data: filtered.map(d => d.event_count),
                backgroundColor: filtered.map((_,i) => COLORS[i%COLORS.length]), borderRadius: 8 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, ticks: { color: '#5a6578' }, grid: { color: 'rgba(255,255,255,0.03)' } },
                y: { ticks: { color: '#8896ab' }, grid: { display: false } }
            }
        }
    });

    createChart('langPieChart', {
        type: 'doughnut',
        data: {
            labels: filtered.map(d => d.language),
            datasets: [{ data: filtered.map(d => d.event_count),
                backgroundColor: filtered.map((_,i) => COLORS[i%COLORS.length]), borderWidth: 0 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#8896ab', font: { size: 10 } } } } }
    });
}

// ---- 2. Top Repos ----
function renderTopRepos() {
    const data = (DATA.topRepos || []).slice(0, 50);
    const tbody = document.querySelector('#repoTable tbody');
    tbody.innerHTML = data.map((d, i) =>
        `<tr><td>${i+1}</td><td>${d.repo_name}</td><td>${d.language}</td><td>${fmt(d.max_stars)}</td><td>${fmt(d.max_forks)}</td><td>${fmt(d.total_events)}</td></tr>`
    ).join('');
}

// ---- 3. Topics ----
function renderTopics(selectedYear) {
    const data = DATA.topics || [];
    const years = [...new Set(data.map(d => d.year))].sort((a,b) => a-b);
    const sel = document.getElementById('topicYearSelect');

    if (!sel.dataset.initialized) {
        sel.innerHTML = '';
        years.forEach(y => { const o = document.createElement('option'); o.value = y; o.text = y; sel.appendChild(o); });
        sel.value = years[years.length - 1];
        sel.onchange = function() { renderTopics(Number(this.value)); };
        sel.dataset.initialized = 'true';
    }

    const yr = selectedYear != null ? selectedYear : Number(sel.value);
    if (selectedYear != null) sel.value = yr;
    const filtered = data.filter(d => d.year === yr).sort((a,b) => b.count - a.count).slice(0, 12);

    createChart('topicBarChart', {
        type: 'bar',
        data: {
            labels: filtered.map(d => d.topic),
            datasets: [{ label: `Mentions in ${yr}`, data: filtered.map(d => d.count),
                backgroundColor: 'rgba(99,179,237,0.5)', borderRadius: 6 }]
        },
        options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
    });

    createChart('topicDoughnut', {
        type: 'doughnut',
        data: {
            labels: filtered.map(d => d.topic),
            datasets: [{ data: filtered.map(d => d.count), backgroundColor: filtered.map((_,i) => COLORS[i%COLORS.length]), borderWidth: 0 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#8896ab', font: { size: 10 } } } } }
    });
}

// ---- 4. YoY Growth ----
function renderGrowth(selectedYear) {
    const data = DATA.growth || [];
    const years = [...new Set(data.map(d => d.year))].sort((a,b) => a-b);
    const sel = document.getElementById('growthYearSelect');

    if (!sel.dataset.initialized) {
        sel.innerHTML = '';
        years.forEach(y => { const o = document.createElement('option'); o.value = y; o.text = y; sel.appendChild(o); });
        // Default to 2025 (last full year) instead of 2026 (partial)
        const defaultYear = years.includes(2025) ? 2025 : years[years.length - 1];
        sel.value = defaultYear;
        sel.onchange = function() { renderGrowth(Number(this.value)); };
        sel.dataset.initialized = 'true';
    }

    const yr = selectedYear != null ? selectedYear : Number(sel.value);
    if (selectedYear != null) sel.value = yr;
    const filtered = data.filter(d => d.year === yr).sort((a,b) => b.growth_rate - a.growth_rate).slice(0, 15);

    createChart('growthChart', {
        type: 'bar',
        data: {
            labels: filtered.map(d => d.language),
            datasets: [{ label: `Growth Rate % (${yr} vs ${yr-1})`, data: filtered.map(d => d.growth_rate),
                backgroundColor: filtered.map(d => d.growth_rate >= 0 ? 'rgba(104,211,145,0.6)' : 'rgba(252,129,129,0.6)'),
                borderRadius: 6 }]
        },
        options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
    });
}

// ---- 5. Star Distribution ----
function renderStarDist() {
    const data = (DATA.starDist || []).sort((a,b) => b.avg_stars - a.avg_stars).slice(0, 15);

    createChart('starAvgChart', {
        type: 'bar',
        data: {
            labels: data.map(d => d.language),
            datasets: [
                { label: 'Avg Stars', data: data.map(d => d.avg_stars), backgroundColor: 'rgba(183,148,244,0.5)', borderRadius: 6 },
                { label: 'Median Stars', data: data.map(d => d.median_stars), backgroundColor: 'rgba(246,135,179,0.5)', borderRadius: 6 }
            ]
        },
        options: chartDefaults
    });

    // Fix: convert total_stars to millions so chart scale works properly
    const sorted = [...(DATA.starDist||[])].sort((a,b) => b.total_stars - a.total_stars).slice(0, 15);
    createChart('starTotalChart', {
        type: 'bar',
        data: {
            labels: sorted.map(d => d.language),
            datasets: [{ label: 'Total Stars (Millions)', data: sorted.map(d => +(d.total_stars / 1e6).toFixed(1)),
                backgroundColor: sorted.map((_,i) => COLORS[i%COLORS.length]), borderRadius: 8 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => `${ctx.raw}M stars` } }
            },
            scales: {
                x: { beginAtZero: true, ticks: { color: '#5a6578' }, grid: { color: 'rgba(255,255,255,0.03)' },
                     title: { display: true, text: 'Stars (Millions)', color: '#8896ab' } },
                y: { ticks: { color: '#8896ab' }, grid: { display: false } }
            }
        }
    });
}

// ---- 6. Activity Index ----
function renderActivity() {
    const data = (DATA.activity || []).slice(0, 50);
    const tbody = document.querySelector('#activityTable tbody');
    tbody.innerHTML = data.map((d, i) =>
        `<tr><td>${i+1}</td><td>${d.repo_name}</td><td>${d.language}</td><td>${fmt(d.total_events)}</td><td>${d.distinct_event_types}</td><td>${d.years_active}</td><td>${fmt(d.activity_score)}</td></tr>`
    ).join('');
}

// ---- 7. Ecosystem Health ----
function renderEcosystem() {
    const data = (DATA.ecosystem || []).sort((a,b) => b.health_score - a.health_score).slice(0, 15);

    createChart('healthChart', {
        type: 'bar',
        data: {
            labels: data.map(d => d.language),
            datasets: [{ label: 'Health Score (0-100)', data: data.map(d => d.health_score),
                backgroundColor: data.map((_,i) => COLORS[i%COLORS.length]), borderRadius: 8 }]
        },
        options: chartDefaults
    });

    // Radar for top 5
    const top5 = data.slice(0, 5);
    const maxR = Math.max(...data.map(d => d.total_repos));
    const maxS = Math.max(...data.map(d => d.total_stars));
    const maxF = Math.max(...data.map(d => d.total_forks));
    const maxE = Math.max(...data.map(d => d.total_events));
    const maxT = Math.max(...data.map(d => d.avg_topics));

    createChart('radarChart', {
        type: 'radar',
        data: {
            labels: ['Repos', 'Stars', 'Forks', 'Activity', 'Topics'],
            datasets: top5.map((d, i) => ({
                label: d.language,
                data: [
                    (d.total_repos/maxR*100).toFixed(1),
                    (d.total_stars/maxS*100).toFixed(1),
                    (d.total_forks/maxF*100).toFixed(1),
                    (d.total_events/maxE*100).toFixed(1),
                    (d.avg_topics/maxT*100).toFixed(1)
                ],
                borderColor: COLORS[i], backgroundColor: COLORS[i]+'20', borderWidth: 2, pointRadius: 3
            }))
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { r: { ticks: { color: '#5a6578', backdropColor: 'transparent' }, grid: { color: 'rgba(255,255,255,0.04)' }, pointLabels: { color: '#8896ab' } } },
            plugins: { legend: { labels: { color: '#8896ab' } } }
        }
    });
}

// ---- 8. Performance ----
function renderPerformance() {
    const perf = DATA.perf || {};
    const analyses = perf.analyses || [];

    document.getElementById('perf-stats').innerHTML =
        statCard((perf.total_pipeline_seconds || 0).toFixed(2) + 's', 'Total Runtime') +
        statCard(fmt(perf.total_records_processed || 0), 'Records Processed') +
        statCard(fmt(perf.records_removed_in_cleaning || 0), 'Records Cleaned') +
        statCard(analyses.length, 'Analysis Phases');

    createChart('perfChart', {
        type: 'bar',
        data: {
            labels: analyses.map(a => a.analysis.replace('Language ', 'Lang ').substring(0, 30)),
            datasets: [
                { label: 'Mapper Phase (s)', data: analyses.map(a => a.mapper_phase_seconds), backgroundColor: 'rgba(99,179,237,0.55)', borderRadius: 6 },
                { label: 'Reducer Phase (s)', data: analyses.map(a => a.reducer_phase_seconds), backgroundColor: 'rgba(183,148,244,0.55)', borderRadius: 6 }
            ]
        },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, x: { ...chartDefaults.scales.x, ticks: { ...chartDefaults.scales.x.ticks, maxRotation: 45 } } } }
    });
}

// ---- 9. User Search (Live GitHub API) ----
function initUserSearch() {
    const btn = document.getElementById('userSearchBtn');
    const input = document.getElementById('userSearchInput');
    if (!btn || !input) return;

    async function doSearch() {
        const query = input.value.trim();
        if (!query) return;

        const resultDiv = document.getElementById('userResult');
        const noResultDiv = document.getElementById('userNoResult');
        const loadingSpan = document.getElementById('userSearchLoading');

        resultDiv.style.display = 'none';
        noResultDiv.style.display = 'none';
        loadingSpan.style.display = 'inline';
        btn.disabled = true;

        try {
            const resp = await fetch(`https://api.github.com/users/${encodeURIComponent(query)}`);
            if (resp.status === 404) { noResultDiv.textContent = `User '${query}' not found on GitHub.`; noResultDiv.style.display = 'block'; return; }
            if (resp.status === 403) { noResultDiv.textContent = 'GitHub API rate limit reached. Try again in a minute.'; noResultDiv.style.display = 'block'; return; }
            const user = await resp.json();

            const [reposResp, eventsResp] = await Promise.all([
                fetch(`https://api.github.com/users/${encodeURIComponent(query)}/repos?per_page=100&sort=stars&direction=desc`),
                fetch(`https://api.github.com/users/${encodeURIComponent(query)}/events?per_page=100`)
            ]);
            const repos = reposResp.ok ? await reposResp.json() : [];
            const events = eventsResp.ok ? await eventsResp.json() : [];

            // Analyze
            const langCounts = {};
            repos.forEach(r => { if(r.language) langCounts[r.language] = (langCounts[r.language]||0) + 1; });
            const eventCounts = {};
            events.forEach(e => { eventCounts[e.type] = (eventCounts[e.type]||0) + 1; });
            const totalStars = repos.reduce((s,r) => s + (r.stargazers_count||0), 0);
            const totalForks = repos.reduce((s,r) => s + (r.forks_count||0), 0);
            const langBreakdown = Object.entries(langCounts).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([l,c])=>({language:l,count:c}));
            const actBreakdown = Object.entries(eventCounts).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([e,c])=>({event_type:e,count:c}));
            const favLang = langBreakdown.length ? langBreakdown[0].language : 'N/A';

            const data = {
                username: user.login, name: user.name, avatar_url: user.avatar_url,
                bio: user.bio, location: user.location, company: user.company,
                public_repos: user.public_repos, followers: user.followers,
                total_stars: totalStars, total_forks: totalForks,
                favorite_language: favLang, languages_used: Object.keys(langCounts).length,
                language_breakdown: langBreakdown, activity_breakdown: actBreakdown,
                top_repos: repos.slice(0,10).map(r => ({name:r.full_name,language:r.language,stars:r.stargazers_count,forks:r.forks_count,description:(r.description||'').slice(0,100)}))
            };

            if (data.error) {
                noResultDiv.textContent = data.error;
                noResultDiv.style.display = 'block';
                resultDiv.style.display = 'none';
                return;
            }

            noResultDiv.style.display = 'none';
            resultDiv.style.display = 'block';

            // Profile header with avatar
            document.getElementById('user-profile-header').innerHTML = `
                <img src="${data.avatar_url}" style="width:80px;height:80px;border-radius:50%;border:3px solid var(--accent-1);">
                <div>
                    <h2 style="margin:0;color:var(--accent-1);font-weight:600;">@${data.username}</h2>
                    <p style="margin:4px 0;color:var(--text-secondary);">${data.name || ''} ${data.location ? '&middot; ' + data.location : ''} ${data.company ? '&middot; ' + data.company : ''}</p>
                    <p style="margin:0;color:var(--text-muted);font-size:0.85rem;">${data.bio || ''}</p>
                </div>`;

            // Stats cards
            document.getElementById('user-stats').innerHTML =
                statCard(data.public_repos, 'Public Repos') +
                statCard(fmt(data.total_stars), 'Total Stars') +
                statCard(fmt(data.total_forks), 'Total Forks') +
                statCard(data.followers, 'Followers') +
                statCard(data.languages_used, 'Languages') +
                statCard(data.favorite_language, 'Top Language');

            // Language distribution chart
            const langs = data.language_breakdown || [];
            if (langs.length > 0) {
                createChart('userLangChart', {
                    type: 'doughnut',
                    data: {
                        labels: langs.map(l => l.language),
                        datasets: [{ data: langs.map(l => l.count),
                            backgroundColor: langs.map((_,i) => COLORS[i%COLORS.length]), borderWidth: 0 }]
                    },
                    options: { responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { position: 'right', labels: { color: '#8896ab', font: { size: 11 } } } } }
                });
            }

            // Activity breakdown chart
            const acts = data.activity_breakdown || [];
            if (acts.length > 0) {
                createChart('userActivityChart', {
                    type: 'bar',
                    data: {
                        labels: acts.map(a => a.event_type.replace('Event', '')),
                        datasets: [{ label: 'Recent Events', data: acts.map(a => a.count),
                            backgroundColor: 'rgba(99,179,237,0.5)', borderRadius: 6 }]
                    },
                    options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
                });
            }

            // Top repos table
            const repos = data.top_repos || [];
            const tbody = document.querySelector('#userRepoTable tbody');
            tbody.innerHTML = repos.map((r, i) =>
                `<tr><td>${i+1}</td><td><a href="https://github.com/${r.name}" target="_blank" style="color:var(--accent-1);text-decoration:none;">${r.name}</a></td><td>${r.language||'N/A'}</td><td>${fmt(r.stars)}</td><td>${fmt(r.forks)}</td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.description}</td></tr>`
            ).join('');

        } catch (err) {
            noResultDiv.textContent = 'Network error. Please check your connection.';
            noResultDiv.style.display = 'block';
        } finally {
            loadingSpan.style.display = 'none';
            btn.disabled = false;
        }
    }

    btn.addEventListener('click', doSearch);
    input.addEventListener('keypress', e => { if (e.key === 'Enter') doSearch(); });
}

// ---- Init ----
loadAll().then(() => initUserSearch());
