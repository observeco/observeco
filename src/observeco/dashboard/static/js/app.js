// ── Toggle QB Detail (Variant C) ──────────────────────────
function toggleQbDetail(agent) {
  var panel = document.getElementById('qb-detail-' + agent);
  if (!panel) return;
  panel.classList.toggle('open');
  var isOpen = panel.classList.contains('open');
  if (!isOpen) return;
  if (panel.dataset.loaded) return;
  panel.dataset.loaded = 'true';
  fetch('/api/fleet/qb-categories?agent=' + encodeURIComponent(agent) + '&token=' + encodeURIComponent(window.__OBSERVECO_TOKEN || ''))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.categories || data.categories.length === 0) {
        panel.innerHTML = '<div style="padding:12px;text-align:center;color:var(--fg-3);font-size:12px;">No benchmark data yet. <button class="qb-run-btn" onclick="openQualityBenchmark(\'' + agent + '\')">▶ Run first benchmark</button></div>';
        return;
      }
      var overall_pct = Math.round(data.overall * 100);
      var overall_color = overall_pct >= 70 ? '#22c55e' : overall_pct >= 40 ? '#eab308' : '#ef4444';
      var worst = data.categories[data.categories.length - 1];
      var writeup = '';
      if (overall_pct >= 70) {
        writeup = _qb_writeup_strong(agent, data);
      } else if (overall_pct >= 40) {
        writeup = _qb_writeup_moderate(agent, data);
      } else {
        writeup = _qb_writeup_weak(agent, data, worst);
      }
      var html = '<div class="qb-writeup">' + writeup + '</div>' +
        '<table class="qb-table">';
      var catIcons = {reasoning:'🧮', coding:'💻', extraction:'📄', tool_use:'🛠', instruction_following:'📋', safety:'🛡'};
      for (var i = 0; i < data.categories.length; i++) {
        var c = data.categories[i];
        var icon = catIcons[c.name] || '📊';
        var pct = Math.round(c.accuracy * 100);
        var color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444';
        html += '<tr><td>' + icon + ' ' + c.name + '</td><td>' + c.pass + '/' + c.total + ' pass</td><td style="color:' + color + '">' + pct + '%</td></tr>';
      }
      html += '</table>' +
        '<div style="text-align:right;margin-top:8px;">' +
          '<button class="btn btn-sm btn-outline" onclick="openQualityBenchmark(\'' + agent + '\')">▶ Run Benchmark</button>' +
        '</div>';
      panel.innerHTML = html;
    })
    .catch(function() {
      panel.innerHTML = '<div style="padding:12px;text-align:center;color:var(--fg-3);font-size:12px;">Could not load breakdown</div>';
    });
}

// ─── Quality Benchmark modal (per-agent canary) ───

// ── QB Write-up generators (Variant C context) ────────
function _qb_writeup_strong(agent, data) {
  var pct = Math.round(data.overall * 100);
  return '<strong style="color:#22c55e">✓ ' + agent + ' is performing well</strong> (' + pct + '% pass across ' + data.total + ' tasks). ' +
    'All categories above 40%. No critical gaps detected. Consider hardening the lowest category: ' +
    data.categories[data.categories.length - 1].name + '.';
}
function _qb_writeup_moderate(agent, data) {
  var pct = Math.round(data.overall * 100);
  var weakest = data.categories[data.categories.length - 1];
  return '<strong style="color:#eab308">⚠ ' + agent + ' is borderline</strong> (' + pct + '% pass). ' +
    'Weakest category: ' + weakest.name + ' (' + Math.round(weakest.accuracy * 100) + '%). ' +
    'Prioritize a retrain or prompt revision on this category before production use.';
}
function _qb_writeup_weak(agent, data, worst) {
  var pct = Math.round(data.overall * 100);
  return '<strong style="color:#ef4444">✗ ' + agent + ' is underperforming</strong> (' + pct + '% pass, ' + data.failed + ' failed). ' +
    'Critical gap in <strong>' + worst.name + '</strong> (' + Math.round(worst.accuracy * 100) + '%). ' +
    'Do not deploy without remediation. Run a focused benchmark on weak categories.';
}

