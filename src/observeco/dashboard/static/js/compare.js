// ─── Fleet Comparison sort ───
let compareSort = { col: 'name', order: 'asc' };

function updateCompareIndicators() {
  const activeCol = compareSort.col;
  const activeOrder = compareSort.order;
  document.querySelectorAll('.sort-indicator').forEach(el => {
    if (el.id === 'sortIndicator_' + activeCol) {
      el.textContent = activeOrder === 'asc' ? '▲' : '▼';
      el.style.color = '#86efac';
      el.style.opacity = '1';
    } else {
      el.textContent = '▲';
      el.style.color = '#86efac';
      el.style.opacity = '0.35';
    }
  });
}

function sortCompare(col) {
  if (compareSort.col === col) {
    compareSort.order = compareSort.order === 'asc' ? 'desc' : 'asc';
  } else {
    compareSort.col = col;
    compareSort.order = 'asc';
  }
  updateCompareIndicators();
  const panel = document.getElementById('comparePanel');
  if (panel) {
    panel.innerHTML = '<div style="color:#64748b;font-size:12px;">Sorting...</div>';
    fetch('/api/fleet-compare?sort=' + compareSort.col + '&order=' + compareSort.order)
      .then(r => r.text())
      .then(html => { panel.innerHTML = html; updateCompareIndicators(); });
  }
}
