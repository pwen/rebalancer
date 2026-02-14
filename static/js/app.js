// ── State ────────────────────────────────────────────────
let breakdownData = null;
let selectedDate = '';  // '' = latest
let liveMode = false;
let allHoldings = [];   // cached for filtering
let holdingsSort = { key: 'value', dir: -1 };  // default: by value desc
let activeTab = 'holdings';
let breakdownView = 'bars';  // 'bars' or 'pie'
let regionFilter = 'equity';   // 'all' or 'equity'

// Categories excluded in "Equity Only" region view
const BOND_CASH_CATEGORIES = new Set(['Cash', 'Short-Term Treasuries', 'Long-Term Treasuries']);

// Color map matching CSS bar colors
const PIE_COLORS = {
    // Regions
    US: '#60a5fa', DM: '#a78bfa', EM: '#fb923c', Global: '#fbbf24',
    // Categories
    Technology: '#60a5fa', Financials: '#34d399', 'Health Care': '#f87171',
    'Consumer Discretionary': '#fb923c', 'Communication Services': '#a78bfa',
    Industrials: '#fbbf24', 'Consumer Staples': '#2dd4bf', Energy: '#f472b6',
    Utilities: '#38bdf8', 'Real Estate': '#e879f9', Materials: '#a3e635',
    'Precious Metals': '#fcd34d', Commodities: '#fb7185', Cryptocurrency: '#c084fc',
    'Short-Term Treasuries': '#6ee7b7', 'Long-Term Treasuries': '#67e8f9',
    Cash: '#9ca3af', Other: '#94a3b8',
};

// ── Tabs ─────────────────────────────────────────────────
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `tab-${tab}`);
    });
    history.replaceState(null, '', `#${tab}`);
}

function restoreTab() {
    const hash = location.hash.replace('#', '');
    if (hash && document.getElementById(`tab-${hash}`)) {
        switchTab(hash);
    }
}
window.addEventListener('hashchange', () => {
    const hash = location.hash.replace('#', '');
    if (hash && hash !== activeTab) switchTab(hash);
});

// ── Upload ──────────────────────────────────────────────
function initUploadDate() {
    const dateInput = document.getElementById('upload-date');
    if (!dateInput.value) {
        dateInput.value = new Date().toISOString().slice(0, 10);
    }
}

async function uploadCSV() {
    const brokerage = document.getElementById('upload-brokerage').value;
    const fileInput = document.getElementById('upload-file');
    const dateInput = document.getElementById('upload-date');
    const statusEl = document.getElementById('upload-status');

    if (!fileInput.files.length) {
        statusEl.textContent = 'Please select a CSV file.';
        statusEl.className = 'status-msg error';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('brokerage', brokerage);
    formData.append('snapshot_date', dateInput.value);

    statusEl.textContent = 'Uploading and classifying...';
    statusEl.className = 'status-msg';

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            statusEl.textContent = data.error || 'Upload failed';
            statusEl.className = 'status-msg error';
            return;
        }

        statusEl.textContent = data.message;
        statusEl.className = 'status-msg success';
        fileInput.value = '';

        // Refresh snapshots and breakdown, then go to holdings tab
        await loadSnapshots();
        await loadBreakdown();
        switchTab('holdings');
    } catch (err) {
        statusEl.textContent = 'Network error: ' + err.message;
        statusEl.className = 'status-msg error';
    }
}