// ── Judge Reasoning Load ──────────────────────────────────
function loadJudgeReasoning(taskId) {
  var panel = document.getElementById('judge-' + taskId);
  if (!panel || panel.dataset.loaded) return;
  panel.dataset.loaded = 'true';
  fetch('/api/capability/canary/judge-reasoning?task_id=' + encodeURIComponent(taskId))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.assertions || data.assertions.length === 0) {
        panel.innerHTML = '<div style="padding:12px;text-align:center;color:var(--fg-3);font-size:12px;">No judge results yet — run a canary first</div>';
        return;
      }
      var html = '';
      for (var i = 0; i < data.assertions.length; i++) {
        var a = data.assertions[i];
        var scoreClass = a.score >= 0.8 ? 'pass' : a.score >= 0.4 ? 'partial' : 'fail';
        html += '<div class="assertion-row">' +
          '<div class="assertion-score ' + scoreClass + '">' +
            '<span>' + Math.round(a.score * 100) + '</span>' +
          '</div>' +
          '<div class="assertion-detail">' +
            '<div class="name">' + a.type + ': ' + (a.name || '') + '</div>' +
            '<div class="reasoning">' + (a.reasoning || '') + '</div>' +
          '</div></div>';
      }
      panel.innerHTML = html;
    })
    .catch(function() {
      panel.innerHTML = '<div style="padding:12px;text-align:center;color:var(--fg-3);font-size:12px;">Could not load judge results</div>';
    });
}

// Wire up expand listeners — load judge reasoning when task row clicked
document.addEventListener('click', function(e) {
  var row = e.target.closest('.task-row');
  if (row) {
    var taskId = row.closest('[data-task-id]');
    if (taskId) loadJudgeReasoning(taskId.getAttribute('data-task-id'));
  }
});

function openQualityBenchmark(agent) {
  // Fetch the canary card HTML and wrap in a modal
  var token = window.__OBSERVECO_TOKEN || '';
  var headers = {};
  if (token) headers['X-ObserveCo-Token'] = token;
  fetch('/api/fleet/canary-card/' + encodeURIComponent(agent), {headers: headers})
    .then(function(r) { return r.text(); })
    .then(function(html) {
      var modal = document.createElement('div');
      modal.className = 'scrim';
      modal.id = 'qbModal';
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:100;';
      modal.onclick = function(e) { if (e.target === modal) modal.remove(); };
      modal.innerHTML = '<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;padding:24px;max-width:520px;width:90%;max-height:80vh;overflow-y:auto;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">' +
        '<h3 style="font-size:17px;font-weight:600;color:#f8fafc;margin:0;">🔬 Quality Benchmark: ' + agent + '</h3>' +
        '<span onclick="this.closest(\'.scrim\').remove()" style="cursor:pointer;font-size:20px;color:#64748b;">✕</span>' +
        '</div>' +
        '<div id="qbContent">' + html + '</div>' +
        '<div style="margin-top:16px;display:flex;gap:8px;">' +
        '<button onclick="runCanaryFor(\'' + agent + '\')" style="background:#3b82f6;border:none;color:white;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;">▶ Run Benchmark</button>' +
        '<button onclick="this.closest(\'.scrim\').remove()" style="border:1px solid #334155;background:transparent;color:#94a3b8;padding:8px 20px;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;">Close</button>' +
        '</div>' +
        '<div id="qbProgress" style="display:none;margin-top:12px;padding:12px;background:#0f172a;border:1px solid #334155;border-radius:8px;font-size:13px;line-height:1.6;"></div>' +
        '</div>';
      document.body.appendChild(modal);
    });
}

