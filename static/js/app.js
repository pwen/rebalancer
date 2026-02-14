// ── State ────────────────────────────────────────────────
let breakdownData = null;

// ── Upload ──────────────────────────────────────────────
async function uploadCSV(brokerage) {
    const fileInput = document.getElementById(`${brokerage}-file`);
    const statusEl = document.getElementById('upload-status');

    if (!fileInput.files.length) {
        statusEl.textContent = `Please select a ${brokerage} CSV file.`;
        statusEl.className = 'status-msg error';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('brokerage', brokerage);

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

        // Refresh breakdown
        await loadBreakdown();
    } catch (err) {
        statusEl.textContent = 'Network error: ' + err.message;
        statusEl.className = 'status-msg error';
    }
}

// ── Breakdown ───────────────────────────────────────────
async function loadBreakdown() {
    try {
        const res = await fetch('/api/breakdown');
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
    const tbody = document.getElementById('holdings-tbody');
    document.getElementById('holdings-count').textContent = holdings.length;

    tbody.innerHTML = holdings.map(h => `
    <tr>
      <td class="mono"><strong>${h.ticker}</strong></td>
      <td>${h.name || ''}</td>
      <td class="mono">$${h.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
      <td class="mono">${h.pct.toFixed(1)}%</td>
      <td>${h.brokerages.join(', ')}</td>
      <td>${formatBreakdown(h.region)}</td>
      <td>${formatBreakdown(h.category)}</td>
    </tr>
  `).join('');
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
        const res = await fetch('/api/rebalance');
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

// ── Init ────────────────────────────────────────────────
loadBreakdown();