// ── Breakdown ───────────────────────────────────────────
async function loadBreakdown() {
    if (liveMode) {
        return loadLiveBreakdown();
    }

    document.getElementById('live-banner').style.display = 'none';

    try {
        const params = selectedDate ? `?date=${selectedDate}` : '';
        const res = await fetch('/api/breakdown' + params);
        breakdownData = await res.json();

        if (breakdownData.total_value === 0) {
            document.getElementById('holdings-empty').style.display = '';
            document.getElementById('breakdown-empty').style.display = '';
            return;
        }

        document.getElementById('holdings-empty').style.display = 'none';
        document.getElementById('breakdown-empty').style.display = 'none';

        // Total value
        const fmtTotal = '$' + breakdownData.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 });
        document.getElementById('total-value').textContent = fmtTotal;
        document.getElementById('breakdown-total').textContent = fmtTotal;

        // Render bars
        renderRegionBreakdown();
        renderBars('category-bars', breakdownData.by_category);

        // Render pies if in pie view
        if (breakdownView === 'pie') {
            renderPie('category-pie', breakdownData.by_category);
        }

        // Holdings table
        renderHoldings(breakdownData.holdings);

        // Show saved analysis if available
        showSavedAnalysis(breakdownData);

        // Load targets
        await loadTargets();
    } catch (err) {
        console.error('Failed to load breakdown:', err);
    }
}

function renderBars(containerId, data) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    const sorted = Object.entries(data).sort((a, b) => b[1].pct - a[1].pct);
    for (const [label, info] of sorted) {
        const cssLabel = label.replace(/\s+/g, '-');
        container.innerHTML += `
      <div class="bar-row">
        <span class="bar-label">${label}</span>
        <div class="bar-track">
          <div class="bar-fill ${cssLabel}" style="width: ${info.pct}%"></div>
        </div>
        <span class="bar-value">${info.pct.toFixed(1)}% ($${info.value.toLocaleString(undefined, { maximumFractionDigits: 0 })})</span>
      </div>
    `;
    }
}

function renderPie(containerId, data) {
    const container = document.getElementById(containerId);
    const entries = Object.entries(data)
        .filter(([, info]) => info.pct > 0)
        .sort((a, b) => b[1].pct - a[1].pct);

    // Build conic-gradient stops
    let angle = 0;
    const stops = [];
    entries.forEach(([label, info]) => {
        const color = PIE_COLORS[label] || '#94a3b8';
        const start = angle;
        angle += info.pct * 3.6; // pct to degrees
        stops.push(`${color} ${start}deg ${angle}deg`);
    });

    const legendHtml = entries.map(([label, info]) => {
        const color = PIE_COLORS[label] || '#94a3b8';
        return `<div class="pie-legend-item">
            <span class="pie-swatch" style="background:${color}"></span>
            <span class="pie-legend-label">${label}</span>
            <span class="pie-legend-value">${info.pct.toFixed(1)}%</span>
        </div>`;
    }).join('');

    container.innerHTML = `
        <div class="pie-wrapper">
            <div class="pie-chart" style="background: conic-gradient(${stops.join(', ')})"></div>
            <div class="pie-legend">${legendHtml}</div>
        </div>
    `;
}

function setBreakdownView(view) {
    breakdownView = view;
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    const showBars = view === 'bars';
    document.getElementById('region-bars').style.display = showBars ? '' : 'none';
    document.getElementById('category-bars').style.display = showBars ? '' : 'none';
    document.getElementById('region-pie').style.display = showBars ? 'none' : '';
    document.getElementById('category-pie').style.display = showBars ? 'none' : '';

    // Re-render with current data
    if (breakdownData) {
        renderRegionBreakdown();
        if (!showBars) {
            renderPie('category-pie', breakdownData.by_category);
        }
    }
}

function setRegionFilter(filter) {
    regionFilter = filter;
    document.querySelectorAll('.rfilt-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.rfilt === filter);
    });
    renderRegionBreakdown();
}

