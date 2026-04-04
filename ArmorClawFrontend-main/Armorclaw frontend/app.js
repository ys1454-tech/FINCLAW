/* FINCLAW frontend wired to live backend */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const state = {
    apiBase:
      window.FINCLAW_API_BASE ||
      localStorage.getItem('FINCLAW_API_BASE') ||
      'http://127.0.0.1:8000',
    currentUser: null,
    dashboard: null,
    trades: [],
    policies: [],
    agent: null,
    notifications: [],
    selectedNotification: null,
    assetSearch: '',
    tradeAssets: ['AAPL', 'MSFT', 'NVDA'],
  };

  const defaultPolicyDescriptions = {
    'Maximum Trade Size Limit': 'Prevents execution of individual orders exceeding your configured risk threshold.',
    'Allowed Assets Only': 'Restricts execution to approved assets and paper-trading universe.',
    'Market Hours Enforcement': 'Pauses automated actions outside approved trading windows.',
    'No Leverage or Margin Trades': 'Disables margin and leveraged exposure.',
    'Risk Exposure Cap': 'Limits aggregate open risk across positions.',
  };

  function showToast(message, type = 'info') {
    const container = $('#toast-container');
    if (!container) return;
    const icons = { info: 'info', success: 'check_circle', error: 'error', warning: 'warning' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="material-symbols-outlined">${icons[type] || 'info'}</span>${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  function formatCurrency(num) {
    const value = Number(num || 0);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  }

  function formatPercent(num) {
    const value = Number(num || 0);
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  }

  async function api(path, options = {}) {
    const response = await fetch(`${state.apiBase}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });

    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }

    if (!response.ok) {
      const message =
        (data && data.detail && data.detail.reason) ||
        (typeof data?.detail === 'string' ? data.detail : null) ||
        data?.message ||
        `Request failed with status ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function rememberUser(user) {
    state.currentUser = user;
    localStorage.setItem('finclaw.currentUser', JSON.stringify(user));
  }

  function loadRememberedUser() {
    try {
      const raw = localStorage.getItem('finclaw.currentUser');
      if (raw) state.currentUser = JSON.parse(raw);
    } catch {}
  }

  function getCurrentEmail() {
    return state.currentUser?.email || $('#login-username')?.value?.trim() || '';
  }

  function syncUserUI() {
    if (!state.currentUser) return;
    const name = state.currentUser.displayName || state.currentUser.email.split('@')[0];
    const tier = `${state.currentUser.risk || 'medium'} risk • ${state.currentUser.asset || 'stocks'}`;
    const initials = name
      .split(/\s+/)
      .filter(Boolean)
      .map((x) => x[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'FC';

    const userName = $('.user-name');
    const userTier = $('.user-tier');
    const userAvatar = $('.user-avatar');
    if (userName) userName.textContent = name;
    if (userTier) userTier.textContent = tier;
    if (userAvatar) userAvatar.textContent = initials;

    const settingsName = $('#settings-name');
    const settingsEmail = $('#settings-email');
    if (settingsName) settingsName.value = name;
    if (settingsEmail) settingsEmail.value = state.currentUser.email;
  }

  function setAppPage(loggedIn) {
    const loginPage = $('#page-login');
    const appPage = $('#page-app');
    if (!loginPage || !appPage) return;
    loginPage.classList.toggle('active', !loggedIn);
    appPage.classList.toggle('active', loggedIn);
  }

  async function refreshPolicies() {
    const email = getCurrentEmail();
    if (!email) return;
    const response = await api(`/api/policies/${encodeURIComponent(email)}`);
    state.policies = (response.policies || []).map((p, idx) => ({
      id: `policy-${idx}`,
      title: p.title,
      value: p.value,
      active: !!p.enabled,
      description: defaultPolicyDescriptions[p.title] || p.value,
    }));
    renderPolicies();
  }

  async function savePolicies() {
    const email = getCurrentEmail();
    if (!email) return;
    await api('/api/policies', {
      method: 'POST',
      body: JSON.stringify({
        email,
        policies: state.policies.map((p) => ({ title: p.title, value: p.value || p.description || p.title, enabled: !!p.active })),
      }),
    });
  }

  async function refreshDashboard() {
    const email = getCurrentEmail();
    if (!email) return;
    const [dashboardResponse, tradesResponse] = await Promise.all([
      api(`/api/dashboard/${encodeURIComponent(email)}`),
      api(`/api/trades/${encodeURIComponent(email)}`),
    ]);
    state.dashboard = dashboardResponse.data;
    state.trades = tradesResponse.trades || [];
    renderDashboard();
    renderAssets();
    renderHistory();
  }

  async function refreshAgent() {
    const response = await api('/api/agent/status');
    state.agent = response.agent;
    renderAgentInSentinel();
  }

  async function refreshNotifications() {
    const email = getCurrentEmail();
    if (!email) return;
    const response = await api(`/api/notifications/${encodeURIComponent(email)}`);
    state.notifications = response.notifications || [];
    renderNotifications();
  }

  async function refreshAll() {
    if (!state.currentUser) return;
    await Promise.all([refreshPolicies(), refreshDashboard(), refreshAgent(), refreshNotifications()]);
    initDashboardCharts();
  }

  function renderDashboard() {
    if (!state.dashboard) return;

    const totalBalance = state.dashboard.total_balance ?? 0;
    const dailyChangePct = state.dashboard.daily_change_pct ?? 0;
    const holdings = state.dashboard.holdings || [];
    const recentTrades = state.dashboard.recent_trades || [];

    const portfolioValue = $('#portfolio-value');
    if (portfolioValue) portfolioValue.textContent = formatCurrency(totalBalance);

    const portfolioMetrics = $('.portfolio-metrics');
    if (portfolioMetrics) {
      const realized = state.trades.filter((t) => String(t.type).toLowerCase() === 'sell').reduce((sum, t) => sum + Number(t.amount || 0), 0);
      const unrealized = holdings.reduce((sum, h) => sum + Number(h.value || 0), 0);
      portfolioMetrics.innerHTML = `
        <div class="metric"><span class="metric-label">Market Status</span><span class="metric-value gold">${state.dashboard.market_status || 'Live'}</span></div>
        <div class="metric"><span class="metric-label">Daily Change</span><span class="metric-value ${dailyChangePct >= 0 ? 'positive' : 'negative'}">${formatPercent(dailyChangePct)}</span></div>
        <div class="metric"><span class="metric-label">Tracked Holdings</span><span class="metric-value">${holdings.length}</span></div>
        <div class="metric"><span class="metric-label">Recent Sell Volume</span><span class="metric-value ${realized >= 0 ? 'positive' : 'negative'}">${formatCurrency(realized)}</span></div>
        <div class="metric"><span class="metric-label">Current Holdings Value</span><span class="metric-value positive">${formatCurrency(unrealized)}</span></div>
        <div class="metric"><span class="metric-label">Recent Trades</span><span class="metric-value gold">${recentTrades.length}</span></div>
      `;
    }

    const primary = holdings[0] || { asset: 'AAPL', shares: 0, value: 0, change_pct: 0 };
    const primaryTicker = $('.asset-ticker');
    const primaryHolding = $('.asset-holding');
    if (primaryTicker && primaryTicker.closest('#card-primary-asset')) primaryTicker.textContent = primary.asset;
    if (primaryHolding) primaryHolding.textContent = `Holding: ${primary.shares} shares • ${formatCurrency(primary.value)}`;

    const ordersCount = $('.orders-count');
    const ordersMargin = $('.orders-margin');
    if (ordersCount) ordersCount.innerHTML = `${state.trades.length.toString().padStart(2, '0')} <span class="orders-label">RECENT</span>`;
    if (ordersMargin) ordersMargin.textContent = `Tracked trade notional: ${formatCurrency(state.trades.reduce((sum, t) => sum + Number(t.amount || 0), 0))}`;

    const activityList = $('#activity-list');
    if (activityList) {
      activityList.innerHTML = (recentTrades.length ? recentTrades : state.trades).slice(0, 5).map((trade) => {
        const type = String(trade.type || trade.trade_type || 'buy').toLowerCase();
        const icon = type === 'sell' ? 'south_west' : 'north_east';
        const cls = type === 'sell' ? 'sell' : 'buy';
        const meta = trade.date || trade.created_at || '';
        const reason = trade.reason || trade.execution_reason || 'Policy-validated execution';
        return `
          <div class="activity-item">
            <span class="material-symbols-outlined activity-icon ${cls}">${icon}</span>
            <div class="activity-details">
              <p class="activity-text">${type.toUpperCase()} ${trade.asset} • ${trade.amount}</p>
              <p class="activity-meta">${reason} • ${meta}</p>
            </div>
          </div>
        `;
      }).join('');
    }

    const gaugeValue = $('#gauge-value');
    if (gaugeValue) {
      const riskScore = Math.min(95, Math.max(15, 40 + Math.abs(dailyChangePct) * 5 + state.policies.filter((p) => p.active).length * 4));
      gaugeValue.textContent = `${Math.round(riskScore)}%`;
      const fill = $('#gauge-fill');
      if (fill) {
        const dash = 157;
        const offset = dash - dash * (riskScore / 100);
        fill.setAttribute('stroke-dashoffset', String(offset));
      }
    }

    drawDistributionChart();
    drawMiniChart();
  }

  function syncTradeAssetOptions() {
    const select = $('#trade-asset');
    if (!select) return;
    const previous = select.value;
    const assets = state.tradeAssets.length ? state.tradeAssets : ['AAPL', 'MSFT', 'NVDA'];
    select.innerHTML = assets.map((asset) => `<option value="${asset}">${asset} / USD</option>`).join('');
    if (assets.includes(previous)) select.value = previous;
  }

  function renderAssets() {
    const tbody = $('#assets-tbody');
    if (!tbody) return;
    const holdings = state.dashboard?.holdings || [];
    state.tradeAssets = Array.from(new Set([
      ...holdings.map((asset) => String(asset.asset || '').toUpperCase()).filter(Boolean),
      'AAPL',
      'MSFT',
      'NVDA',
    ]));
    syncTradeAssetOptions();
    const filtered = holdings.filter((asset) => {
      const term = state.assetSearch.toLowerCase();
      if (!term) return true;
      return String(asset.asset).toLowerCase().includes(term);
    });

    tbody.innerHTML = filtered.map((asset) => {
      const change = Number(asset.change_pct || 0);
      return `
        <tr>
          <td>
            <div class="asset-cell">
              <div class="asset-icon">${String(asset.asset).slice(0, 2)}</div>
              <div>
                <div class="asset-name-col">${asset.asset}</div>
                <div class="asset-symbol">LIVE</div>
              </div>
            </div>
          </td>
          <td>${formatCurrency(Number(asset.value || 0) / Math.max(Number(asset.shares || 1), 1))}</td>
          <td class="${change >= 0 ? 'change-positive' : 'change-negative'}">${formatPercent(change)}</td>
          <td>${asset.shares}</td>
          <td>${formatCurrency(asset.value)}</td>
          <td>
            <button class="trade-btn buy" data-action="buy" data-symbol="${asset.asset}">BUY</button>
            <button class="trade-btn sell" data-action="sell" data-symbol="${asset.asset}" style="margin-left:6px">SELL</button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.trade-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const symbol = btn.dataset.symbol;
        const action = btn.dataset.action;
        const tradeAsset = $('#trade-asset');
        if (tradeAsset) {
          const existing = Array.from(tradeAsset.options).find((o) => o.value === symbol);
          if (!existing) {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = `${symbol} / USD`;
            tradeAsset.appendChild(option);
          }
          tradeAsset.value = symbol;
        }
        $$('.trade-toggle').forEach((el) => el.classList.toggle('active', el.dataset.type === action));
        showToast(`${action.toUpperCase()} panel primed for ${symbol}`, 'info');
      });
    });
  }

  function renderPolicies() {
    const grid = $('#policies-grid');
    if (!grid) return;
    grid.innerHTML = state.policies.map((p, idx) => `
      <div class="policy-card" data-policy-id="${p.id || idx}">
        <h4 class="policy-title">${p.title}</h4>
        <p class="policy-desc">${p.description || p.value || 'Policy loaded from backend.'}</p>
        <div class="policy-toggle-row">
          <span class="policy-status ${p.active ? 'active' : 'inactive'}">${p.active ? 'ACTIVE' : 'INACTIVE'}</span>
          <div style="display:flex; gap:8px; align-items:center;">
            <button class="btn-text" data-remove-policy-index="${idx}" style="color:#ff8a80; font-size:12px;">Remove</button>
            <label class="toggle-switch">
              <input type="checkbox" data-policy-index="${idx}" ${p.active ? 'checked' : ''}>
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
    `).join('');

    grid.querySelectorAll('input[data-policy-index]').forEach((toggle) => {
      toggle.addEventListener('change', async () => {
        const index = Number(toggle.dataset.policyIndex);
        state.policies[index].active = toggle.checked;
        renderPolicies();
        try {
          await savePolicies();
          showToast(`Policy ${state.policies[index].title} ${toggle.checked ? 'enabled' : 'disabled'}.`, toggle.checked ? 'success' : 'warning');
        } catch (error) {
          state.policies[index].active = !toggle.checked;
          renderPolicies();
          showToast(error.message, 'error');
        }
      });
    });

    grid.querySelectorAll('[data-remove-policy-index]').forEach((button) => {
      button.addEventListener('click', async () => {
        const index = Number(button.dataset.removePolicyIndex);
        const [removed] = state.policies.splice(index, 1);
        renderPolicies();
        try {
          await savePolicies();
          showToast(`Policy ${removed.title} removed.`, 'warning');
        } catch (error) {
          state.policies.splice(index, 0, removed);
          renderPolicies();
          showToast(error.message, 'error');
        }
      });
    });
  }

  function renderHistory() {
    const list = $('#history-list');
    if (!list) return;
    const typeFilter = $('#history-type-filter')?.value || 'all';
    const trades = state.trades.filter((t) => typeFilter === 'all' || String(t.type || '').toLowerCase() === typeFilter);

    list.innerHTML = trades.length
      ? trades.map((t) => {
          const amount = Number(t.amount || 0);
          const positive = String(t.type || '').toLowerCase() === 'buy';
          return `
            <div class="history-item">
              <span class="history-type-badge ${String(t.type || '').toLowerCase()}">${t.type}</span>
              <div class="history-info">
                <p class="history-title">${t.type} ${t.asset} • ${formatCurrency(amount)}</p>
                <p class="history-meta">${t.execution_reason || 'Trade execution'} • ${t.created_at || ''}</p>
              </div>
              <span class="history-amount ${positive ? 'positive' : 'negative'}">${positive ? '+' : '-'}${formatCurrency(amount)}</span>
            </div>
          `;
        }).join('')
      : '<p style="padding:40px; text-align:center; color: rgba(229,226,225,0.3);">No transaction history yet.</p>';
  }

  function showPolicyAlert(notification) {
    state.selectedNotification = notification;
    const details = $('#policy-alert-details');
    if (details) {
      const relatedPolicies = state.policies
        .filter((policy) => notification.message.toLowerCase().includes(policy.title.toLowerCase().split(' ')[0]) || policy.active)
        .slice(0, 3)
        .map((policy) => `<div class="reg-detail-row"><span class="reg-detail-label">Policy</span><span class="reg-detail-value highlight">${policy.title}</span></div><div class="reg-detail-row"><span class="reg-detail-label">Rule</span><span class="reg-detail-value">${policy.description || policy.value}</span></div>`)
        .join('');
      details.innerHTML = `
        <div class="reg-detail-row"><span class="reg-detail-label">Decision</span><span class="reg-detail-value highlight">${notification.title}</span></div>
        <div class="reg-detail-row"><span class="reg-detail-label">Reason</span><span class="reg-detail-value">${notification.message}</span></div>
        <div class="reg-detail-row"><span class="reg-detail-label">Source</span><span class="reg-detail-value">${notification.source}</span></div>
        ${relatedPolicies || '<div class="reg-detail-row"><span class="reg-detail-label">Policy Context</span><span class="reg-detail-value">Review active FINCLAW policies for the exact enforcement rules.</span></div>'}
      `;
    }
    $('#modal-policy-alert')?.classList.remove('hidden');
  }

  function renderNotifications() {
    const list = $('#notification-list');
    const badge = $('.notif-badge');
    if (badge) badge.textContent = String(state.notifications.length || 0);
    if (!list) return;
    if (!state.notifications.length) {
      list.innerHTML = '<p style="padding: 24px; text-align: center; color: rgba(229,226,225,0.3); font-size: 13px;">No new notifications</p>';
      return;
    }
    list.innerHTML = state.notifications.map((item, index) => `
      <button class="notification-item ${item.read ? '' : 'unread'}" data-notification-index="${index}" style="width:100%; text-align:left; background:none; border:none;">
        <span class="material-symbols-outlined notif-icon">${item.level === 'warning' ? 'warning' : item.level === 'error' ? 'error' : item.level === 'success' ? 'check_circle' : 'info'}</span>
        <div class="notif-content">
          <p class="notif-text"><strong>${item.title}</strong> — ${item.message}</p>
          <p class="notif-time">${item.source} • ${item.created_at}</p>
        </div>
      </button>
    `).join('');

    list.querySelectorAll('[data-notification-index]').forEach((node) => {
      node.addEventListener('click', async () => {
        const item = state.notifications[Number(node.dataset.notificationIndex)];
        await refreshPolicies();
        showPolicyAlert(item);
      });
    });
  }

  function renderAgentInSentinel() {
    if (!state.agent) return;
    const subtitle = $('.sentinel-subtitle');
    if (subtitle) subtitle.textContent = `AI Risk Advisor • ${state.agent.running ? 'Automation running' : 'Automation idle'}`;

    const threats = $$('.threat-value');
    if (threats[0]) threats[0].textContent = `${state.agent.running ? 72 : 18}%`;
    if (threats[1]) threats[1].textContent = `${state.agent.last_error ? 61 : 94}%`;

    const riskTitle = $('.sentinel-risk-title');
    if (riskTitle) riskTitle.textContent = `Agent • ${state.agent.strategy_name || 'paper-sim'}`;
  }

  function drawMiniChart() {
    const container = $('#btc-chart');
    if (!container) return;
    const points = (state.dashboard?.holdings || []).map((h) => Number(h.value || 0));
    const series = points.length >= 3 ? points : [420, 460, 430, 510, 530, 520];

    const canvas = document.createElement('canvas');
    canvas.width = container.offsetWidth || 280;
    canvas.height = container.offsetHeight || 80;
    container.innerHTML = '';
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min || 1;

    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, 'rgba(227, 27, 35, 0.25)');
    gradient.addColorStop(1, 'rgba(227, 27, 35, 0)');

    ctx.beginPath();
    series.forEach((p, i) => {
      const x = (i / (series.length - 1)) * w;
      const y = h - ((p - min) / range) * h * 0.8 - h * 0.1;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    series.forEach((p, i) => {
      const x = (i / (series.length - 1)) * w;
      const y = h - ((p - min) / range) * h * 0.8 - h * 0.1;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#E31B23';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function drawDistributionChart() {
    const container = $('#distribution-chart');
    const legend = $('#distribution-legend');
    if (!container || !legend) return;
    const holdings = state.dashboard?.holdings || [];
    const total = holdings.reduce((sum, h) => sum + Number(h.value || 0), 0) || 1;
    const palette = ['#E31B23', '#627EEA', '#9945FF', '#26A17B', '#EAC349', '#4A4949'];
    const data = holdings.map((h, i) => ({
      label: h.asset,
      value: (Number(h.value || 0) / total) * 100,
      color: palette[i % palette.length],
    }));

    const size = 100;
    const cx = size / 2;
    const cy = size / 2;
    const r = 38;
    let cumAngle = -Math.PI / 2;
    let svg = '';
    data.forEach((d) => {
      const angle = (d.value / 100) * Math.PI * 2;
      const x1 = cx + r * Math.cos(cumAngle);
      const y1 = cy + r * Math.sin(cumAngle);
      cumAngle += angle;
      const x2 = cx + r * Math.cos(cumAngle);
      const y2 = cy + r * Math.sin(cumAngle);
      const largeArc = angle > Math.PI ? 1 : 0;
      svg += `<path d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z" fill="${d.color}" opacity="0.85"/>`;
    });

    container.innerHTML = `<svg viewBox="0 0 ${size} ${size}" style="width:${size}px;height:${size}px">${svg}<circle cx="${cx}" cy="${cy}" r="22" fill="#201F1F"/></svg>`;
    legend.innerHTML = data.map((d) => `<div class="legend-item"><span class="legend-dot" style="background:${d.color}"></span>${d.label} ${d.value.toFixed(1)}%</div>`).join('');
  }

  function initTerminalChart(force = false) {
    const container = $('#terminal-main-chart');
    if (!container) return;
    const initialized = container.getAttribute('data-initialized') === 'true';
    if (!force && initialized) return;
    container.setAttribute('data-initialized', 'true');
    container.style.position = 'relative';
    container.innerHTML = '';

    const canvas = document.createElement('canvas');
    canvas.width = container.offsetWidth || 800;
    canvas.height = container.offsetHeight || 500;
    container.appendChild(canvas);

    const tooltip = document.createElement('div');
    tooltip.className = 'chart-tooltip';
    Object.assign(tooltip.style, {
      position: 'absolute',
      pointerEvents: 'none',
      background: 'rgba(12, 12, 12, 0.95)',
      border: '1px solid var(--accent-cyan)',
      color: 'var(--text-primary)',
      padding: '12px 16px',
      borderRadius: '6px',
      fontSize: '12px',
      fontFamily: 'var(--font-mono)',
      boxShadow: '0 4px 16px rgba(0, 255, 255, 0.15)',
      display: 'none',
      zIndex: '100',
    });
    container.appendChild(tooltip);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const base = Number(state.trades[0]?.amount || 100);
    const candles = [];
    let price = Math.max(50, base);
    for (let i = 0; i < 40; i += 1) {
      const open = price;
      const close = open + (Math.random() - 0.45) * 12;
      const high = Math.max(open, close) + Math.random() * 6;
      const low = Math.min(open, close) - Math.random() * 6;
      candles.push({ open, close, high, low });
      price = close;
    }

    const min = Math.min(...candles.map((c) => c.low));
    const max = Math.max(...candles.map((c) => c.high));
    const range = max - min || 1;
    const spacing = w / candles.length;
    const candleWidth = spacing * 0.6;

    candles.forEach((c, i) => {
      const x = i * spacing + spacing / 2;
      const yOpen = h - ((c.open - min) / range) * h * 0.9 - h * 0.05;
      const yClose = h - ((c.close - min) / range) * h * 0.9 - h * 0.05;
      const yHigh = h - ((c.high - min) / range) * h * 0.9 - h * 0.05;
      const yLow = h - ((c.low - min) / range) * h * 0.9 - h * 0.05;
      const up = c.close >= c.open;
      const color = up ? '#4CAF50' : '#E31B23';
      ctx.beginPath();
      ctx.moveTo(x, yHigh);
      ctx.lineTo(x, yLow);
      ctx.strokeStyle = color;
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.fillRect(x - candleWidth / 2, Math.min(yOpen, yClose), candleWidth, Math.max(1, Math.abs(yOpen - yClose)));
    });

    canvas.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const idx = Math.floor(x / spacing);
      if (idx < 0 || idx >= candles.length) return;
      const c = candles[idx];
      tooltip.style.display = 'block';
      tooltip.innerHTML = `
        <div style="font-family: var(--font-sans); font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px;">Live trade curve</div>
        <div style="font-weight: 700; color: var(--accent-cyan); margin-bottom: 8px; font-size: 14px;">${formatCurrency(c.close)}</div>
        <div>O: ${c.open.toFixed(2)}</div>
        <div>H: ${c.high.toFixed(2)}</div>
        <div>L: ${c.low.toFixed(2)}</div>
        <div>C: ${c.close.toFixed(2)}</div>
      `;
      tooltip.style.left = `${Math.min(w - 180, x + 15)}px`;
      tooltip.style.top = `${Math.min(h - 120, e.clientY - rect.top + 15)}px`;
    });
    canvas.addEventListener('mouseleave', () => (tooltip.style.display = 'none'));
  }

  function initDashboardCharts() {
    drawMiniChart();
    drawDistributionChart();
    initTerminalChart(true);
  }

  async function doLogin() {
    const email = $('#login-username').value.trim();
    const password = $('#login-password').value.trim();
    if (!email) return showToast('Identity identifier is required.', 'error');
    if (!password) return showToast('Security credential is required.', 'error');

    const btn = $('#btn-login');
    const original = btn.innerHTML;
    btn.innerHTML = 'INITIALIZING...';
    btn.disabled = true;
    try {
      const response = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      rememberUser({ ...response.user, email, displayName: email.split('@')[0] });
      syncUserUI();
      setAppPage(true);
      await refreshAll();
      showToast('Terminal initialized.', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      btn.innerHTML = original;
      btn.disabled = false;
    }
  }

  async function doRegister() {
    const name = $('#reg-fullname').value.trim();
    const email = $('#reg-email').value.trim();
    const password = $('#reg-password').value.trim();
    const experience = document.querySelector('#exp-level-cards .exp-card.selected')?.dataset.value || 'beginner';
    const portfolioSize = document.querySelector('#exp-portfolio-cards .exp-card.selected')?.dataset.value || 'small';
    const riskSlider = $('#exp-risk-slider');
    const riskMap = { 1: 'low', 2: 'low', 3: 'medium', 4: 'high', 5: 'high' };
    const risk = riskMap[riskSlider ? Number(riskSlider.value) : 3] || 'medium';

    if (!name || !email || !password) {
      showToast('Complete registration details first.', 'error');
      return;
    }

    await api('/api/auth/onboarding', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        goal: 'growth',
        experience,
        risk,
        asset: portfolioSize,
      }),
    });

    const selectedPolicies = $$('#policy-suggest-list input[type="checkbox"]:checked').map((toggle) => ({
      title: toggle.closest('.policy-suggest-item')?.querySelector('.policy-suggest-name')?.textContent || 'Custom Policy',
      value: toggle.closest('.policy-suggest-item')?.querySelector('.policy-suggest-reason')?.textContent || 'User-selected policy',
      enabled: true,
    }));

    await api('/api/policies', {
      method: 'POST',
      body: JSON.stringify({ email, policies: selectedPolicies }),
    });

    rememberUser({ email, displayName: name, risk, asset: portfolioSize, experience });
    syncUserUI();
    showToast('Registration complete. You can log in now.', 'success');
  }

  async function executeTrade() {
    const email = getCurrentEmail();
    if (!email) {
      showToast('Please log in first.', 'error');
      return;
    }

    const asset = $('#trade-asset')?.value;
    const amount = Number($('#trade-amount')?.value || 0);
    const type = document.querySelector('.trade-toggle.active')?.dataset.type || 'buy';
    if (!asset || amount <= 0) {
      showToast('Please enter a valid amount to trade.', 'error');
      return;
    }

    const btn = $('#btn-execute-trade');
    const original = btn.innerHTML;
    btn.innerHTML = 'EXECUTING...';
    btn.disabled = true;
    try {
      const response = await api('/api/trade-intents', {
        method: 'POST',
        body: JSON.stringify({
          user_email: email,
          ticker: asset,
          side: type,
          notional_usd: amount,
          quantity: 1,
          reason: `Frontend ${type} execution from ArmorClaw terminal`,
          source: 'frontend',
          asset_class: asset.includes('USD') ? 'crypto' : 'equity',
          mode: 'paper',
        }),
      });
      const mode = response?.broker_result?.mode || 'paper';
      showToast(`Trade allowed via ${mode}: ${response.reason}`, 'success');
      $('#trade-amount').value = '';
      await refreshDashboard();
      await refreshNotifications();
    } catch (error) {
      showToast(error.message, 'error');
      await refreshNotifications();
    } finally {
      btn.innerHTML = original;
      btn.disabled = false;
    }
  }

  async function controlAgent(action) {
    const email = getCurrentEmail();
    try {
      if (action === 'configure' && email) {
        await api('/api/agent/configure', {
          method: 'POST',
          body: JSON.stringify({ user_email: email, tickers: ['AAPL', 'MSFT', 'NVDA'], loop_interval_seconds: 15 }),
        });
      } else if (action === 'run-once') {
        await api('/api/agent/run-once', { method: 'POST' });
      } else if (action === 'start') {
        await api('/api/agent/start', { method: 'POST' });
      } else if (action === 'stop') {
        await api('/api/agent/stop', { method: 'POST' });
      }
      await refreshAgent();
      await refreshDashboard();
      await refreshNotifications();
      showToast(`Agent ${action} completed.`, 'success');
    } catch (error) {
      showToast(error.message, 'error');
    }
  }

  async function applyArmoriqActions(actions = []) {
    for (const action of actions) {
      if (action.kind === 'view' && action.target) {
        const nav = $(`#nav-${action.target}`);
        const view = $(`#view-${action.target}`);
        if (nav && view) {
          $$('.nav-item').forEach((n) => n.classList.remove('active'));
          nav.classList.add('active');
          $$('.view').forEach((v) => v.classList.remove('active'));
          view.classList.add('active');
        }
      }

      if (action.kind === 'highlight_assets' && Array.isArray(action.assets)) {
        state.tradeAssets = Array.from(new Set(action.assets.map((item) => String(item).toUpperCase())));
        syncTradeAssetOptions();
        renderAssets();
      }

      if (action.kind === 'trade_ticket' && action.trade) {
        const trade = action.trade;
        const ticketView = $('#view-terminal');
        const terminalTab = $('#tab-terminal');
        if (terminalTab && ticketView) {
          $$('.topbar-tab').forEach((t) => t.classList.remove('active'));
          terminalTab.classList.add('active');
          $$('.view').forEach((v) => v.classList.remove('active'));
          ticketView.classList.add('active');
        }
        const tradeAsset = $('#trade-asset');
        if (tradeAsset) {
          if (!Array.from(tradeAsset.options).find((o) => o.value === trade.ticker)) {
            const option = document.createElement('option');
            option.value = trade.ticker;
            option.textContent = `${trade.ticker} / USD`;
            tradeAsset.appendChild(option);
          }
          tradeAsset.value = trade.ticker;
        }
        const amountInput = $('#trade-amount');
        if (amountInput) amountInput.value = trade.notional_usd;
        $$('.trade-toggle').forEach((el) => el.classList.toggle('active', el.dataset.type === trade.side));
      }

      if (action.kind === 'agent' && action.status === 'ready' && action.command) {
        await controlAgent(action.command);
      }
    }
  }

  function bindEvents() {
    $('#btn-login')?.addEventListener('click', doLogin);
    $('#login-password')?.addEventListener('keydown', (e) => e.key === 'Enter' && doLogin());
    $('#login-username')?.addEventListener('keydown', (e) => e.key === 'Enter' && $('#login-password')?.focus());

    $('#btn-toggle-password')?.addEventListener('click', () => {
      const input = $('#login-password');
      const icon = $('#btn-toggle-password .material-symbols-outlined');
      const visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      if (icon) icon.textContent = visible ? 'visibility_off' : 'visibility';
    });

    $('#btn-forgot')?.addEventListener('click', () => $('#modal-forgot')?.classList.remove('hidden'));
    $('#btn-close-forgot')?.addEventListener('click', () => $('#modal-forgot')?.classList.add('hidden'));
    $('#btn-close-policy-alert')?.addEventListener('click', () => $('#modal-policy-alert')?.classList.add('hidden'));
    $('#btn-open-policies-from-alert')?.addEventListener('click', async () => {
      $('#modal-policy-alert')?.classList.add('hidden');
      await refreshPolicies();
      $$('.nav-item').forEach((n) => n.classList.remove('active'));
      $('#nav-policies')?.classList.add('active');
      $$('.view').forEach((v) => v.classList.remove('active'));
      $('#view-policies')?.classList.add('active');
      const violationList = $('#violation-list');
      if (violationList && state.selectedNotification) {
        violationList.innerHTML = `
          <div class="violation-item warning">
            <div class="violation-header"><span class="material-symbols-outlined">warning</span><span class="violation-name">ArmorIQ Decision</span></div>
          </div>
          <div class="violation-item">
            <div class="violation-header"><span class="violation-name">${state.selectedNotification.title}</span><span class="violation-time">just now</span></div>
            <p class="violation-detail">${state.selectedNotification.message}</p>
          </div>
          ${state.policies.slice(0, 3).map((policy) => `
            <div class="violation-item">
              <div class="violation-header"><span class="violation-name">${policy.title}</span><span class="violation-time">policy</span></div>
              <p class="violation-detail">${policy.description || policy.value}</p>
            </div>
          `).join('')}
        `;
      }
    });
    $('#btn-submit-forgot')?.addEventListener('click', () => {
      const email = $('#forgot-email').value.trim();
      if (!email.includes('@')) return showToast('Valid email required.', 'error');
      $('#modal-forgot').classList.add('hidden');
      showToast(`Reset link prepared for ${email}`, 'success');
    });

    $('#btn-request-access')?.addEventListener('click', () => $('#modal-register')?.classList.remove('hidden'));
    $('#btn-close-register')?.addEventListener('click', () => $('#modal-register')?.classList.add('hidden'));

    $$('.modal-overlay').forEach((overlay) => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.add('hidden');
      });
    });

    let regStep = 1;
    const goToRegStep = (step) => {
      regStep = step;
      $$('.reg-step-panel').forEach((panel) => panel.classList.remove('active'));
      $(`#reg-step-${step}`)?.classList.add('active');
      const dots = $$('.reg-step-dot');
      const lines = $$('.reg-step-line');
      dots.forEach((dot) => {
        const s = Number(dot.dataset.step);
        dot.classList.remove('active', 'done');
        if (s === step) dot.classList.add('active');
        else if (s < step) dot.classList.add('done');
      });
      lines.forEach((line, idx) => line.classList.toggle('done', idx < step - 1));
    };

    $('#btn-reg-next-1')?.addEventListener('click', () => {
      const name = $('#reg-fullname').value.trim();
      const email = $('#reg-email').value.trim();
      const pw = $('#reg-password').value.trim();
      if (!name || !email.includes('@') || pw.length < 8) return showToast('Complete valid identity details first.', 'error');
      goToRegStep(2);
    });
    $('#btn-reg-back-2')?.addEventListener('click', () => goToRegStep(1));
    $('#btn-reg-back-3')?.addEventListener('click', () => goToRegStep(2));

    $$('#exp-level-cards .exp-card').forEach((card) => card.addEventListener('click', () => {
      $$('#exp-level-cards .exp-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
    }));
    $$('#exp-portfolio-cards .exp-card').forEach((card) => card.addEventListener('click', () => {
      $$('#exp-portfolio-cards .exp-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
    }));
    $$('#exp-instruments .exp-chip').forEach((chip) => chip.addEventListener('click', () => chip.classList.toggle('selected')));

    $('#btn-reg-next-2')?.addEventListener('click', () => {
      const experience = document.querySelector('#exp-level-cards .exp-card.selected')?.dataset.value || 'beginner';
      const profile = $('#policy-suggest-profile');
      const list = $('#policy-suggest-list');
      const policyMap = {
        beginner: [
          ['Maximum Trade Size Limit', 'Cap each order size for safety', true],
          ['No Leverage or Margin Trades', 'Prevents amplified downside risk', true],
          ['Allowed Assets Only', 'Restrict to approved universe', true],
        ],
        intermediate: [
          ['Maximum Trade Size Limit', 'Balanced notional guardrail', true],
          ['Risk Exposure Cap', 'Limit aggregate portfolio exposure', true],
          ['Allowed Assets Only', 'Universe restriction for safe paper trading', true],
        ],
        advanced: [
          ['Risk Exposure Cap', 'Controls open risk budget', true],
          ['Market Hours Enforcement', 'Protects outside active windows', false],
          ['Allowed Assets Only', 'Execution whitelist', true],
        ],
        expert: [
          ['Risk Exposure Cap', 'Institutional-style position cap', true],
          ['Market Hours Enforcement', 'Operational window control', true],
          ['Allowed Assets Only', 'Execution whitelist', true],
        ],
      };
      const items = policyMap[experience] || policyMap.beginner;
      if (profile) profile.innerHTML = `<div class="profile-badge level"><span class="material-symbols-outlined">military_tech</span>${experience}</div>`;
      if (list) list.innerHTML = items.map(([name, reason, enabled], idx) => `
        <div class="policy-suggest-item recommended">
          <div class="policy-suggest-info">
            <div class="policy-suggest-name">${name}</div>
            <div class="policy-suggest-reason">${reason}</div>
          </div>
          <span class="policy-suggest-tag recommended">recommended</span>
          <div class="policy-suggest-toggle">
            <label class="toggle-switch">
              <input type="checkbox" ${enabled ? 'checked' : ''} data-policy-suggest="${idx}">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      `).join('');
      goToRegStep(3);
    });

    $('#btn-reg-next-3')?.addEventListener('click', async () => {
      try {
        await doRegister();
        const details = $('#reg-success-details');
        if (details) {
          details.innerHTML = `
            <div class="reg-detail-row"><span class="reg-detail-label">Identity</span><span class="reg-detail-value">${$('#reg-fullname').value.trim()}</span></div>
            <div class="reg-detail-row"><span class="reg-detail-label">Policies Applied</span><span class="reg-detail-value highlight">${$$('#policy-suggest-list input:checked').length} active</span></div>
            <div class="reg-detail-row"><span class="reg-detail-label">Backend</span><span class="reg-detail-value highlight">${state.apiBase}</span></div>
          `;
        }
        goToRegStep(4);
      } catch (error) {
        showToast(error.message, 'error');
      }
    });

    $('#btn-reg-finish')?.addEventListener('click', () => {
      $('#modal-register')?.classList.add('hidden');
      $('#login-username').value = getCurrentEmail();
      goToRegStep(1);
    });

    $$('.nav-item').forEach((item) => {
      item.addEventListener('click', async () => {
        const page = item.dataset.page;
        $$('.nav-item').forEach((n) => n.classList.remove('active'));
        item.classList.add('active');
        $$('.view').forEach((v) => v.classList.remove('active'));
        $(`#view-${page}`)?.classList.add('active');
        if (page === 'history') renderHistory();
        if (page === 'assets') renderAssets();
      });
    });

    $$('.topbar-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        const viewTarget = tabName === 'markets' ? 'dashboard' : tabName;
        $$('.topbar-tab').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        $$('.view').forEach((v) => v.classList.remove('active'));
        $(`#view-${viewTarget}`)?.classList.add('active');
        if (tabName === 'terminal') initTerminalChart(true);
      });
    });

    $('#btn-logout')?.addEventListener('click', () => {
      localStorage.removeItem('finclaw.currentUser');
      state.currentUser = null;
      setAppPage(false);
      showToast('Terminal session terminated.', 'info');
    });

    $('#btn-execute-trade')?.addEventListener('click', executeTrade);
    $$('.trade-toggle').forEach((toggle) => toggle.addEventListener('click', () => {
      $$('.trade-toggle').forEach((t) => t.classList.remove('active'));
      toggle.classList.add('active');
    }));

    $('#asset-search')?.addEventListener('input', (e) => {
      state.assetSearch = e.target.value || '';
      renderAssets();
    });
    $('#btn-add-asset')?.addEventListener('click', () => showToast('Assets are sourced from backend portfolio data.', 'info'));

    $('#history-type-filter')?.addEventListener('change', renderHistory);
    $('#history-time-filter')?.addEventListener('change', renderHistory);

    $('#btn-add-policy')?.addEventListener('click', async () => {
      const title = $('#custom-policy-title')?.value?.trim();
      const value = $('#custom-policy-value')?.value?.trim();
      if (!title || !value) return showToast('Enter both policy title and rule.', 'error');
      state.policies.unshift({
        id: `policy-${Date.now()}`,
        title,
        value,
        active: true,
        description: value,
      });
      renderPolicies();
      try {
        await savePolicies();
        $('#custom-policy-title').value = '';
        $('#custom-policy-value').value = '';
        showToast(`Policy ${title} added.`, 'success');
      } catch (error) {
        state.policies.shift();
        renderPolicies();
        showToast(error.message, 'error');
      }
    });

    $('#btn-save-profile')?.addEventListener('click', () => {
      if (!state.currentUser) return;
      state.currentUser.displayName = $('#settings-name').value.trim() || state.currentUser.displayName;
      rememberUser(state.currentUser);
      syncUserUI();
      showToast('Profile updated locally.', 'success');
    });
    $('#btn-save-security')?.addEventListener('click', () => showToast('Security settings saved locally.', 'success'));
    $('#btn-save-notifications')?.addEventListener('click', () => showToast('Notification preferences saved locally.', 'success'));

    $('#btn-sentinel')?.addEventListener('click', () => $('#sentinel-panel')?.classList.toggle('open'));
    $('#btn-close-sentinel')?.addEventListener('click', () => $('#sentinel-panel')?.classList.remove('open'));
    $('#btn-live-chat')?.addEventListener('click', () => $('#sentinel-panel')?.classList.add('open'));
    $('#btn-docs')?.addEventListener('click', () => showToast('Docs are available in the repository docs/ folder.', 'info'));
    $('#btn-report-issue')?.addEventListener('click', () => showToast('Issue reporting can be added next, but app is now usable.', 'info'));
    $('#btn-training')?.addEventListener('click', () => showToast('Training module is not connected yet.', 'info'));

    $('#btn-notifications')?.addEventListener('click', (e) => {
      e.stopPropagation();
      $('#notification-dropdown')?.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
      const notif = $('#notification-dropdown');
      const btn = $('#btn-notifications');
      if (notif && btn && !notif.contains(e.target) && e.target !== btn) notif.classList.add('hidden');
    });
    $('#btn-clear-notifs')?.addEventListener('click', () => {
      const list = $('#notification-list');
      if (list) list.innerHTML = '<p style="padding: 24px; text-align: center; color: rgba(229,226,225,0.3); font-size: 13px;">No new notifications</p>';
      showToast('Notifications cleared.', 'info');
    });

    $('#btn-fullscreen')?.addEventListener('click', async () => {
      const icon = $('#btn-fullscreen .material-symbols-outlined');
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
        if (icon) icon.textContent = 'fullscreen_exit';
      } else {
        await document.exitFullscreen();
        if (icon) icon.textContent = 'fullscreen';
      }
    });

    $('#btn-sentinel-send')?.addEventListener('click', async () => {
      const input = $('#sentinel-input');
      const text = input.value.trim();
      if (!text) return;
      const messages = $('#sentinel-messages');
      messages.insertAdjacentHTML('beforeend', `<div class="sentinel-msg user"><div class="sentinel-msg-avatar"><span class="material-symbols-outlined">person</span></div><div class="sentinel-msg-content"><p>${text}</p></div></div>`);
      input.value = '';

      let reply = 'ArmorIQ is online and operating as a FINCLAW controller.';
      try {
        const normalized = text.toLowerCase();
        const response = await api('/api/armoriq', {
          method: 'POST',
          body: JSON.stringify({
            message: text,
            email: getCurrentEmail() || null,
            auto_execute: normalized.includes('run once') || normalized.includes('scan market') || normalized.includes('start automation') || normalized.includes('start agent') || normalized.includes('stop automation') || normalized.includes('stop agent'),
          }),
        });
        reply = response.reply || reply;
        await applyArmoriqActions(response.actions || []);
        if (response.context?.agent) {
          state.agent = response.context.agent;
          if (state.agent?.last_decision?.allowed === false && state.agent?.last_decision?.rationale) {
            reply += ` Latest automation result: blocked — ${state.agent.last_decision.rationale}.`;
          }
        }
        await refreshDashboard();
        await refreshNotifications();
      } catch {
        try {
          const fallback = await api('/api/chat', { method: 'POST', body: JSON.stringify({ message: text, email: getCurrentEmail() || null }) });
          reply = fallback.reply || reply;
        } catch {}
      }

      messages.insertAdjacentHTML('beforeend', `<div class="sentinel-msg bot"><div class="sentinel-msg-avatar"><span class="material-symbols-outlined">smart_toy</span></div><div class="sentinel-msg-content"><p>${reply}</p></div></div>`);
      messages.scrollTop = messages.scrollHeight;
    });
    $('#sentinel-input')?.addEventListener('keydown', (e) => e.key === 'Enter' && $('#btn-sentinel-send')?.click());

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        $('#sentinel-panel')?.classList.remove('open');
        $('#notification-dropdown')?.classList.add('hidden');
        $$('.modal-overlay').forEach((m) => m.classList.add('hidden'));
      }
      if (e.ctrlKey && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        $('#sentinel-panel')?.classList.toggle('open');
        $('#sentinel-input')?.focus();
      }
    });
  }

  async function boot() {
    loadRememberedUser();
    bindEvents();
    syncTradeAssetOptions();
    syncUserUI();
    if (state.currentUser) {
      setAppPage(true);
      try {
        await refreshAll();
      } catch (error) {
        showToast(`Backend connection issue: ${error.message}`, 'warning');
      }
    } else {
      setAppPage(false);
    }
  }

  boot();
})();
