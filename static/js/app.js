// ── State ────────────────────────────────────────────────
let breakdownData = null;
let selectedDate = '';  // '' = latest
let liveMode = false;
let allHoldings = [];   // cached for filtering
let holdingsSort = { key: 'value', dir: -1 };  // default: by value desc

// ── Upload ──────────────────────────────────────────────
async function uploadCSV(brokerage) {
    const fileInput = document.getElementById(`${brokerage}-file`);
    const dateInput = document.getElementById(`${brokerage}-date`);
    const statusEl = document.getElementById('upload-status');

    if (!fileInput.files.length) {
        statusEl.textContent = `Please select a ${brokerage} CSV file.`;
        statusEl.className = 'status-msg error';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('brokerage', brokerage);
    if (dateInput.value) {
        formData.append('snapshot_date', dateInput.value);
    }

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
        dateInput.value = '';

        // Refresh snapshots and breakdown
        await loadSnapshots();
        await loadBreakdown();
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
            document.getElementById('breakdown-section').style.display = 'none';
            document.getElementById('targets-section').style.display = 'none';
            document.getElementById('rebalance-section').style.display = 'none';
            return;
        }

        document.getElementById('breakdown-section').style.display = '';
        document.getElementById('targets-section').style.display = '';
        document.getElementById('rebalance-section').style.display = '';

        // Total value
        document.getElementById('total-value').textContent =
            '$' + breakdownData.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 });

        // Render bars
        renderBars('region-bars', breakdownData.by_region);
        renderBars('category-bars', breakdownData.by_category);

        // Holdings table
        renderHoldings(breakdownData.holdings);

        // Load targets
        await loadTargets();
    } catch (err) {
        console.error('Failed to load breakdown:', err);
    }
}

function renderBars(containerId, data) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    for (const [label, info] of Object.entries(data)) {
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
        holdingsSort.dir = key === 'ticker' ? 1 : -1;  // alpha asc, numbers desc
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
        if (holdingsSort.key === 'ticker') {
            va = a.ticker; vb = b.ticker;
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

        return `
    <tr>
      <td class="mono"><strong>${h.ticker}</strong></td>
      <td class="mono">${h.quantity ? h.quantity.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 4 }) : '—'}</td>
      <td class="mono">$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
      <td class="mono">${costPerShare ? '$' + costPerShare.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</td>
      <td class="mono">${costBasis ? '$' + costBasis.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '—'}</td>
      <td class="mono">$${h.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
      <td class="mono">${h.pct.toFixed(1)}%</td>
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

        renderTargets('region', targetMap.region || {});
        renderTargets('category', targetMap.category || {});
    } catch (err) {
        console.error('Failed to load targets:', err);
    }
}

function renderTargets(dimension, savedTargets) {
    const container = document.getElementById(`${dimension}-targets`);
    const source = breakdownData[`by_${dimension}`];

    // Get all labels from both current breakdown and saved targets
    const labels = [...new Set([...Object.keys(source), ...Object.keys(savedTargets)])];

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
                <td><button class="btn-icon" onclick="deleteSnapshot(${s.id})" title="Delete">✕</button></td>
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
        document.getElementById('total-value').textContent =
            '$' + breakdownData.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 }) + ' (live)';

        renderBars('region-bars', breakdownData.by_region);
        renderBars('category-bars', breakdownData.by_category);
        renderHoldings(breakdownData.holdings);

        await loadTargets();
    } catch (err) {
        banner.innerHTML = `<span class="error">Failed to fetch live prices: ${err.message}</span>`;
        console.error('Live breakdown error:', err);
    }
}

// ── Init ────────────────────────────────────────────────
loadSnapshots();
loadBreakdown();
