// ── Pathway Map — standalone Cytoscape graph (loaded via htmx swap) ──
// Auto-initializes when #cy element appears in the DOM.

(function() {
  'use strict';
  try {

  var cy = null;
  var graphData = { nodes: [], edges: [] };
  var shortcutActive = false;
  var currentViewFilter = null;

  var NODE_STYLES = {
    agent:      { icon: '🧠', color: '#6366f1', shape: 'round-rectangle' },
    cron:       { icon: '⏰', color: '#f59e0b', shape: 'round-rectangle' },
    platform:   { icon: '📱', color: '#06b6d4', shape: 'round-rectangle' },
    consumer:   { icon: '📖', color: '#14b8a6', shape: 'ellipse' },
    router:     { icon: '🔀', color: '#3b82f6', shape: 'round-rectangle' },
    daemon:     { icon: '⚙️', color: '#8b5cf6', shape: 'round-rectangle' },
    watcher:    { icon: '👁️', color: '#ec4899', shape: 'ellipse' },
    gateway:    { icon: '🚪', color: '#10b981', shape: 'round-rectangle' },
    service:    { icon: '📡', color: '#f97316', shape: 'round-rectangle' },
    mesh:       { icon: '🔗', color: '#06b6d4', shape: 'ellipse' },
    filesystem: { icon: '💾', color: '#64748b', shape: 'ellipse' },
  };

  var EDGE_COLORS = { green: '#22c55e', yellow: '#eab308', red: '#ef4444', teal: '#14b8a6', unknown: '#64748b' };

  function nodeStyle(nodeType) {
    return NODE_STYLES[nodeType] || { icon: '❓', color: '#6b7280', shape: 'round-rectangle' };
  }

  function buildCytoscapeElements() {
    var elements = [];
    var ns = graphData.nodes || [];
    var es = graphData.edges || [];
    var nodeMap = {};
    ns.forEach(function(n) { nodeMap[n.id] = n; });

    ns.forEach(function(n) {
      var style = nodeStyle(n.type);
      elements.push({
        group: 'nodes',
        data: {
          id: n.id, label: n.name, type: n.type, icon: style.icon,
          confidence: n.confidence || 50, source: n.source || 'manual',
          framework: n.framework || '', nodeColor: style.color,
          shape: style.shape, raw: n
        }
      });
    });

    var edgeBundle = {};
    es.forEach(function(e) {
      var targetId = e.target_id;
      if (!targetId) {
        var stubId = '__dead__' + e.source_id;
        if (!nodeMap[stubId]) {
          elements.push({
            group: 'nodes', data: {
              id: stubId, label: '∅', type: 'dead-end', icon: '✕',
              nodeColor: '#ef4444', shape: 'ellipse',
              raw: { id: stubId, name: '∅ Dead End', type: 'dead-end' }
            }, classes: 'dead-end-node'
          });
          nodeMap[stubId] = { id: stubId };
        }
        elements.push({
          group: 'edges', data: {
            id: e.id || ('edge-' + e.source_id + '-dead'),
            source: e.source_id, target: stubId, status: 'red',
            label: 'Dead End', mechanism: e.mechanism || '',
            confidence: e.confidence || 50, scenario: e.scenario || '',
            metadata: e.metadata || '{}', raw: e, bundleCount: 1
          }, classes: 'edge-red'
        });
      } else {
        var key = e.source_id + '→' + targetId;
        if (!edgeBundle[key]) edgeBundle[key] = [];
        edgeBundle[key].push(e);
      }
    });

    Object.keys(edgeBundle).forEach(function(key) {
      var edges = edgeBundle[key];
      var first = edges[0];
      var count = edges.length;
      var statusOrder = { red: 3, yellow: 2, green: 1, teal: 1, unknown: 0 };
      var useStatus = first.status || 'unknown';
      edges.forEach(function(e) {
        if ((statusOrder[e.status] || 0) > (statusOrder[useStatus] || 0)) useStatus = e.status;
      });
      var width = Math.min(2 + (count * 0.5), 6);
      var deliverLabel = '';
      try { var m = JSON.parse(first.metadata || '{}'); if (m.deliver && m.deliver !== 'local' && m.deliver !== 'origin') { deliverLabel = m.deliver.replace('telegram:-1003985609979:', '📱T').replace('telegram:', '📱'); } } catch(e) {}
      var edgeLabel = count > 1 ? ('×' + count + (deliverLabel ? ' ' + deliverLabel : '')) : deliverLabel;
      elements.push({
        group: 'edges', data: {
          id: first.id || ('edge-' + first.source_id + '-' + first.target_id),
          source: first.source_id, target: first.target_id, status: useStatus,
          label: edgeLabel, mechanism: first.mechanism || '',
          confidence: first.confidence || 50, scenario: first.scenario || '',
          metadata: first.metadata || '{}', raw: first, bundleCount: count, deliverLabel: deliverLabel
        }, classes: 'edge-' + useStatus
      });
    });

    return elements;
  }

  function getLayoutConfig(overrides) {
    var base = {
      name: 'dagre', rankDir: 'LR', spacingFactor: 1.05,
      nodeSep: 24, rankSep: 50, fit: true, padding: 20,
      animate: true, animationDuration: 300
    };
    if (overrides) Object.keys(overrides).forEach(function(k) { base[k] = overrides[k]; });
    return base;
  }

  function updateSummary() {
    var es = graphData.edges || [];
    var green = 0, yellow = 0, red = 0;
    es.forEach(function(e) {
      if (e.status === 'green') green++;
      else if (e.status === 'yellow') yellow++;
      else if (e.status === 'red') red++;
    });
    var el = document.getElementById('total-nodes');
    if (el) el.textContent = (graphData.nodes || []).length;
    el = document.getElementById('total-green');
    if (el) el.textContent = green;
    el = document.getElementById('total-yellow');
    if (el) el.textContent = yellow;
    el = document.getElementById('total-red');
    if (el) el.textContent = red;
  }

  function updateFilterStatus() {
    if (!cy) return;
    var totalNodes = graphData.nodes ? graphData.nodes.length : 0;
    var totalEdges = graphData.edges ? graphData.edges.length : 0;
    var visibleNodes = cy.nodes(':visible').filter(function(n) { return n.data('type') !== 'dead-end' && n.data('type') !== 'filesystem'; }).length;
    var visibleEdges = cy.edges(':visible').length;
    var statusBar = document.getElementById('filter-status-bar');
    if (!statusBar) return;
    var isActive = shortcutActive;
    statusBar.style.display = isActive ? 'block' : 'none';
    if (!isActive) return;
    var showingEl = document.getElementById('filter-showing');
    var totalEl = document.getElementById('filter-total');
    var edgesVisibleEl = document.getElementById('filter-edges-visible');
    var edgesTotalEl = document.getElementById('filter-edges-total');
    if (showingEl) showingEl.textContent = visibleNodes;
    if (totalEl) totalEl.textContent = totalNodes;
    if (edgesVisibleEl) edgesVisibleEl.textContent = visibleEdges;
    if (edgesTotalEl) edgesTotalEl.textContent = totalEdges;
  }

  function showEmptyDetail() {
    var panel = document.getElementById('detail-body');
    if (panel) panel.innerHTML = '<div class="detail-empty" style="color:var(--muted);font-size:12px;text-align:center;padding:30px 10px;">Click a node or edge to see details</div>';
  }

  function showNodeDetail(node) {
    var d = node.data();
    var raw = d.raw || {};
    var panel = document.getElementById('detail-body');
    if (!panel) return;
    var style = nodeStyle(d.type);
    var color = d.nodeColor || style.color;
    var connectionsHtml = '';
    var connected = node.connectedEdges();
    if (connected.length > 0) {
      connectionsHtml = '<div class="detail-section" style="margin-top:10px;"><div class="detail-section-title" style="font-size:12px;font-weight:600;color:var(--fg-2);margin-bottom:6px;">Connections</div>';
      connected.forEach(function(edge) {
        var isSource = edge.source().id() === node.id();
        var other = isSource ? edge.target() : edge.source();
        var arrow = isSource ? '→' : '←';
        var status = edge.data('status') || 'unknown';
        var icon = {green:'🟢',yellow:'🟡',red:'🔴',teal:'🔵'}[status] || '⚪';
        connectionsHtml += '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.3);cursor:pointer;" onclick="window.__pathwayShowEdge(\'' + edge.id() + '\')">' +
          '<span class="detail-label" style="color:var(--muted);">' + icon + ' ' + (other.data('label') || '∅') + '</span>' +
          '<span class="detail-value" style="color:var(--fg);font-weight:500;">' + arrow + ' ' + status + '</span></div>';
      });
      connectionsHtml += '</div>';
    }
    panel.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">' +
      '<span style="font-size:24px;">' + d.icon + '</span>' +
      '<div><div style="font-size:15px;font-weight:600;">' + d.label + '</div>' +
      '<span class="detail-tag" style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:' + color + '22;color:' + color + ';">' + d.type + '</span></div></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Node ID</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.id + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Type</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.type + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Source</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.source + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Confidence</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.confidence + '%</span></div>' +
      (d.framework ? '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Framework</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.framework + '</span></div>' : '') +
      connectionsHtml;
  }

  function showEdgeDetail(edge) {
    var d = edge.data();
    var panel = document.getElementById('detail-body');
    if (!panel) return;
    var status = d.status || 'unknown';
    var statusIcon = {green:'🟢',yellow:'🟡',red:'🔴',teal:'🔵'}[status] || '⚪';
    var sourceLabel = edge.source().data('label') || '?';
    var targetLabel = d.status === 'red' && !edge.target().data('label') ? '∅ (Dead End)' : (edge.target().data('label') || '?');
    var bundleCount = d.bundleCount || 1;
    var bundleHtml = bundleCount > 1 ? '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Bundled Edges</span><span class="detail-value" style="color:var(--fg);font-weight:500;color:#818cf8;">×' + bundleCount + '</span></div>' : '';
    panel.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">' +
      '<span style="font-size:20px;">🔗</span>' +
      '<div><div style="font-size:15px;font-weight:600;">' + sourceLabel + ' → ' + targetLabel + '</div>' +
      '<span class="detail-tag" style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:' + (EDGE_COLORS[status] || '#64748b') + '22;color:' + (EDGE_COLORS[status] || '#64748b') + ';">' + statusIcon + ' ' + status + '</span></div></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Source</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + sourceLabel + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Target</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + targetLabel + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Mechanism</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + (d.mechanism || '-') + '</span></div>' +
      '<div class="detail-row" style="display:flex;justify-content:space-between;padding:6px 0;font-size:13px;border-bottom:1px solid rgba(30,41,59,0.5);"><span class="detail-label" style="color:var(--muted);">Confidence</span><span class="detail-value" style="color:var(--fg);font-weight:500;">' + d.confidence + '%</span></div>' +
      bundleHtml +
      (d.status === 'red' ? '<div style="margin-top:10px;padding:8px;background:rgba(239,68,68,0.08);border-radius:6px;border-left:3px solid var(--danger);font-size:12px;color:var(--fg-2);"><strong style="color:var(--danger);">Dead End</strong> — This path has no consumer. Messages delivered here will be lost.</div>' : '');
  }

  // Expose for onclick handlers
  window.__pathwayShowEdge = function(edgeId) {
    if (!cy) return;
    var edge = cy.getElementById(edgeId);
    if (edge && edge.length) showEdgeDetail(edge);
  };

  function syncTreeToGraph() {
    if (!cy) return;
    document.querySelectorAll('#tree-body .tree-item').forEach(function(item) {
      var nid = item.getAttribute('data-node-id');
      var cb = item.querySelector('input[type="checkbox"]');
      if (!cb || !nid) return;
      var node = cy.getElementById(nid);
      if (!node || node.length === 0) return;
      node.style('display', cb.checked ? 'element' : 'none');
    });
    cy.nodes('.dead-end-node').forEach(function(n) {
      if (currentViewFilter === 'green' || currentViewFilter === 'yellow') {
        n.style('display', 'none');
      } else {
        n.style('display', 'element');
      }
    });
    cy.edges().forEach(function(e) {
      var src = e.source().style('display') !== 'none';
      var tgt = e.target().style('display') !== 'none';
      if (!src || !tgt) { e.style('display', 'none'); return; }
      if (currentViewFilter) {
        e.style('display', (e.data('status') === currentViewFilter) ? 'element' : 'none');
      } else {
        e.style('display', 'element');
      }
    });
    var layout = cy.layout(getLayoutConfig({ animate: true, animationDuration: 200 }));
    layout.run();
    updateFilterStatus();
  }

  function buildNodeTree() {
    var nodes = graphData.nodes || [];
    var body = document.getElementById('tree-body');
    if (!body) return;
    var counts = {};
    nodes.forEach(function(n) {
      var t = n.type || 'unknown';
      if (!counts[t]) counts[t] = [];
      counts[t].push(n);
    });
    var countEl = document.getElementById('tree-count');
    if (countEl) countEl.textContent = nodes.length + ' nodes';
    var html = '';
    var order = ['agent', 'cron', 'daemon', 'watcher', 'gateway', 'platform', 'consumer', 'router', 'filesystem'];
    order.forEach(function(t) {
      var items = counts[t] || [];
      var style = NODE_STYLES[t] || { icon: '❓', color: '#6b7280' };
      html += '<div>' +
        '<div class="tree-group-label" onclick="window.__toggleTreeGroup(this)" style="padding:5px 8px 2px;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--muted);letter-spacing:0.5px;display:flex;align-items:center;gap:4px;cursor:pointer;user-select:none;">' +
        '<span class="tree-group-toggle" style="font-size:8px;color:var(--muted);width:12px;flex-shrink:0;text-align:center;">▼</span> ' +
        '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:' + style.color + ';flex-shrink:0;"></span> ' + style.icon + ' ' + t + ' <span style="font-weight:400;color:var(--muted);">· ' + items.length + '</span></div>' +
        '<div class="tree-group-children">';
      items.forEach(function(n) {
        var nc = NODE_STYLES[n.type] || NODE_STYLES.agent;
        var disabled = shortcutActive ? ' disabled' : '';
        html += '<div class="tree-item" data-node-id="' + n.id + '" style="display:flex;align-items:center;gap:6px;padding:2px 8px 2px 8px;font-size:11px;font-weight:400;color:var(--fg-2);cursor:default;user-select:none;border-left:2px solid transparent;transition:all 0.1s;">' +
          '<input type="checkbox" checked' + disabled + ' onchange="window.__treeCheckboxChange(\'' + n.id + '\', this.checked)" style="accent-color:var(--accent);width:13px;height:13px;cursor:pointer;flex-shrink:0;">' +
          '<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:' + nc.color + ';flex-shrink:0;"></span>' +
          '<span class="tree-item-name" onclick="window.__treeFocusNode(\'' + n.id + '\')" style="cursor:pointer;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:1px 0;">' + n.name + '</span></div>';
      });
      html += '</div></div>';
    });
    body.innerHTML = html;
  }

  // Expose tree helpers
  window.__toggleTreeGroup = function(el) {
    var children = el.nextElementSibling;
    var toggle = el.querySelector('.tree-group-toggle');
    if (!children || !toggle) return;
    children.classList.toggle('collapsed');
    toggle.textContent = children.classList.contains('collapsed') ? '▶' : '▼';
  };

  window.__treeCheckboxChange = function(nodeId, checked) {
    if (shortcutActive) return;
    if (!cy) return;
    var node = cy.getElementById(nodeId);
    if (!node || node.length === 0) return;
    node.style('display', checked ? 'element' : 'none');
    node.connectedEdges().forEach(function(e) {
      var src = e.source().style('display') !== 'none';
      var tgt = e.target().style('display') !== 'none';
      e.style('display', (src && tgt) ? 'element' : 'none');
    });
    updateFilterStatus();
  };

  window.__treeFocusNode = function(nodeId) {
    if (!cy) return;
    var node = cy.getElementById(nodeId);
    if (!node || node.length === 0) return;
    cy.animate({ fit: { eles: node, padding: 40 }, duration: 300 });
    node.style('border-width', 4);
    node.style('border-color', '#fbbf24');
    node.style('border-opacity', 1);
    setTimeout(function() {
      if (cy) {
        node.style('border-width', 2);
        node.style('border-color', function(ele) { return ele.data('nodeColor'); });
        node.style('border-opacity', 0.5);
      }
    }, 1500);
    showNodeDetail(node);
  };

  // Filter functions (exposed globally for onclick)
  window.setFilter = function(filter, btn) {
    currentViewFilter = (filter === 'all') ? null : filter;
    document.querySelectorAll('[onclick^="setFilter"]').forEach(function(b) {
      b.classList.remove('active', 'active-red', 'active-amber');
    });
    if (filter === 'red') { btn.classList.add('active-red'); btn.style.background = 'rgba(239,68,68,0.15)'; btn.style.borderColor = 'var(--danger)'; btn.style.color = 'var(--danger)'; }
    else if (filter === 'yellow') { btn.classList.add('active-amber'); btn.style.background = 'rgba(245,158,11,0.15)'; btn.style.borderColor = 'var(--warn)'; btn.style.color = 'var(--warn)'; }
    else { btn.classList.add('active'); btn.style.background = 'rgba(34,197,94,0.15)'; btn.style.borderColor = 'var(--accent)'; btn.style.color = 'var(--accent)'; }
    var typeChips = document.querySelectorAll('[data-type]');
    var typeDisabled = filter !== 'all';
    typeChips.forEach(function(c) { c.classList.toggle('disabled', typeDisabled); if (typeDisabled) { c.style.opacity = '0.3'; c.style.pointerEvents = 'none'; } else { c.style.opacity = ''; c.style.pointerEvents = ''; } });
    if (filter === 'all') { clearShortcuts(); } else { applyShortcut(filter, null); }
  };

  window.setTypeFilter = function(type, btn) {
    document.querySelectorAll('[onclick^="setTypeFilter"]').forEach(function(b) {
      b.classList.remove('active', 'active-red', 'active-amber');
      b.style.background = ''; b.style.borderColor = ''; b.style.color = '';
    });
    btn.classList.add('active');
    btn.style.background = 'rgba(34,197,94,0.15)'; btn.style.borderColor = 'var(--accent)'; btn.style.color = 'var(--accent)';
    if (type === 'all') { clearShortcuts(); } else { applyShortcut(null, type); }
  };

  function getNodesForFilter(filter) {
    if (filter === 'all') return null;
    var es = graphData.edges || [];
    var ids = new Set();
    es.forEach(function(e) {
      if (e.status === filter) { ids.add(e.source_id); if (e.target_id) ids.add(e.target_id); }
    });
    return ids;
  }

  function getNodesForType(typeFilter) {
    if (typeFilter === 'all') return null;
    var ns = graphData.nodes || [];
    var ids = new Set();
    ns.forEach(function(n) { if (n.type === typeFilter) ids.add(n.id); });
    return ids;
  }

  function applyShortcut(viewFilter, typeFilter) {
    shortcutActive = true;
    var viewIds = viewFilter ? getNodesForFilter(viewFilter) : null;
    var typeIds = typeFilter ? getNodesForType(typeFilter) : null;
    document.querySelectorAll('#tree-body .tree-item').forEach(function(item) {
      var nid = item.getAttribute('data-node-id');
      var cb = item.querySelector('input[type="checkbox"]');
      if (!cb || !nid) return;
      var visible = true;
      if (viewIds && !viewIds.has(nid)) visible = false;
      if (typeIds && !typeIds.has(nid)) visible = false;
      cb.checked = visible;
      cb.disabled = true;
    });
    updateFilterStatus();
    syncTreeToGraph();
  }

  function clearShortcuts() {
    shortcutActive = false;
    document.querySelectorAll('#tree-body .tree-item input[type="checkbox"]').forEach(function(cb) {
      cb.checked = true;
      cb.disabled = false;
    });
    var statusBar = document.getElementById('filter-status-bar');
    if (statusBar) statusBar.style.display = 'none';
    syncTreeToGraph();
  }

  async function fetchGraph() {
    try {
      var headers = {};
      if (window.__OBSERVECO_TOKEN) headers['X-ObserveCo-Token'] = window.__OBSERVECO_TOKEN;
      var resp = await fetch('/api/pathway-graph', { headers: headers });
      graphData = await resp.json();
      return true;
    } catch (e) {
      console.error('Failed to fetch pathway graph:', e);
      return false;
    }
  }

  function initializeCy() {
    if (cy) { cy.destroy(); cy = null; }
    var cyContainer = document.getElementById('cy');
    if (!cyContainer) return;
    var loadingEl = cyContainer.querySelector('.loading');
    if (loadingEl) loadingEl.remove();
    var elements = buildCytoscapeElements();
    if (typeof cytoscape === 'undefined') {
      cyContainer.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted);font-size:13px;">Cytoscape library not loaded. Refresh the page.</div>';
      return;
    }
    cy = cytoscape({
      container: cyContainer,
      elements: elements,
      style: [
        { selector: 'node', style: { 'label': 'data(label)', 'text-valign': 'center', 'text-halign': 'center', 'color': '#e2e8f0', 'font-size': '13px', 'font-weight': '600', 'font-family': 'Inter, system-ui, sans-serif', 'width': 'label', 'height': 'label', 'padding': '8px 12px', 'shape': function(ele) { return ele.data('shape'); }, 'background-color': function(ele) { return ele.data('nodeColor'); }, 'border-width': 2, 'border-color': function(ele) { return ele.data('nodeColor'); }, 'border-opacity': 0.5, 'text-wrap': 'wrap', 'text-max-width': '200px', 'min-width': '60px', 'min-height': '30px' } },
        { selector: 'node.dead-end-node', style: { 'background-color': '#ef4444', 'border-color': '#ef4444', 'color': '#ef4444', 'font-size': '18px', 'font-weight': '800', 'padding': '4px 6px', 'min-width': '24px', 'min-height': '24px', 'shape': 'ellipse', 'text-valign': 'center', 'text-halign': 'center', 'width': '28px', 'height': '28px' } },
        { selector: 'edge', style: { 'width': 2, 'line-color': '#64748b', 'target-arrow-color': '#64748b', 'target-arrow-shape': 'triangle', 'arrow-scale': 1.2, 'curve-style': 'bezier', 'font-size': '10px', 'color': '#64748b', 'font-family': 'Inter, system-ui, sans-serif', 'text-rotation': 'autorotate', 'text-margin-y': -8, 'text-background-color': '#0c111d', 'text-background-opacity': 0.8, 'text-background-padding': '2px' } },
        { selector: 'edge.edge-green', style: { 'line-color': '#22c55e', 'target-arrow-color': '#22c55e', 'width': 2.5 } },
        { selector: 'edge.edge-yellow', style: { 'line-color': '#eab308', 'target-arrow-color': '#eab308', 'width': 2.5, 'line-style': 'dashed' } },
        { selector: 'edge.edge-red', style: { 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'width': 2, 'line-style': 'dashed', 'target-arrow-shape': 'tee' } },
        { selector: 'edge.edge-teal', style: { 'line-color': '#14b8a6', 'target-arrow-color': '#14b8a6', 'width': 1.5, 'line-style': 'dashed' } },
        { selector: 'node:selected', style: { 'border-width': 3, 'border-opacity': 1 } },
        { selector: 'edge:selected', style: { 'width': 3.5 } }
      ],
      layout: getLayoutConfig(),
      minZoom: 0.4, maxZoom: 2.5, wheelSensitivity: 0.3,
    });
    cy.on('tap', 'node', function(evt) {
      var node = evt.target;
      showNodeDetail(node);
      cy.animate({ fit: { eles: node, padding: 40 }, duration: 300 });
    });
    cy.on('tap', 'edge', function(evt) { showEdgeDetail(evt.target); });
    cy.on('tap', function(evt) { if (evt.target === cy) showEmptyDetail(); });
    cy.on('mouseover', 'node', function(evt) {
      var node = evt.target;
      var connected = new Set();
      node.connectedEdges().forEach(function(e) { connected.add(e.source().id()); connected.add(e.target().id()); });
      cy.nodes().forEach(function(n) { if (n.id() !== node.id() && !connected.has(n.id()) && n.data('type') !== 'dead-end') n.style('opacity', 0.25); });
      cy.edges().forEach(function(e) { if (e.source().id() !== node.id() && e.target().id() !== node.id()) e.style('opacity', 0.15); });
    });
    cy.on('mouseout', 'node', function() { cy.nodes().forEach(function(n) { n.style('opacity', 1); }); cy.edges().forEach(function(e) { e.style('opacity', 1); }); });
    syncTreeToGraph();
    updateFilterStatus();
    updateSummary();
  }

  async function initPathway() {
    var cyContainer = document.getElementById('cy');
    if (!cyContainer) return; // not our tab
    var ok = await fetchGraph();
    if (!ok) {
      cyContainer.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted);font-size:13px;">Failed to load pathway data.</div>';
      return;
    }
    buildNodeTree();
    initializeCy();
  }

  // Auto-init when #cy appears (htmx swap)
  var observer = new MutationObserver(function() {
    if (document.getElementById('cy')) {
      observer.disconnect();
      initPathway();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Also check immediately in case already in DOM
  if (document.getElementById('cy')) {
    observer.disconnect();
    initPathway();
  }

  // Re-init on htmx after-swap for the pathway container
  document.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target && e.detail.target.id === 'pathwayContainer') {
      // Small delay for DOM to settle
      setTimeout(function() {
        if (document.getElementById('cy') && !cy) initPathway();
      }, 50);
    }
  });  // htmx:afterSwap

  // ─── Particles ───
  var particlesEnabled = true;
  var particleCtx = null;
  var particleCanvas = null;
  var particleAnimFrame = null;
  var particles = [];
  var particleResizeHandler = null;

  function initParticleCanvas() {
    var container = document.getElementById('cy');
    if (!container) return;
    var canvas = document.createElement('canvas');
    canvas.id = 'particle-canvas';
    canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2;';
    container.style.position = 'relative';
    container.appendChild(canvas);
    particleCanvas = canvas;
    particleCtx = canvas.getContext('2d');
    particleResizeCanvas();
    if (particleResizeHandler) window.removeEventListener('resize', particleResizeHandler);
    particleResizeHandler = function() { particleResizeCanvas(); };
    window.addEventListener('resize', particleResizeHandler);
    if (cy) {
      cy.on('viewport', function() { particleResizeCanvas(); });
      cy.on('zoom', function() { particleResizeCanvas(); });
      cy.on('pan', function() { particleResizeCanvas(); });
    }
  }

  function particleResizeCanvas() {
    if (!particleCanvas || !cy) return;
    var rect = particleCanvas.parentElement.getBoundingClientRect();
    particleCanvas.width = rect.width;
    particleCanvas.height = rect.height;
  }

  window.toggleParticles = function() {
    particlesEnabled = !particlesEnabled;
    var btn = document.getElementById('particle-btn');
    if (!btn) return;
    if (particlesEnabled) {
      btn.classList.add('btn-active');
      btn.textContent = '💫 Particles ON';
      if (!particleCanvas) initParticleCanvas();
      startParticles();
    } else {
      btn.classList.remove('btn-active');
      btn.textContent = '💫 Particles';
      stopParticles();
    }
  };

  function startParticles() {
    if (particleAnimFrame) cancelAnimationFrame(particleAnimFrame);
    particleAnimFrame = requestAnimationFrame(animateParticles);
  }

  function stopParticles() {
    if (particleAnimFrame) cancelAnimationFrame(particleAnimFrame);
    particleAnimFrame = null;
    particles = [];
    if (particleCtx && particleCanvas) {
      particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
    }
  }

  function animateParticles() {
    if (!particlesEnabled || !cy || !particleCtx) return;
    particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
    var zoom = cy.zoom();
    var panX = cy.pan().x;
    var panY = cy.pan().y;
    cy.edges(':visible').forEach(function(e) {
      if (currentViewFilter && e.data('status') !== currentViewFilter) return;
      var source = e.source();
      var target = e.target();
      if (!source || !target) return;
      var srcPos = source.position();
      var tgtPos = target.position();
      if (!srcPos || !tgtPos) return;
      if (Math.random() > 0.03) return;
      var status = e.data('status') || 'unknown';
      var color = EDGE_COLORS[status] || '#64748b';
      particles.push({
        sx: srcPos.x, sy: srcPos.y,
        tx: tgtPos.x, ty: tgtPos.y,
        t: 0, speed: 0.003 + Math.random() * 0.007,
        color: color, size: 1.2 + Math.random() * 0.8
      });
    });
    var newParticles = [];
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.t += p.speed;
      if (p.t >= 1) continue;
      var x = (p.sx + (p.tx - p.sx) * p.t) * zoom + panX;
      var y = (p.sy + (p.ty - p.sy) * p.t) * zoom + panY;
      particleCtx.save();
      particleCtx.globalAlpha = 0.3;
      particleCtx.fillStyle = p.color;
      particleCtx.beginPath();
      particleCtx.arc(x, y, p.size * 2.5, 0, Math.PI * 2);
      particleCtx.fill();
      particleCtx.globalAlpha = 0.9;
      particleCtx.fillStyle = p.color;
      particleCtx.beginPath();
      particleCtx.arc(x, y, p.size, 0, Math.PI * 2);
      particleCtx.fill();
      particleCtx.restore();
      newParticles.push(p);
    }
    particles = newParticles;
    // Cap particles to prevent performance issues
    if (particles.length > 2000) particles = particles.slice(-2000);
    particleAnimFrame = requestAnimationFrame(animateParticles);
  }

  // Auto-start particles after graph init
  var origInit = initializeCy;
  initializeCy = function() {
    origInit();
    setTimeout(function() {
      if (!particleCanvas) initParticleCanvas();
      startParticles();
    }, 100);
  };

  // ─── Re-layout ───
  window.resetLayout = function() {
    if (!cy) return;
    var layout = cy.layout(getLayoutConfig({ animationDuration: 400 }));
    layout.run();
  };

  // ─── Data Reload ───
  window.refreshData = async function() {
    stopParticles();
    if (particleCanvas) {
      particleCanvas.remove();
      particleCanvas = null;
      particleCtx = null;
    }
    document.getElementById('cy').innerHTML = '<div class="loading" style="text-align:center;padding:40px;color:var(--muted);font-size:13px;">Refreshing...</div>';
    var ok = await fetchGraph();
    if (!ok) {
      document.getElementById('cy').innerHTML = '<div class="loading" style="text-align:center;padding:40px;color:var(--muted);font-size:13px;">Failed to load data.</div>';
      return;
    }
    initializeCy();
    buildNodeTree();
  };

  } catch(e) { console.error('pathway.js init error:', e.message, e.stack); }
})();