function computeFilteredRegion() {
    if (!breakdownData || !breakdownData.holdings) return breakdownData.by_region;
    if (regionFilter === 'all') return breakdownData.by_region;

    // Recompute region breakdown excluding bond/cash categories
    const regionTotals = {};
    let filteredTotal = 0;

    for (const h of breakdownData.holdings) {
        const cat = h.category || {};
        // Calculate what % of this holding is in non-bond/cash categories
        let excludedPct = 0;
        for (const [catName, catPct] of Object.entries(cat)) {
            if (BOND_CASH_CATEGORIES.has(catName)) excludedPct += catPct;
        }
        const equityRatio = (100 - excludedPct) / 100;
        if (equityRatio <= 0) continue;

        const adjustedValue = h.value * equityRatio;
        filteredTotal += adjustedValue;

        const region = h.region || {};
        for (const [regName, regPct] of Object.entries(region)) {
            regionTotals[regName] = (regionTotals[regName] || 0) + adjustedValue * regPct / 100;
        }
    }

    if (filteredTotal === 0) return {};

    // Build sorted result
    const sorted = Object.entries(regionTotals).sort((a, b) => b[1] - a[1]);
    const result = {};
    for (const [k, v] of sorted) {
        result[k] = { value: Math.round(v * 100) / 100, pct: Math.round(v / filteredTotal * 10000) / 100 };
    }
    return result;
}

function renderRegionBreakdown() {
    const regionData = computeFilteredRegion();
    if (breakdownView === 'bars') {
        renderBars('region-bars', regionData);
    } else {
        renderPie('region-pie', regionData);
    }
}

function renderHoldings(holdings) {
    allHoldings = holdings;
    populateFilterDropdowns(holdings);
    applyHoldingsFilters();
}

function populateFilterDropdowns(holdings) {
    // Brokerage filter
    const brokerages = new Set();
    const categories = new Set();
    const regions = new Set();

    holdings.forEach(h => {
        (h.brokerages || []).forEach(b => brokerages.add(b));
        Object.keys(h.category || {}).forEach(c => categories.add(c));
        Object.keys(h.region || {}).forEach(r => regions.add(r));
    });

    fillSelect('filter-brokerage', sorted(brokerages));
    fillSelect('filter-category', sorted(categories));
    fillSelect('filter-region', sorted(regions));
}

function fillSelect(id, values) {
    const sel = document.getElementById(id);
    const current = sel.value;
    sel.innerHTML = '<option value="">All</option>';
    values.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        sel.appendChild(opt);
    });
    // Restore previous selection if still valid
    if (values.includes(current)) sel.value = current;
}

function sorted(setObj) {
    return [...setObj].sort();
}

function sortHoldings(key) {
    if (holdingsSort.key === key) {
        holdingsSort.dir *= -1;  // toggle direction
    } else {
        holdingsSort.key = key;
        holdingsSort.dir = (['ticker', 'primaryCategory', 'security_type', 'primaryRegion'].includes(key)) ? 1 : -1;  // alpha asc, numbers desc
    }
    applyHoldingsFilters();
}