// Run canary for a specific agent with live progress — updates the card row in real-time
function runCanaryFor(agent) {
  var token = window.__OBSERVECO_TOKEN || '';
  var authHeaders = {};
  if (token) authHeaders['X-ObserveCo-Token'] = token;

  // Show progress on the card row immediately
  _updateQbRow(agent, '⏳', 'starting...', 'var(--muted)');

  fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {method: 'POST', headers: authHeaders})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        _updateQbRow(agent, '⏳', 'running...', 'var(--warn)');
        // Close the modal so user can move on
        var modal = document.getElementById('qbModal');
        if (modal) modal.remove();
        // Poll for progress every 5s — updates the card row live
        var pollStart = Date.now();
        var poll = setInterval(function() {
          // Stop polling after 5 minutes no matter what
          if (Date.now() - pollStart > 300000) {
            clearInterval(poll);
            _updateQbRow(agent, '❌', 'timeout', 'var(--danger)');
            return;
          }
          fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent), {headers: authHeaders})
            .then(function(r) { return r.json(); })
            .then(function(s) {
              if (s.running) {
                var pct = s.total_tasks > 0 ? Math.round((s.pass_count + s.fail_count) / s.total_tasks * 100) : 0;
                _updateQbRow(agent, '⏳', pct + '% (' + (s.pass_count + s.fail_count) + '/' + s.total_tasks + ')', 'var(--warn)');
              } else if (s.completed) {
                clearInterval(poll);
                var acc = s.total_tasks > 0 ? Math.round(s.pass_count / s.total_tasks * 100) : 0;
                var color = acc >= 70 ? 'var(--accent)' : acc >= 40 ? 'var(--warn)' : 'var(--danger)';
                _updateQbRow(agent, acc + '%', s.pass_count + '/' + s.total_tasks + ' pass', color);
                setTimeout(function() {
                  htmx.ajax('GET', '/api/fleet/agents', {target: '#fleetGrid', swap: 'innerHTML'});
                }, 2000);
              } else {
                clearInterval(poll);
              }
            });
        }, 5000);
      } else {
        _updateQbRow(agent, '❌', 'failed', 'var(--danger)');
      }
    })
    .catch(function(e) {
      _updateQbRow(agent, '❌', 'error', 'var(--danger)');
    });
}

