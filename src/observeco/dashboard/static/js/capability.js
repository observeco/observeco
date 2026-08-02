// Capability page JS — loaded via <script src> to avoid htmx parser choking on { } in inline scripts
(function() {
  'use strict';

  // ── Auth headers ──
  // Token is injected on the host page (index) as window.__OBSERVECO_TOKEN and
  // a <meta name="observeco-token"> tag. It persists after htmx swaps in this fragment.
  function _authHeaders() {
    var t = (window.__OBSERVECO_TOKEN || '').trim();
    if (!t) {
      var m = document.querySelector('meta[name="observeco-token"]');
      t = (m && m.getAttribute('content') || '').trim();
    }
    return t ? { 'X-ObserveCo-Token': t } : {};
  }

  // ── Agent switcher ──
  window.switchCapabilityAgent = function(agent) {
    htmx.ajax('GET', '/api/capability/page?agent=' + encodeURIComponent(agent), {
      target: '#capabilityContainer',
      swap: 'innerHTML',
      headers: _authHeaders()
    });
  };

  // ── Navigate to Tasks tab ──
  window.navigateToTasksTab = function() {
    var el = document.getElementById('gridReport') || document.querySelector('.cap-section');
    if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
  };

  // ── Advanced section toggle ──
  window.toggleAdvanced = function() {
    var body = document.getElementById('capAdvancedBody');
    var toggle = document.querySelector('.cap-advanced-toggle');
    if (!body || !toggle) return;
    var open = body.classList.toggle('open');
    toggle.classList.toggle('open', open);
    if (open) {
      var gridEl = document.getElementById('gridTableContainer');
      if (gridEl && gridEl.querySelector('.cap-empty') && gridEl.querySelector('.cap-empty').textContent.includes('No Grid Runs')) {
        var agent = _getCapAgent();
        htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent(agent), {target: '#gridTableContainer', swap: 'innerHTML'});
      }
    }
  };

  // ── Canary runner ──
  window.runCanary = function() {
    var agent = _getCapAgent();
    var btn = document.querySelector('.cap-btn-primary') || document.querySelector('button');
    if (btn) { btn.textContent = '⏳ Running…'; btn.disabled = true; }

    var _headers = _authHeaders();

    fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {method:'POST', headers: _headers})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          showToast('Benchmark started for ' + agent + ' — this takes ~2–3 min');
          var accEl = document.getElementById('capOvBigAcc');
          if (accEl) { accEl.textContent = '...'; accEl.className = 'cap-ov-big-accuracy muted'; }
          var lastEl = document.getElementById('capOvLastTested');
          if (lastEl) lastEl.textContent = '⏳ Benchmark running…';
          var untestedEl = document.getElementById('capUntested');
          if (untestedEl) untestedEl.style.display = 'none';

          var poll = setInterval(function() {
            fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent), {headers: _headers})
              .then(function(r) { return r.json(); })
              .then(function(s) {
                if (s.running) {
                  if (accEl && s.total_tasks) {
                    var done = (s.pass_count||0) + (s.fail_count||0) + (s.hang_count||0);
                    accEl.textContent = done + '/' + s.total_tasks;
                  }
                } else if (!s.running && s.completed) {
                  clearInterval(poll);
                  showToast('Benchmark complete — refreshing');
                  htmx.ajax('GET', '/api/capability/page?agent=' + encodeURIComponent(agent), {target: '#capabilityContainer', swap: 'innerHTML'});
                } else if (!s.running && !s.completed) {
                  clearInterval(poll);
                  if (btn) { btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }
                  showToast('No test data available — try running a benchmark');
                }
              });
          }, 5000);
        } else {
          if (btn) { btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }
          showToast('Benchmark failed to start: ' + (d.error || 'unknown'));
        }
      })
      .catch(function(e) {
        if (btn) { btn.textContent = '▶ Run Benchmark'; btn.disabled = false; }
        showToast('Benchmark failed: ' + e.message);
      });
  };

  // ── Grid comparison runner ──
  window.runGrid = function() {
    var judgeSel = document.getElementById('gridJudge');
    var agentSel = document.getElementById('gridAgent');
    var agent = (agentSel && agentSel.value) ? agentSel.value : _getCapAgent();
    var selectedModels = [];
    var modelCbs = document.querySelectorAll('#gridModels .grid-model-cb:checked');
    for (var i = 0; i < modelCbs.length; i++) {
      selectedModels.push(modelCbs[i].value);
    }
    var selectedProfiles = [];
    var profileCbs = document.querySelectorAll('#gridProfiles .grid-profile-cb:checked');
    for (var j = 0; j < profileCbs.length; j++) {
      selectedProfiles.push(profileCbs[j].value);
    }
    if (selectedModels.length === 0 || selectedProfiles.length === 0) {
      showToast('Select at least one model and one profile');
      return;
    }
    // Estimate cell count before running — prevents accidental mega-runs.
    // Ask the /grid/options endpoint for the active task count, then confirm.
    fetch('/api/capability/grid/options', {headers:_authHeaders()})
      .then(function(r){ return r.json(); })
      .then(function(opts){
        var taskCount = opts.task_count || 0;
        var est = taskCount * selectedModels.length * selectedProfiles.length;
        var mins = Math.round(est * 0.15);
        var large = est > 200;
        showGridConfirm({
          models: selectedModels,
          profiles: selectedProfiles,
          judge: judgeSel ? judgeSel.value : '',
          taskCount: taskCount,
          cells: est,
          mins: mins,
          large: large,
          onRun: function() { startGridRun(agent, selectedModels, selectedProfiles, judgeSel ? judgeSel.value : ''); }
        });
      })
      .catch(function(e) { showToast('Could not estimate run: ' + e.message); });
  };

  // ── Themed grid-run confirmation modal ──
  function showGridConfirm(opts) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay active';
    overlay.id = 'gridConfirmModal';

    var modelChips = opts.models.map(function(m) {
      return '<span class="grid-confirm-chip">' + esc(m) + '</span>';
    }).join('');
    var profileChips = opts.profiles.map(function(p) {
      return '<span class="grid-confirm-chip">' + esc(p) + '</span>';
    }).join('');

    var warnHtml = '';
    if (opts.large) {
      warnHtml = '<div class="grid-confirm-warn">⚠️ Large run — about ' + opts.mins +
                 ' min. Consider trimming models or profiles.</div>';
    }

    overlay.innerHTML =
      '<div class="modal" style="max-width:560px;">' +
        '<div class="modal-header">' +
          '<div>' +
            '<h3>Run Grid Comparison</h3>' +
            '<div class="sub">' + opts.models.length + ' model(s) × ' + opts.profiles.length +
            ' profile(s) × ' + opts.taskCount + ' task(s)</div>' +
          '</div>' +
          '<button class="modal-close" id="gridConfirmClose">✕</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div style="font-size:13px;color:var(--fg);margin-bottom:12px;">' +
            'This will run <strong style="color:var(--accent);">' + opts.cells + ' cells</strong> through the full agent harness. ' +
            (opts.mins > 0 ? 'Estimated time: <strong>' + opts.mins + ' min</strong>.' : '') +
          '</div>' +
          warnHtml +
          '<div style="font-size:11px;color:var(--muted);font-weight:600;margin:12px 0 4px;text-transform:uppercase;">Models</div>' +
          '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">' + modelChips + '</div>' +
          '<div style="font-size:11px;color:var(--muted);font-weight:600;margin:12px 0 4px;text-transform:uppercase;">Profiles</div>' +
          '<div style="display:flex;flex-wrap:wrap;gap:6px;">' + profileChips + '</div>' +
        '</div>' +
        '<div class="modal-header" style="border-top:1px solid var(--border);border-bottom:none;justify-content:flex-end;gap:8px;">' +
          '<button class="btn" id="gridConfirmCancel" style="padding:8px 16px;border-radius:6px;font-size:12px;cursor:pointer;">Cancel</button>' +
          '<button class="btn btn-primary" id="gridConfirmRun" style="padding:8px 16px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">Run ' + opts.cells + ' cells</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    function close() { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }
    overlay.querySelector('#gridConfirmClose').onclick = close;
    overlay.querySelector('#gridConfirmCancel').onclick = close;
    overlay.querySelector('#gridConfirmRun').onclick = function() {
      close();
      opts.onRun();
    };
    // Click on scrim (outside modal) closes
    overlay.onclick = function(e) { if (e.target === overlay) close(); };
  }

  // ── Actually start the grid run ──
  function startGridRun(agent, selectedModels, selectedProfiles, judge) {
    var url = '/api/capability/grid/run?agent=' + encodeURIComponent(agent);
    if (selectedModels.length > 0) {
      url += '&models=' + encodeURIComponent(selectedModels.join(','));
    }
    if (selectedProfiles.length > 0) {
      url += '&configs=' + encodeURIComponent(selectedProfiles.join(','));
    }
    if (judge) {
      url += '&judge=' + encodeURIComponent(judge);
    }

    // ── Immediate hourglass transition ──
    // Replace the grid area with a "starting…" spinner the instant Run is
    // clicked so there is zero dead time while the POST + subprocess boot
    // happens. The running view (progress bar) replaces it as soon as the
    // subprocess has created the run row.
    var container = document.getElementById('gridTableContainer');
    if (container) {
      container.innerHTML =
        '<div class="cap-empty" style="border:1px solid var(--border);">' +
          '<div class="cap-empty-icon" style="font-size:32px;"><span class="spinner" style="width:18px;height:18px;display:inline-block;vertical-align:middle;"></span></div>' +
          '<h2>Starting comparison…</h2>' +
          '<p style="color:var(--fg-3);font-size:12px;">Spinning up the grid runner — this takes a few seconds.</p>' +
        '</div>';
    }

    return fetch(url, {method:'POST', headers:_authHeaders()})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          showToast('Comparison started for ' + agent);
          // Fetch the running view aggressively (1s retry). The server returns
          // the progress-bar view as soon as the run row exists; until then the
          // spinner stays. Once the running view is in place its own
          // hx-trigger="every 10s" takes over for live cell updates.
          (function fetchRunningView(attempts) {
            fetch('/api/capability/grid/table?agent=' + encodeURIComponent(agent), {headers:_authHeaders()})
              .then(function(r) { return r.text(); })
              .then(function(html) {
                var el = document.getElementById('gridTableContainer');
                if (!el) return;
                if (html.indexOf('grid-running') !== -1 || html.indexOf('Grid Run In Progress') !== -1) {
                  el.innerHTML = html;
                  return; // running view live — its own polling continues
                }
                if (attempts < 20) {
                  setTimeout(function() { fetchRunningView(attempts + 1); }, 1000);
                } else {
                  el.innerHTML = html; // give up — show whatever the server reports
                }
              })
              .catch(function() {
                if (attempts < 20) setTimeout(function() { fetchRunningView(attempts + 1); }, 1000);
              });
          })(0);

          // Keep the original completion poll — after cells finish, refresh once.
          var poll = setInterval(function() {
            fetch('/api/capability/grid?agent=' + encodeURIComponent(agent), {headers:_authHeaders()})
              .then(function(r) { return r.json(); })
              .then(function(g) {
                if (g.cells && g.cells.length > 0) {
                  clearInterval(poll);
                  showToast('Comparison complete — refreshing');
                  htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent(agent), {target: '#gridTableContainer', swap: 'innerHTML'});
                }
              });
          }, 10000);
        } else {
          // Start failed — restore the table view instead of leaving the spinner.
          htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent(agent), {target: '#gridTableContainer', swap: 'innerHTML'});
        }
      })
      .catch(function(e) {
        showToast('Comparison failed: ' + e.message);
        htmx.ajax('GET', '/api/capability/grid/table?agent=' + encodeURIComponent(agent), {target: '#gridTableContainer', swap: 'innerHTML'});
      });
  };

  // ── Live selection counts ──
  window.updateGridCounts = function() {
    var m = document.querySelectorAll('#gridModels .grid-model-cb:checked').length;
    var mc = document.getElementById('gridModelCount');
    if (mc) mc.textContent = m + ' selected';
    var p = document.querySelectorAll('#gridProfiles .grid-profile-cb:checked').length;
    var pc = document.getElementById('gridProfileCount');
    if (pc) pc.textContent = p + ' selected';
  };

  // ── Dynamic grid options loader ──
  // Populates the model/profile checkbox lists client-side from /grid/options
  // so model availability is always current (new providers/models in hermes
  // config appear without a server re-render).
  window.loadGridOptions = function() {
    var mList = document.getElementById('gridModels');
    var pList = document.getElementById('gridProfiles');
    if (!mList || !pList) return;
    fetch('/api/capability/grid/options', {headers:_authHeaders()})
      .then(function(r){ return r.json(); })
      .then(function(opts){
        var defaults = opts.default_models || [];
        var defaultSet = {};
        defaults.forEach(function(d){ defaultSet[d] = true; });

        // Models grouped by provider
        var mHtml = '';
        (opts.model_groups || []).forEach(function(g){
          if (!g.models || !g.models.length) return;
          mHtml += '<div style="margin-bottom:4px;">';
          mHtml += '<div style="font-size:10px;color:var(--muted);font-weight:600;padding:2px 4px;">' +
                   (g.provider || '').toUpperCase() + '</div>';
          g.models.forEach(function(m){
            var checked = defaultSet[m.spec] ? 'checked' : '';
            mHtml += '<label class="grid-check" style="display:flex;align-items:center;gap:6px;' +
                     'padding:3px 4px;border-radius:4px;cursor:pointer;font-size:12px;color:var(--fg);">' +
                     '<input type="checkbox" class="grid-model-cb" value="' + esc(m.spec) + '" ' + checked +
                     ' onchange="updateGridCounts()">' + esc(m.name) + '</label>';
          });
          mHtml += '</div>';
        });
        mList.innerHTML = mHtml || '<div style="color:var(--muted);font-size:12px;padding:4px;">No cloud models configured</div>';

        // Profiles
        var pHtml = '';
        (opts.profiles || []).forEach(function(p){
          var checked = defaultSet[p] || opts.profiles.indexOf(p) < 3 ? 'checked' : '';
          pHtml += '<label class="grid-check" style="display:flex;align-items:center;gap:6px;' +
                   'padding:3px 4px;border-radius:4px;cursor:pointer;font-size:12px;color:var(--fg);">' +
                   '<input type="checkbox" class="grid-profile-cb" value="' + esc(p) + '" ' + checked +
                   ' onchange="updateGridCounts()">' + esc(p) + '</label>';
        });
        pList.innerHTML = pHtml || '<div style="color:var(--muted);font-size:12px;padding:4px;">No profiles found</div>';

        // Judge select
        var judgeSel = document.getElementById('gridJudge');
        if (judgeSel) {
          var curJudge = judgeSel.value || opts.default_judge || 'ollama-cloud/glm-5.2';
          var jHtml = '';
          (opts.judge_options || []).forEach(function(j){
            var sel = (j.spec === curJudge) ? 'selected' : '';
            jHtml += '<option value="' + esc(j.spec) + '" ' + sel + '>' + esc(j.spec) + '</option>';
          });
          if (jHtml) judgeSel.innerHTML = jHtml;
        }

        // Agent select (all agents with grid data, keep current selection)
        var agentSel = document.getElementById('gridAgent');
        if (agentSel) {
          var curAgent = agentSel.value || 'main';
          var aHtml = '';
          (opts.agent_options || []).forEach(function(a){
            var sel = (a === curAgent) ? 'selected' : '';
            aHtml += '<option value="' + esc(a) + '" ' + sel + '>' + esc(a) + '</option>';
          });
          if (aHtml) agentSel.innerHTML = aHtml;
        }

        // Run history selector
        var runSel = document.getElementById('gridRunSelect');
        if (runSel) {
          var rHtml = '<option value="">Current</option>';
          (opts.run_history || []).forEach(function(r){
            var label = r.started_at + ' · ' + r.agent + ' · ' + r.status + ' · ' + r.cells + ' cells' +
                        (r.judge ? ' · judge=' + r.judge : '');
            rHtml += '<option value="' + esc(r.id) + '">' + esc(label) + '</option>';
          });
          runSel.innerHTML = rHtml;
        }

        updateGridCounts();
      })
      .catch(function(){
        mList.innerHTML = '<div style="color:var(--danger);font-size:12px;padding:4px;">Failed to load models</div>';
        pList.innerHTML = '<div style="color:var(--danger);font-size:12px;padding:4px;">Failed to load profiles</div>';
      });
  };

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Load a specific historical run (run selector) ──
  window.loadGridRun = function(runId) {
    var agent = _getCapAgent();
    var t = new URLSearchParams(location.search).get('token') || '';
    var url = '/api/capability/grid/table?agent=' + encodeURIComponent(agent) +
              (runId ? '&run_id=' + encodeURIComponent(runId) : '');
    if (t) url += '&token=' + t;
    htmx.ajax('GET', url, {target: '#gridTableContainer', swap: 'innerHTML'});
  };

  // Initialize on load + after grid table swaps
  document.addEventListener('DOMContentLoaded', function() { loadGridOptions(); });
  document.body.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target && e.detail.target.id && e.detail.target.id.indexOf('grid') !== -1) {
      loadGridOptions();
    }
  });

  // ── Toast ──
  window.showToast = function(msg) {
    var existing = document.getElementById('capToast');
    if (existing) existing.remove();
    var t = document.createElement('div');
    t.id = 'capToast';
    t.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 16px;color:#f8fafc;font-size:13px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function() { t.remove(); }, 5000);
  };

  // ── Per-agent canary runner (from task list) ──
  window.runCanaryForAgent = function(agent) {
    fetch('/api/capability/canary/run?agent=' + encodeURIComponent(agent), {method:'POST', headers: _authHeaders()})
      .then(function(r) { return r.json(); })
      .then(function(d) { if (d.ok) showToast('Benchmark started for ' + agent); });
  };

  // ── Task management ──
  window.showNewTaskForm = function() { showToast('Task editor coming soon'); };
  window.editTask = function(id) { showToast('Task editor coming soon'); };

  window.showTaskTab = function(tab) {
    var activeBtn = document.getElementById('taskTabActive');
    var pendingBtn = document.getElementById('taskTabPending');
    var activeEl = document.getElementById('taskListContainer');
    var pendingEl = document.getElementById('pendingListContainer');
    if (tab === 'pending') {
      activeEl.style.display = 'none';
      pendingEl.style.display = 'block';
      activeBtn.classList.remove('cap-btn-active');
      pendingBtn.classList.add('cap-btn-active');
      htmx.ajax('GET', '/api/capability/pending-tasks/html', {target: '#pendingListContainer', swap: 'innerHTML'});
    } else {
      activeEl.style.display = 'block';
      pendingEl.style.display = 'none';
      pendingBtn.classList.remove('cap-btn-active');
      activeBtn.classList.add('cap-btn-active');
    }
  };

  window.approveDraft = function(id) {
    fetch('/api/capability/canary/pending-tasks/approve', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task_id: id})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('✓ Approved — now active in canary');
        htmx.ajax('GET', '/api/capability/pending-tasks/html', {target: '#pendingListContainer', swap: 'innerHTML'});
      } else {
        showToast('Approve failed: ' + (d.error || 'unknown'));
      }
    })
    .catch(function(e) { showToast('Approve failed: ' + e.message); });
  };

  window.rejectDraft = function(id) {
    if (!confirm('Reject this draft? It will be deleted.')) return;
    fetch('/api/capability/canary/pending-tasks/reject', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task_id: id})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('Draft rejected');
        htmx.ajax('GET', '/api/capability/pending-tasks/html', {target: '#pendingListContainer', swap: 'innerHTML'});
      } else {
        showToast('Reject failed: ' + (d.error || 'unknown'));
      }
    })
    .catch(function(e) { showToast('Reject failed: ' + e.message); });
  };

  window.viewSourceSession = function(sessionId) {
    if (!sessionId) { showToast('No source session linked'); return; }
    var modal = document.getElementById('sourceSessionModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'sourceSessionModal';
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9998;display:flex;align-items:center;justify-content:center;';
      modal.innerHTML = '<div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;max-width:640px;width:90%;max-height:80vh;overflow:auto;padding:20px;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        + '<h3 style="margin:0;font-size:15px;color:var(--fg);">Original Conversation</h3>'
        + '<button onclick="closeSourceModal()" style="background:none;border:none;color:var(--fg-3);font-size:20px;cursor:pointer;">✕</button>'
        + '</div>'
        + '<div id="sourceSessionBody"><div class="spinner"></div> Loading...</div>'
        + '</div>';
      document.body.appendChild(modal);
    }
    var body = document.getElementById('sourceSessionBody');
    body.innerHTML = '<div class="spinner"></div> Loading...';
    fetch('/api/capability/canary/source-session?session_id=' + encodeURIComponent(sessionId))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) {
          body.innerHTML = '<p style="color:var(--danger);">' + (d.error || 'Failed to load') + '</p>';
          return;
        }
        if (d.deleted) {
          body.innerHTML = '<p style="color:var(--warn);">Original conversation no longer available (session deleted).</p>';
          return;
        }
        if (!d.messages || d.messages.length === 0) {
          body.innerHTML = '<p style="color:var(--fg-3);">No messages found for this session.</p>';
          return;
        }
        var html = '';
        for (var i = 0; i < d.messages.length; i++) {
          var m = d.messages[i];
          var roleColor = m.role === 'user' ? 'var(--accent)' : 'var(--success)';
          var roleLabel = m.role === 'user' ? '👤 User' : '🤖 Agent';
          html += '<div style="margin-bottom:8px;padding:8px 12px;border-radius:6px;background:' + (m.role === 'user' ? 'var(--accent)08' : 'var(--success)08') + ';border-left:3px solid ' + roleColor + ';">'
            + '<div style="font-size:11px;color:' + roleColor + ';margin-bottom:4px;">' + roleLabel + '</div>'
            + '<div style="font-size:13px;color:var(--fg);white-space:pre-wrap;word-break:break-word;">' + (m.content || '') + '</div>'
            + '</div>';
        }
        body.innerHTML = html;
      })
      .catch(function(e) { body.innerHTML = '<p style="color:var(--danger);">Failed to load: ' + e.message + '</p>'; });
  };

  // ── Per-task drift filter ──
  window.filterPerTaskDrift = function(taskId) {
    var agent = _getCapAgent();
    htmx.ajax('GET', '/api/capability/drift/per-task-history?agent=' + encodeURIComponent(agent) + '&task_id=' + encodeURIComponent(taskId), {target: '#driftChartContainer', swap: 'innerHTML'});
  };

  // ── Approve all pending drafts ──
  window.approveAllDrafts = function() {
    var checkboxes = document.querySelectorAll('#pendingListContainer input[type="checkbox"]:checked');
    var ids = [];
    checkboxes.forEach(function(cb) { ids.push(cb.value); });
    if (ids.length === 0) { showToast('Select at least one draft to approve'); return; }
    fetch('/api/capability/canary/pending-tasks/approve-batch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task_ids: ids})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('✓ Approved ' + ids.length + ' draft(s)');
        htmx.ajax('GET', '/api/capability/pending-tasks/html', {target: '#pendingListContainer', swap: 'innerHTML'});
      } else {
        showToast('Batch approve failed: ' + (d.error || 'unknown'));
      }
    })
    .catch(function(e) { showToast('Batch approve failed: ' + e.message); });
  };

  // ── Mine conversations for new tasks ──
  window.mineConversations = function() {
    var btn = document.getElementById('mineBtn');
    if (btn) { btn.textContent = '⏳ Mining…'; btn.disabled = true; }
    fetch('/api/capability/canary/pending-tasks/mine', {method: 'POST'})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (btn) { btn.textContent = '⛏ Mine Conversations'; btn.disabled = false; }
        if (d.ok) {
          showToast('Mined ' + (d.count || 0) + ' new draft(s)');
          htmx.ajax('GET', '/api/capability/pending-tasks/html', {target: '#pendingListContainer', swap: 'innerHTML'});
        } else {
          showToast('Mining failed: ' + (d.error || 'unknown'));
        }
      })
      .catch(function(e) {
        if (btn) { btn.textContent = '⛏ Mine Conversations'; btn.disabled = false; }
        showToast('Mining failed: ' + e.message);
      });
  };

  // ── Per-task drift chart ──────────────────────────────────────────
  var _perTaskChart = null;
  var _perTaskAllTasks = [];
  var _perTaskActiveCat = 'all';

  var _perTaskCatColors = {
    reasoning: '#3b82f6',
    coding: '#22c55e',
    extraction: '#a855f7',
    tool_use: '#eab308',
    instruction_following: '#14b8a6'
  };

  function _perTaskColor(task) {
    if (task.severity === 'breach') return '#ef4444';
    if (task.severity === 'warning') return '#eab308';
    return _perTaskCatColors[task.category] || '#64748b';
  }

  function _getCapAgent() {
    var el = document.getElementById('capAgentName');
    return el ? el.getAttribute('data-agent') || 'default' : 'default';
  }

  // Auto-fetch per-task data on load
  (function() {
    fetchPerTaskData();
  })();

  async function fetchPerTaskData() {
    try {
      var agent = _getCapAgent();
      var resp = await fetch('/api/capability/drift/per-task-history?agent=' + encodeURIComponent(agent), {headers: _authHeaders()});
      var data = await resp.json();
      _perTaskAllTasks = data.tasks || [];
      if (_perTaskAllTasks.length === 0) {
        var body = document.getElementById('taskBreakdownBody');
        if (body) body.innerHTML = '<div style="text-align:center;padding:32px;color:var(--fg-3);font-size:13px;">📋 Run a benchmark to see per-task breakdown</div>';
      } else {
        renderPerTaskDriftChart();
      }
    } catch(e) { console.error('per-task drift fetch failed', e); }
  }

  function renderPerTaskDriftChart() {
    if (typeof Chart === 'undefined') return;
    var ctx = document.getElementById('perTaskDriftChart');
    if (!ctx) return;

    var filtered = _perTaskAllTasks;
    if (_perTaskActiveCat !== 'all') {
      filtered = _perTaskAllTasks.filter(function(t) { return t.category === _perTaskActiveCat; });
    }

    if (filtered.length === 0) {
      var legendEl = document.getElementById('perTaskLegend');
      if (legendEl) legendEl.innerHTML = '<span style="font-size:12px;color:var(--muted);">No tasks in this category yet. Run a benchmark to populate.</span>';
      return;
    }

    var dateSet = {};
    filtered.forEach(function(t) {
      t.points.forEach(function(p) { dateSet[p.date] = true; });
    });
    var labels = Object.keys(dateSet).sort();

    var datasets = filtered.map(function(t) {
      var accMap = {};
      t.points.forEach(function(p) { accMap[p.date] = p.accuracy; });
      var data = labels.map(function(d) { return accMap[d] !== undefined ? accMap[d] : null; });
      var color = _perTaskColor(t);
      return {
        label: t.name,
        data: data,
        borderColor: color,
        backgroundColor: color,
        borderWidth: t.severity === 'stable' ? 1.5 : 2.5,
        pointRadius: t.severity === 'stable' ? 2 : 4,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        fill: false,
        tension: 0.3,
        spanGaps: false,
        taskId: t.task_id,
        taskName: t.name,
        baseline: t.baseline,
        current: t.current,
        delta: t.delta,
        severity: t.severity,
        category: t.category
      };
    });

    if (_perTaskChart) { _perTaskChart.destroy(); _perTaskChart = null; }

    _perTaskChart = new Chart(ctx, {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: true },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(30,41,59,.95)',
            titleColor: '#f8fafc',
            bodyColor: '#94a3b8',
            borderColor: '#334155',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              title: function(ctx) {
                return ctx[0].dataset.taskName || ctx[0].dataset.label || '';
              },
              label: function(ctx) {
                var ds = ctx.dataset;
                var lines = [];
                lines.push('Accuracy: ' + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) + '%' : 'N/A'));
                lines.push('Baseline: ' + (ds.baseline != null ? ds.baseline.toFixed(1) + '%' : '—'));
                lines.push('Current:  ' + (ds.current != null ? ds.current.toFixed(1) + '%' : '—'));
                var dsgn = ds.delta >= 0 ? '+' : '';
                lines.push('Change: ' + dsgn + (ds.delta != null ? ds.delta.toFixed(1) + 'pp' : '—') + ' · ' + (ds.severity || 'stable'));
                return lines;
              }
            }
          }
        },
        onClick: function(e, elements) {
          if (elements.length > 0) {
            var ds = _perTaskChart.data.datasets[elements[0].datasetIndex];
            showPerTaskDetail(ds.taskId, ds.taskName, ds.baseline, ds.current, ds.delta, ds.severity);
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#64748b', font: { size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 14 }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: 'rgba(51,65,85,.2)' },
            ticks: { color: '#94a3b8', font: { size: 9 }, callback: function(v) { return v + '%'; } }
          }
        }
      }
    });

    renderPerTaskLegend(filtered);
  }

  function renderPerTaskLegend(tasks) {
    var el = document.getElementById('perTaskLegend');
    if (!el) return;
    var h = '';
    tasks.forEach(function(t, i) {
      var c = _perTaskColor(t);
      var tag = '';
      if (t.severity === 'breach') {
        tag = ' <span style="font-size:9px;padding:0 4px;border-radius:3px;background:rgba(239,68,68,.2);color:#ef4444;">BREACH</span>';
      } else if (t.severity === 'warning') {
        tag = ' <span style="font-size:9px;padding:0 4px;border-radius:3px;background:rgba(234,179,8,.2);color:#eab308;">WARNING</span>';
      }
      h += '<span style="display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--fg-2);cursor:pointer;padding:2px 0;" onclick="(function(){var m=_perTaskChart.getDatasetMeta(' + i + ');m.hidden=!m.hidden;_perTaskChart.update();})()">' +
        '<span style="width:8px;height:8px;border-radius:50%;background:' + c + ';display:inline-block;flex-shrink:0;"></span>' +
        t.name + tag + '</span>';
    });
    el.innerHTML = h;
  }

  // Keep togglePerTaskDrift for backward compat
  window.togglePerTaskDrift = function() {};

  window.filterPerTaskDrift = function(cat) {
    _perTaskActiveCat = cat;
    document.querySelectorAll('.per-task-chip').forEach(function(c) {
      var active = c.dataset.cat === cat;
      c.style.background = active ? 'var(--meta)' : 'transparent';
      c.style.color = active ? '#fff' : 'var(--fg-2)';
      c.style.borderColor = active ? 'var(--meta)' : 'var(--border)';
    });
    renderPerTaskDriftChart();
  };

  window.showPerTaskDetail = function(taskId, name, baseline, current, delta, severity) {
    var panel = document.getElementById('perTaskDetail');
    var nameEl = document.getElementById('perTaskDetailName');
    var gridEl = document.getElementById('perTaskDetailGrid');
    var reasonEl = document.getElementById('perTaskDetailReasoningText');
    if (!panel || !nameEl || !gridEl || !reasonEl) return;

    var deltaColor = delta < 0 ? '#ef4444' : delta > 0 ? 'var(--accent)' : 'var(--muted)';
    var dsgn = delta >= 0 ? '+' : '';

    nameEl.textContent = name;
    nameEl.style.color = severity === 'breach' ? '#ef4444' : severity === 'warning' ? '#eab308' : 'var(--fg)';
    gridEl.innerHTML =
      '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:var(--accent);">' + (baseline != null ? baseline.toFixed(1) + '%' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Baseline</div></div>' +
      '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:' + (delta < 0 ? '#ef4444' : 'var(--accent)') + ';">' + (current != null ? current.toFixed(1) + '%' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Current</div></div>' +
      '<div style="text-align:center;"><div style="font-size:20px;font-weight:700;color:' + deltaColor + ';">' + dsgn + (delta != null ? delta.toFixed(1) + 'pp' : '—') + '</div><div style="font-size:10px;color:var(--muted);margin-top:2px;">Change</div></div>';
    reasonEl.innerHTML = 'Loading judge reasoning...';
    panel.style.display = 'block';

    fetch('/api/capability/canary/judge-reasoning?task_id=' + encodeURIComponent(taskId))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var assertions = data.assertions || [];
        if (assertions.length === 0) {
          reasonEl.innerHTML = '<span style="color:var(--muted);">No LLM judge reasoning available for this task.</span>';
          return;
        }
        var h = '';
        assertions.forEach(function(a) {
          var sc = a.status === 'pass' ? 'var(--accent)' : a.status === 'fail' ? 'var(--danger)' : 'var(--muted)';
          h += '<div style="margin-bottom:8px;"><span style="color:' + sc + ';font-weight:600;">' + (a.status || '?').toUpperCase() + '</span> ' +
            '<span style="color:var(--fg-2);">Score: ' + (a.score != null ? (a.score * 100).toFixed(0) + '%' : '—') + '</span></div>' +
            '<div style="color:var(--muted);margin-bottom:12px;">' + (a.reasoning || 'No reasoning provided.') + '</div>';
        });
        reasonEl.innerHTML = h || '<span style="color:var(--muted);">No judge data available.</span>';
      })
      .catch(function() {
        reasonEl.innerHTML = '<span style="color:var(--muted);">Failed to load judge reasoning.</span>';
      });
  };

  window.closePerTaskDetail = function() {
    var panel = document.getElementById('perTaskDetail');
    if (panel) panel.style.display = 'none';
  };

  // ── Overview card: load canary status ──
  (function loadCapOverview() {
    var agent = _getCapAgent();
    fetch('/api/capability/canary/status?agent=' + encodeURIComponent(agent), {headers: _authHeaders()})
      .then(function(r) { return r.json(); })
      .then(function(s) {
        var lastEl = document.getElementById('capOvLastTested');
        var statsEl = document.getElementById('capOvStats');
        var accEl = document.getElementById('capOvBigAcc');
        var accLabel = document.getElementById('capOvAccLabel');
        var untestedEl = document.getElementById('capUntested');
        var overviewCard = document.getElementById('capOverviewCard');
        var perfSection = document.getElementById('perfTrendSection');

        if (!s.completed && !s.running) {
          if (overviewCard) overviewCard.style.display = 'none';
          if (untestedEl) untestedEl.style.display = 'block';
          if (perfSection) perfSection.style.display = 'none';
          if (lastEl) lastEl.textContent = 'Not tested yet';
          if (accEl) { accEl.textContent = '—%'; accEl.className = 'cap-ov-big-accuracy muted'; }
          if (accLabel) accLabel.innerHTML = '<strong>No benchmark data yet</strong><br>Run a test to establish a baseline';
        } else if (s.running) {
          if (overviewCard) overviewCard.style.display = 'grid';
          if (untestedEl) untestedEl.style.display = 'none';
          if (lastEl) lastEl.textContent = '⏳ Benchmark running…';
          if (accEl) { accEl.textContent = '...'; accEl.className = 'cap-ov-big-accuracy muted'; }
        } else {
          if (overviewCard) overviewCard.style.display = 'grid';
          if (untestedEl) untestedEl.style.display = 'none';
          var pass = s.pass_count || 0;
          var fail = s.fail_count || 0;
          var hang = s.hang_count || 0;
          var total = s.total_tasks || (pass + fail + hang);
          var accuracy = total > 0 ? Math.round((pass / total) * 100) : 0;

          var accClass = accuracy >= 80 ? 'green' : accuracy >= 60 ? 'amber' : 'red';
          if (accEl) {
            accEl.textContent = accuracy + '%';
            accEl.className = 'cap-ov-big-accuracy ' + accClass;
          }
          if (accLabel) {
            var desc = accuracy >= 80 ? 'Good performance' : accuracy >= 60 ? 'Needs attention' : 'Significant issues';
            accLabel.innerHTML = '<strong>' + desc + '</strong><br>' + pass + '/' + total + ' tasks passed';
          }
          if (lastEl && s.run_id) {
            lastEl.textContent = 'Last test results available — hover chart for details';
          }
          if (statsEl) {
            statsEl.innerHTML =
              '<div class="cap-ov-stat"><div class="val green">' + pass + '</div><div class="lbl">Passed</div></div>' +
              '<div class="cap-ov-stat"><div class="val ' + (fail > 0 ? 'red' : 'muted') + '">' + fail + '</div><div class="lbl">Failed</div></div>' +
              '<div class="cap-ov-stat"><div class="val muted">' + total + '</div><div class="lbl">Total</div></div>';
          }
          if (perfSection) perfSection.style.display = 'block';
        }
      })
      .catch(function() {
        var lastEl = document.getElementById('capOvLastTested');
        if (lastEl) lastEl.textContent = '⚠ Could not load status';
      });
  })();

  // ── Task management helpers ──
  window.deleteTask = function(id) {
    if (!confirm('Delete this task?')) return;
    fetch('/api/capability/tasks/' + id, {method:'DELETE'})
      .then(function() { htmx.ajax('GET', '/api/capability/tasks/list', {target: '#taskListContainer', swap: 'innerHTML'}); });
  };
  window.duplicateTask = function(id) { showToast('Duplicate coming soon'); };
  window.switchEditorMode = function(id, mode) {};
  window.saveYamlTask = function(id) { showToast('Save coming soon'); };
  window.saveFormTask = function(id) { showToast('Save coming soon'); };
  window.closeEditor = function(id) {};
  window.shareDriftView = function() { showToast('Share coming soon'); };

  // ── HTML escape helper ──
  window._escHtml = function(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  };

})();