function applyHoldingsFilters() {
    const brokerage = document.getElementById('filter-brokerage').value;
    const category = document.getElementById('filter-category').value;
    const region = document.getElementById('filter-region').value;

    let filtered = allHoldings;

    if (brokerage) {
        filtered = filtered.filter(h => (h.brokerages || []).includes(brokerage));
    }
    if (category) {
        filtered = filtered.filter(h => h.category && h.category[category]);
    }
    if (region) {
        filtered = filtered.filter(h => h.region && h.region[region]);
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
        let va, vb;
        const stringKeys = ['ticker', 'primaryCategory', 'security_type', 'primaryRegion'];
        if (stringKeys.includes(holdingsSort.key)) {
            va = holdingsSort.key === 'ticker' ? a.ticker
                : holdingsSort.key === 'security_type' ? (a.security_type || '')
                    : holdingsSort.key === 'primaryRegion' ? getPrimaryRegion(a)
                        : getPrimaryCategory(a);
            vb = holdingsSort.key === 'ticker' ? b.ticker
                : holdingsSort.key === 'security_type' ? (b.security_type || '')
                    : holdingsSort.key === 'primaryRegion' ? getPrimaryRegion(b)
                        : getPrimaryCategory(b);
            return holdingsSort.dir * va.localeCompare(vb);
        }
        va = a[holdingsSort.key] || 0;
        vb = b[holdingsSort.key] || 0;
        return holdingsSort.dir * (va - vb);
    });

    // Update sort indicators
    document.querySelectorAll('.holdings-table th[data-sort]').forEach(th => {
        const arrow = th.querySelector('.sort-arrow');
        if (th.dataset.sort === holdingsSort.key) {
            arrow.textContent = holdingsSort.dir === 1 ? ' \u25B2' : ' \u25BC';
        } else {
            arrow.textContent = '';
        }
    });

    const tbody = document.getElementById('holdings-tbody');
    document.getElementById('holdings-count').textContent = filtered.length;

    tbody.innerHTML = filtered.map(h => {
        const price = h.price || 0;
        const costPerShare = h.cost_per_share || 0;
        const costBasis = h.cost_basis || 0;
        const badges = (h.brokerages || []).map(b =>
            `<span class="badge badge-${b}">${b[0].toUpperCase()}</span>`
        ).join('');
        const catLabel = getPrimaryCategory(h);
        const regionLabel = getPrimaryRegion(h);
        const typeLabel = h.security_type || '—';

        return `
    <tr>
      <td class="mono"><strong>${h.ticker}</strong></td>
      <td class="mono">${h.quantity ? h.quantity.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 4 }) : '—'}</td>
      <td class="mono">$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
      <td class="mono">${costPerShare ? '$' + costPerShare.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</td>
      <td class="mono">${costBasis ? '$' + costBasis.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '—'}</td>
      <td class="mono">$${h.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
      <td class="mono">${h.pct.toFixed(1)}%</td>
      <td class="type-label type-${typeLabel.toLowerCase().replace(/\s+/g, '-')}">${typeLabel}</td>
      <td class="cat-label">${catLabel}</td>
      <td class="region-label">${regionLabel}</td>
      <td>${badges}</td>
    </tr>
  `;
    }).join('');

    // Filter summary
    updateFilterSummary(filtered, brokerage, category, region);
}

function updateFilterSummary(filtered, brokerage, category, region) {
    const summaryEl = document.getElementById('filter-summary');
    const anyFilter = brokerage || category || region;

    if (!anyFilter) {
        summaryEl.style.display = 'none';
        return;
    }

    const totalValue = breakdownData ? breakdownData.total_value : 0;
    const filteredValue = filtered.reduce((sum, h) => sum + h.value, 0);
    const filteredPct = totalValue ? (filteredValue / totalValue * 100) : 0;

    const parts = [];
    if (brokerage) parts.push(brokerage.charAt(0).toUpperCase() + brokerage.slice(1));
    if (category) parts.push(category);
    if (region) parts.push(region);
    const label = parts.join(' + ');

    summaryEl.style.display = '';
    summaryEl.innerHTML = `
        <strong>${label}:</strong>
        ${filtered.length} holdings ·
        $${filteredValue.toLocaleString(undefined, { minimumFractionDigits: 2 })} ·
        <strong>${filteredPct.toFixed(1)}%</strong> of portfolio
    `;
}

function formatBreakdown(bd) {
    return Object.entries(bd)
        .map(([k, v]) => `${k} ${v}%`)
        .join(', ');
}

// ── Targets ─────────────────────────────────────────────
async function loadTargets() {
    try {
        const [targetsRes] = await Promise.all([fetch('/api/targets')]);
        const targets = await targetsRes.json();

        const targetMap = {};
        for (const t of targets) {
            if (!targetMap[t.dimension]) targetMap[t.dimension] = {};
            targetMap[t.dimension][t.label] = t.target_pct;
        }

        renderTargets('category', targetMap.category || {});
    } catch (err) {
        console.error('Failed to load targets:', err);
    }
}