// Update the Quality Benchmark row on the agent card
function _updateQbRow(agent, val, sub, color) {
  var row = document.querySelector('[data-qb="' + agent.replace(/"/g, '') + '"]');
  if (row) {
    var valEl = row.querySelector('.row-val');
    var subEl = row.querySelector('.row-sub');
    if (valEl) { valEl.textContent = val; valEl.style.color = color; }
    if (subEl) {
      subEl.innerHTML = sub + ' <span class="row-chev">▸</span>';
    }
  }
}
function applyFilter(btn, filter) {
  document.querySelectorAll('.filter-chip').forEach(function(c) {
    c.classList.remove('active');
  });
  btn.classList.add('active');
  // Reload fleet grid with backend filter so search respects it
  var q = document.getElementById('agentSearch').value;
  htmx.ajax('GET', '/api/fleet/agents?status_filter=' + filter + '&q=' + encodeURIComponent(q), {target: '#fleetGrid', swap: 'innerHTML'});
}

// ─── Tab switching (v2 nav → existing tab-content divs) ───
function switchTab(tab, btn) {
  window._lastTab = tab;
  try {
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    var tabMap = {
      'fleet': 'tabFleet',
      'alerts': 'tabAlerts',
      'timeline': 'tabTimeline',
      'tokens': 'tabTokens',
      'brain': 'tabBrain',
      'drift': 'tabDrift',
      'compare': 'tabCompare',
      'capability': 'tabCapability',
      'anomalies': 'tabAnomalies',
      'health-score': 'tabHealthScore',
      'traces': 'tabTraces',
      'config': 'tabConfig',
      'billing': 'tabBilling'
    };

    var targetId = tabMap[tab] || 'tabFleet';
    var target = document.getElementById(targetId);
    if (target) { target.classList.add('active'); if (tab === 'tokens') htmx.ajax('GET', '/api/analytics/tokens', {target: '#analyticsContent', swap: 'innerHTML'}); }
  } catch (e) {
    console.error('switchTab error:', e);
    showTabError();
  }
}

// ponytail: error banner is generic — shows for any htmx failure, not just tab loads.
// Upgrade: pass e.detail to showTabError for context-specific messaging.
function showTabError() {
  var area = document.getElementById('tabContentArea');
  if (!area) return;
  var banner = document.getElementById('tabErrorBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'tabErrorBanner';
    area.insertBefore(banner, area.firstChild);
  }
  banner.innerHTML = '<div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);padding:8px 12px;border-radius:4px;margin-bottom:8px;display:flex;align-items:center;gap:8px;color:#fca5a5">⚠️ Failed to load tab. <button onclick="switchTab(window._lastTab)" style="margin-left:auto;padding:4px 10px;border:1px solid rgba(239,68,68,0.6);border-radius:3px;background:rgba(239,68,68,0.2);cursor:pointer;color:#fca5a5">Retry</button></div>';
}

document.addEventListener('htmx:responseError', function() { showTabError(); });

// Wire nav tab clicks
document.addEventListener('click', function(e) {
  var tab = e.target.closest('.nav-tab.clickable');
  if (!tab) return;
  var tabName = tab.getAttribute('data-tab');
  if (!tabName) return;
  if (tab.querySelector('.soon')) return;
  switchTab(tabName, tab);
});

// ─── Keyboard tab shortcuts (1-9) ───
document.addEventListener('keydown', function(e) {
  if (e.target.closest('input,textarea,select')) return;
  var n = parseInt(e.key, 10);
  if (n < 1 || n > 9) return;
  var tabs = document.querySelectorAll('.nav-tab.clickable:not(:has(.soon))');
  var tab = tabs[n - 1];
  if (tab) switchTab(tab.getAttribute('data-tab'), tab);
});

// ─── Card toggle handlers (for v2 collapsible cards) ───
function _attachCardToggles() {
  document.querySelectorAll('#fleetGrid [data-toggle]').forEach(function(t) {
    if (t._toggleAttached) return;
    t._toggleAttached = true;
    var toggle = function() { t.closest('.card').classList.toggle('open'); };
    t.addEventListener('click', toggle);
    t.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  });
  document.querySelectorAll('#fleetGrid [data-health]').forEach(function(h) {
    if (h._healthAttached) return;
    h._healthAttached = true;
    var toggle = function() {
      var open = h.getAttribute('aria-expanded') === 'true';
      h.setAttribute('aria-expanded', String(!open));
    };
    h.addEventListener('click', toggle);
  });
}
document.addEventListener('htmx:afterSwap', function(e) {
  if (e.detail.target && e.detail.target.id === 'fleetGrid') {
    _attachCardToggles();
  }
});
// ponytail: Also run on DOMContentLoaded in case fleet grid loaded before this script ran.
document.addEventListener('DOMContentLoaded', _attachCardToggles);

// ─── Verdict agent name → modal ───
document.addEventListener('click', function(e) {
  var el = e.target.closest('.agent');
  if (el) htmx.ajax('GET', '/api/fleet/modal/' + encodeURIComponent(el.textContent.trim()), {target: '#modalContainer', swap: 'innerHTML'});
});

// ─── Glossary tooltips ───
var _glossary = {
  'fleet-compare': 'Side-by-side comparison of all agents across token composition, drift, and error metrics.',
  'brain-analysis': 'Detailed breakdown of what data feeds each agent\'s context window, including memory, tools, and skill usage.',
  'memory-garden': 'Memory hygiene automation: scans agent memory for duplicates, contradictions, and stale entries. Assigns a health score (A-F). Run `observeco memory garden` to audit any agent.'
};
function showGlossary(term, event) {
  // Try API first for full detail + FAQ
  fetch('/api/glossary/' + encodeURIComponent(term))
    .then(function(r) { return r.text(); })
    .then(function(html) {
      if (html && !html.includes('glossary-not-found')) {
        _showGlossaryPopup(html, event);
        return;
      }
      // Fallback to hardcoded definition
      var def = _glossary[term];
      if (!def) return;
      _showGlossaryPopup('<div style="padding:4px;font-size:13px;line-height:1.6;">' + def + '</div>', event);
    })
    .catch(function() {
      var def = _glossary[term];
      if (!def) return;
      _showGlossaryPopup('<div style="padding:4px;font-size:13px;line-height:1.6;">' + def + '</div>', event);
    });
}
function _showGlossaryPopup(html, event) {
  var existing = document.getElementById('glossaryPopup');
  if (existing) existing.remove();
  var popup = document.createElement('div');
  popup.id = 'glossaryPopup';
  popup.style.cssText = 'position:fixed;z-index:9999;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 14px;max-width:360px;font-size:12px;color:#f8fafc;line-height:1.5;box-shadow:0 8px 24px rgba(0,0,0,0.4);';
  popup.innerHTML = html;
  var x = event.clientX, y = event.clientY;
  popup.style.left = Math.min(x, window.innerWidth - 380) + 'px';
  popup.style.top = Math.min(y + 20, window.innerHeight - 80) + 'px';
  document.body.appendChild(popup);
  document.addEventListener('click', function _close() { popup.remove(); document.removeEventListener('click', _close); }, {once: true});
}
// ponytail: hardcoded definition map — add new terms here as tabs ship.
// Upgrade: fetch from /api/glossary endpoint when more than ~10 terms.

// ─── Auto-refresh every 30s ───
setInterval(function() {
  var sp = document.querySelector('#fleetGrid') ? document.querySelector('#fleetGrid').parentElement.scrollTop : 0;
  // Preserve filter and search state during auto-refresh
  var q = document.getElementById('agentSearch') ? document.getElementById('agentSearch').value : '';
  var activeFilter = document.querySelector('.filter-chip.active') ? document.querySelector('.filter-chip.active').getAttribute('data-filter') || '' : '';
  var fleetUrl = '/api/fleet/agents';
  if (q || activeFilter) {
    fleetUrl += '?';
    if (q) fleetUrl += 'q=' + encodeURIComponent(q);
    if (q && activeFilter) fleetUrl += '&';
    if (activeFilter) fleetUrl += 'status_filter=' + activeFilter;
  }
  // ponytail: innerHTML, NOT outerHTML. outerHTML on first refresh removes the container (id lost), then htmx falls back to BODY as target on second refresh, replacing entire page with verdict HTML — black screen.
  htmx.ajax('GET', '/api/fleet/verdict', {target: '#verdictContainer', swap: 'innerHTML'});
  htmx.ajax('GET', fleetUrl, {target: '#fleetGrid', swap: 'innerHTML'});
  htmx.ajax('GET', '/api/alerts/live', {target: '#alertsContainer', swap: 'innerHTML'});
  setTimeout(function() {
    if (document.querySelector('#fleetGrid')) {
      document.querySelector('#fleetGrid').parentElement.scrollTop = sp;
    }
  }, 100);
  var updatedEl = document.getElementById('fleetUpdated');
  if (updatedEl) updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
}, 30000);

// ─── Token Analytics chart (fired after htmx swap) ───
// ponytail: chart init MUST run here, not in inline <script> inside swapped HTML.
// htmx innerHTML swaps do not execute inline scripts. Global fn + afterSwap is the
// same pattern the drift chart attempts (loadDriftChart). Data arrives via window._tokenChart.
function renderTokenChart() {
  if (typeof Chart === 'undefined') return;
  var data = window._tokenChart;
  if (!data) return;
  var ctx = document.getElementById('costChart');
  if (!ctx) return;
  if (window._tokenChartInstance) window._tokenChartInstance.destroy();
  window._tokenChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [
        {label: 'Total (K)', data: data.total_data, backgroundColor: '#22c55e', stack: 'v', yAxisID: 'y', borderRadius: 2},
        {label: 'Input (K)', data: data.input_data, backgroundColor: '#3b82f6', stack: 'v', yAxisID: 'y', borderRadius: 2},
        {label: 'Output (K)', data: data.output_data, backgroundColor: '#eab308', stack: 'v', yAxisID: 'y', borderRadius: 2},
        {label: 'Cache reads (K)', data: data.cache_data, backgroundColor: '#8b5cf6', stack: 'v', yAxisID: 'y', borderRadius: 2},
        {label: 'Estimated (K)', data: data.est_data, backgroundColor: '#64748b', stack: 'v', yAxisID: 'y', borderRadius: 2}
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: {mode: 'index', intersect: false},
      plugins: {legend: {display: false}, tooltip: {callbacks: {label: function(c){return c.dataset.label + ': ' + (c.parsed.y||0).toLocaleString() + 'K';}}}},
      scales: {
        x: {stacked: true, grid: {color: 'rgba(51,65,85,.3)'}, ticks: {color: '#64748b', font: {size: 10}, maxRotation: 0, autoSkip: true, maxTicksLimit: 14}},
        y: {stacked: true, grid: {color: 'rgba(51,65,85,.2)'}, ticks: {color: '#94a3b8', font: {size: 10}, callback: function(v){return v + 'K';}}}
      }
    }
  });
  bindTokenToggles();
}