function renderTargets(dimension, savedTargets) {
    const container = document.getElementById(`${dimension}-targets`);
    const source = breakdownData[`by_${dimension}`];

    // Get all labels from both current breakdown and saved targets, sorted by current weight desc
    const labels = [...new Set([...Object.keys(source), ...Object.keys(savedTargets)])]
        .sort((a, b) => ((source[b] ? source[b].pct : 0) - (source[a] ? source[a].pct : 0)));

    container.innerHTML = labels.map(label => {
        const current = source[label] ? source[label].pct.toFixed(1) : '0.0';
        const target = savedTargets[label] !== undefined ? savedTargets[label] : '';

        return `
      <div class="target-row">
        <span class="target-label">${label}</span>
        <input type="number" class="target-input" data-dimension="${dimension}" data-label="${label}"
               value="${target}" min="0" max="100" step="0.5"
               oninput="updateTargetTotal('${dimension}')" placeholder="—" />
        <span class="target-current">(now ${current}%)</span>
      </div>
    `;
    }).join('');

    updateTargetTotal(dimension);
}

function updateTargetTotal(dimension) {
    const inputs = document.querySelectorAll(`.target-input[data-dimension="${dimension}"]`);
    let total = 0;
    inputs.forEach(input => {
        total += parseFloat(input.value) || 0;
    });

    const totalEl = document.getElementById(`${dimension}-total`);
    totalEl.textContent = total.toFixed(1);

    const parent = totalEl.closest('.targets-total');
    parent.className = 'targets-total';
    if (Math.abs(total - 100) < 0.5) parent.classList.add('balanced');
    else if (total > 100) parent.classList.add('over');
    else parent.classList.add('under');
}

async function saveTargets(dimension) {
    const inputs = document.querySelectorAll(`.target-input[data-dimension="${dimension}"]`);
    const allocations = [];

    inputs.forEach(input => {
        const pct = parseFloat(input.value);
        if (pct > 0) {
            allocations.push({ label: input.dataset.label, target_pct: pct });
        }
    });

    const total = allocations.reduce((s, a) => s + a.target_pct, 0);
    if (Math.abs(total - 100) > 1) {
        alert(`Target percentages must sum to 100 (currently ${total.toFixed(1)})`);
        return;
    }

    try {
        const res = await fetch('/api/targets', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dimension, allocations }),
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Failed to save targets');
            return;
        }

        // Flash success
        const btn = event.target;
        const orig = btn.textContent;
        btn.textContent = '✓ Saved';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

// ── Rebalance ───────────────────────────────────────────
async function loadRebalance() {
    try {
        const params = selectedDate ? `?date=${selectedDate}` : '';
        const endpoint = liveMode ? '/api/live-rebalance' : '/api/rebalance';
        const res = await fetch(endpoint + params);
        const data = await res.json();

        if (data.error) {
            document.getElementById('rebalance-summary').textContent = data.error;
            return;
        }

        // Summary
        document.getElementById('rebalance-summary').innerHTML =
            data.summary.split('; ').map(s => `<div>${s}</div>`).join('');

        // Tables
        renderRebalanceTable('category-rebalance', data.category);
        renderRebalanceTable('region-rebalance', data.region);
    } catch (err) {
        console.error('Failed to load rebalance:', err);
    }
}

function renderRebalanceTable(tableId, items) {
    const table = document.getElementById(tableId);

    if (!items || items.length === 0) {
        table.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-dim)">Set targets first</td></tr>';
        return;
    }

    table.innerHTML = `
    <thead>
      <tr>
        <th>Label</th>
        <th>Current</th>
        <th>Target</th>
        <th>Drift</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      ${items.map(item => `
        <tr>
          <td><strong>${item.label}</strong></td>
          <td class="mono">${item.current_pct.toFixed(1)}%</td>
          <td class="mono">${item.target_pct.toFixed(1)}%</td>
          <td class="mono ${item.drift > 0 ? 'drift-pos' : 'drift-neg'}">
            ${item.drift > 0 ? '+' : ''}${item.drift.toFixed(1)}%
          </td>
          <td class="action-${item.action}">
            ${item.action === 'hold' ? '—' :
            `${item.action.toUpperCase()} $${item.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          </td>
        </tr>
      `).join('')}
    </tbody>
  `;
}

// ── Snapshots ───────────────────────────────────────────
async function loadSnapshots() {
    try {
        const res = await fetch('/api/snapshots');
        const snapshots = await res.json();

        // Populate date selector
        const select = document.getElementById('snapshot-select');
        const currentVal = select.value;
        select.innerHTML = '<option value="">Latest</option>';

        // Group by date
        const dateSet = new Set();
        snapshots.forEach(s => dateSet.add(s.snapshot_date));
        for (const d of dateSet) {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            select.appendChild(opt);
        }
        select.value = currentVal || '';

        // Render snapshot history
        renderSnapshotList(snapshots);
    } catch (err) {
        console.error('Failed to load snapshots:', err);
    }
}

function renderSnapshotList(snapshots) {
    const container = document.getElementById('snapshot-list');

    if (!snapshots.length) {
        container.innerHTML = '<p class="empty-msg">No snapshots yet — upload a CSV to get started.</p>';
        return;
    }

    // Group by date
    const grouped = {};
    snapshots.forEach(s => {
        if (!grouped[s.snapshot_date]) grouped[s.snapshot_date] = [];
        grouped[s.snapshot_date].push(s);
    });

    let html = '<table class="snapshot-table"><thead><tr>' +
        '<th>Date</th><th>Brokerage</th><th>Holdings</th><th>Value</th><th>File</th><th></th>' +
        '</tr></thead><tbody>';

    for (const [date, snaps] of Object.entries(grouped)) {
        const totalValue = snaps.reduce((sum, s) => sum + s.total_value, 0);
        const totalHoldings = snaps.reduce((sum, s) => sum + s.holding_count, 0);

        // Date summary row
        html += `<tr class="snapshot-date-row">
            <td rowspan="${snaps.length + 1}"><strong>${date}</strong></td>
            <td colspan="2"><em>${totalHoldings} holdings total</em></td>
            <td><strong>$${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></td>
            <td colspan="2"></td>
        </tr>`;

        for (const s of snaps) {
            html += `<tr>
                <td class="brokerage-label ${s.brokerage}">${s.brokerage}</td>
                <td>${s.holding_count}</td>
                <td class="mono">$${s.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td class="filename">${s.filename || ''}</td>
                <td>
                    <button class="btn-icon" onclick="editSnapshotDate(${s.id}, '${date}')" title="Edit date">✏</button>
                    <button class="btn-icon" onclick="deleteSnapshot(${s.id})" title="Delete">✕</button>
                </td>
            </tr>`;
        }
    }

    html += '</tbody></table>';
    container.innerHTML = html;
}

async function deleteSnapshot(id) {
    if (!confirm('Delete this snapshot and all its holdings?')) return;

    try {
        await fetch(`/api/snapshots/${id}`, { method: 'DELETE' });
        await loadSnapshots();
        await loadBreakdown();
    } catch (err) {
        console.error('Failed to delete snapshot:', err);
    }
}

async function editSnapshotDate(id, currentDate) {
    const newDate = prompt('Enter new date (YYYY-MM-DD):', currentDate);
    if (!newDate || newDate === currentDate) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(newDate)) {
        alert('Invalid date format. Use YYYY-MM-DD.');
        return;
    }

    try {
        const res = await fetch(`/api/snapshots/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ snapshot_date: newDate }),
        });
        if (!res.ok) {
            const data = await res.json();
            alert(data.error || 'Failed to update snapshot');
            return;
        }
        await loadSnapshots();
        await loadBreakdown();
    } catch (err) {
        console.error('Failed to update snapshot:', err);
    }
}

function onSnapshotChange() {
    selectedDate = document.getElementById('snapshot-select').value;
    loadBreakdown();
}

// ── Live View ───────────────────────────────────────────
async function toggleLiveView() {
    liveMode = document.getElementById('live-toggle').checked;
    await loadBreakdown();
}