// ponytail: toggles are static HTML chips (data-idx = dataset index). They persist
// across range changes because the toggle ROW is outside the OOB-swapped chart canvas,
// but the chart instance is rebuilt each render — so we re-bind handlers here and
// apply the current hidden state from the chips' .on class.
function bindTokenToggles() {
  var chart = window._tokenChartInstance;
  if (!chart) return;
  var chips = document.querySelectorAll('#tokenSeriesToggles .tgl');
  chips.forEach(function(chip){
    var idx = parseInt(chip.getAttribute('data-idx'), 10);
    // reflect current visibility
    chip.classList.toggle('on', !chart.data.datasets[idx].hidden);
    chip.onclick = function(){
      var ds = chart.data.datasets[idx];
      ds.hidden = !ds.hidden;
      chip.classList.toggle('on', !ds.hidden);
      chart.update();
    };
  });
}

// Per-agent cache hit-rate horizontal bar chart (obs-spec-020 §5.5).
// Color by rate: red <5%, yellow 5-20%, green >20%.
function renderCacheChart() {
  if (typeof Chart === 'undefined') return;
  var data = window._cacheChart;
  if (!data || !data.agents || !data.agents.length) return;
  var ctx = document.getElementById('cacheChart');
  if (!ctx) return;
  if (window._cacheChartInstance) window._cacheChartInstance.destroy();
  var colors = data.rates.map(function(r){
    if (r < 5) return '#ef4444';
    if (r <= 20) return '#eab308';
    return '#22c55e';
  });
  window._cacheChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.agents,
      datasets: [{label: 'Cache hit rate %', data: data.rates, backgroundColor: colors, borderRadius: 2}]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {legend: {display: false}, tooltip: {callbacks: {label: function(c){return 'Hit rate: ' + c.parsed.x + '%';}}}},
      scales: {
        x: {min: 0, max: 100, grid: {color: 'rgba(51,65,85,.3)'}, ticks: {color: '#64748b', font: {size: 10}, callback: function(v){return v + '%';}}},
        y: {grid: {display: false}, ticks: {color: '#94a3b8', font: {size: 11}}}
      }
    }
  });
}