async function loadLiveBreakdown() {
    const banner = document.getElementById('live-banner');
    banner.style.display = '';
    banner.innerHTML = '<span class="loading">📡 Fetching live prices…</span>';

    try {
        const params = selectedDate ? `?date=${selectedDate}` : '';
        const res = await fetch('/api/live-breakdown' + params);
        breakdownData = await res.json();

        if (breakdownData.error) {
            banner.innerHTML = `<span class="error">${breakdownData.error}</span>`;
            return;
        }

        // Show change banner
        const change = breakdownData.total_change;
        const changePct = breakdownData.total_change_pct;
        const sign = change >= 0 ? '+' : '';
        const cls = change >= 0 ? 'change-pos' : 'change-neg';
        banner.innerHTML = `
            <span class="${cls}">
                ${sign}$${change.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                (${sign}${changePct.toFixed(2)}%) vs snapshot
            </span>
            <span class="snapshot-val">Snapshot: $${breakdownData.snapshot_total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
        `;

        // Render same as normal breakdown
        const fmtLive = '$' + breakdownData.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 }) + ' (live)';
        document.getElementById('total-value').textContent = fmtLive;
        document.getElementById('breakdown-total').textContent = fmtLive;

        renderRegionBreakdown();
        renderBars('category-bars', breakdownData.by_category);
        renderHoldings(breakdownData.holdings);

        await loadTargets();
    } catch (err) {
        banner.innerHTML = `<span class="error">Failed to fetch live prices: ${err.message}</span>`;
        console.error('Live breakdown error:', err);
    }
}

// ── Helpers ─────────────────────────────────────────────
function getPrimaryCategory(h) {
    if (!h.category) return '—';
    const entries = Object.entries(h.category);
    if (entries.length === 0) return '—';
    if (entries.length === 1) return entries[0][0];
    // Return top category, or "Mixed" if top < 80%
    entries.sort((a, b) => b[1] - a[1]);
    return entries[0][1] >= 80 ? entries[0][0] : 'Mixed';
}

function getPrimaryRegion(h) {
    if (!h.region) return '—';
    const entries = Object.entries(h.region);
    if (entries.length === 0) return '—';
    if (entries.length === 1) return entries[0][0];
    entries.sort((a, b) => b[1] - a[1]);
    return entries[0][1] >= 80 ? entries[0][0] : 'Mixed';
}
// ── AI Analysis ─────────────────────────────────────────
function showSavedAnalysis(data) {
    const btn = document.getElementById('analyze-btn');
    const output = document.getElementById('analysis-output');

    if (data.analysis) {
        output.style.display = '';
        output.innerHTML = markdownToHtml(data.analysis);
        btn.textContent = '🔮 Regenerate Analysis';
    } else {
        output.style.display = 'none';
        output.innerHTML = '';
        btn.textContent = '🔮 Generate AI Analysis';
    }
}

async function generateAnalysis() {
    const btn = document.getElementById('analyze-btn');
    const output = document.getElementById('analysis-output');

    btn.disabled = true;
    btn.textContent = '🔮 Analyzing...';
    output.style.display = '';
    output.innerHTML = '<p class="loading">Sending portfolio data to AI...</p>';

    try {
        const params = selectedDate ? `?date=${selectedDate}` : '';
        const res = await fetch('/api/analyze' + params, { method: 'POST' });
        const data = await res.json();

        if (data.error) {
            output.innerHTML = `<p class="error">${data.error}</p>`;
        } else {
            output.innerHTML = markdownToHtml(data.analysis);
        }
    } catch (err) {
        output.innerHTML = `<p class="error">Failed: ${err.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '🔮 Regenerate Analysis';
    }
}

function markdownToHtml(md) {
    // Simple markdown to HTML converter for our analysis output
    let html = md
        .replace(/\[\d+\]/g, '')  // strip citation references like [1][2][5]
        .replace(/^## (.+)$/gm, '<h3 class="analysis-heading">$1</h3>')
        .replace(/^### (.+)$/gm, '<h4 class="analysis-subheading">$1</h4>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\n/g, '<br>');
    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>(<br>)?)+/g, match => {
        const items = match.replace(/<br>/g, '');
        return `<ul>${items}</ul>`;
    });
    return html;
}
// ── Init ────────────────────────────────────────────────
restoreTab();
initUploadDate();
loadSnapshots();
loadBreakdown();
