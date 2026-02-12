/**
 * Smart Campus Store — Frontend Application
 * Handles all dashboard pages, charts, barcode scanning, and ML insights.
 */

const API = '';  // Same origin

// ═══════════════════════════════════════
// STATE & INIT
// ═══════════════════════════════════════

let charts = {};
let html5QrCode = null;
let invQrCode = null;
let productsCache = [];
let _dashboardStale = false;

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initClock();
    initSearch();
    initNotifications();
    initModals();
    initPOSForm();
    initScanner();
    initInventoryScanner();
    loadDashboard();
    loadCategories();

    // ── Real-time Sync ──
    initBroadcastSync();
});

// ── Broadcast Channel for Cross-Tab Sync ──
const appBus = new BroadcastChannel('app_sync');

function initBroadcastSync() {
    // Listen for updates from other tabs/actions
    appBus.onmessage = (event) => {
        if (event.data.type === 'INVENTORY_UPDATE') {
            console.log('🔄 Received sync event: updating data...');
            refreshKPIs();

            // Reload current active page data if applicable
            const activePage = document.querySelector('.page.active');
            if (activePage) {
                // page-dashboard -> dashboard
                const pageId = activePage.id.replace('page-', '');
                switch (pageId) {
                    case 'inventory': loadInventory(); break;
                    case 'dashboard': loadDashboard(); break; // kpis already refreshed but charts need reload
                    case 'expiry': loadExpiry(); break;
                    case 'pos': loadPOS(); break; // refresh product list to remove 0 stock items
                    case 'analytics': loadAnalytics(); break;
                }
            }
        }
    };
}

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════

function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            switchPage(page);
        });
    });

    // Mobile toggle
    const toggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
}

function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    document.getElementById(`page-${page}`).classList.add('active');
    document.querySelector(`[data-page="${page}"]`).classList.add('active');

    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('open');

    // Load page data
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'inventory': loadInventory(); break;
        case 'expiry': loadExpiry(); break;
        case 'pos': loadPOS(); break;
        case 'analytics': loadAnalytics(); break;
        case 'scanner': loadBarcodeDirectory(); break;
        case 'ml': loadMLInsights(); break;
    }
}

// ═══════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════

function initClock() {
    const update = () => {
        const now = new Date();
        document.getElementById('current-time').textContent = now.toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit'
        });
    };
    update();
    setInterval(update, 30000);
}

function initSearch() {
    const searchInput = document.getElementById('global-search');
    let timeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const q = searchInput.value.trim();
            if (q.length >= 2) {
                switchPage('inventory');
                loadInventory(q);
            }
        }, 400);
    });
}

function formatCurrency(val) {
    if (val === undefined || val === null) return '₹0';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2
    }).format(val);
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

async function apiFetch(url, options = {}) {
    try {
        const res = await fetch(API + url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// ═══════════════════════════════════════
// NOTIFICATIONS (dismissible)
// ═══════════════════════════════════════

const DISMISSED_STORAGE_KEY = 'campus_dismissed_notifs';
const DISMISS_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

// ── Dismissed-state helpers (localStorage) ──

function getDismissedNotifs() {
    try {
        const raw = localStorage.getItem(DISMISSED_STORAGE_KEY);
        if (!raw) return {};
        const data = JSON.parse(raw);
        // Purge entries older than 24 h so stale IDs don't pile up
        const now = Date.now();
        const cleaned = {};
        for (const [id, ts] of Object.entries(data)) {
            if (now - ts < DISMISS_EXPIRY_MS) cleaned[id] = ts;
        }
        if (Object.keys(cleaned).length !== Object.keys(data).length) {
            localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify(cleaned));
        }
        return cleaned;
    } catch { return {}; }
}

function dismissNotif(id) {
    const dismissed = getDismissedNotifs();
    dismissed[id] = Date.now();
    localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify(dismissed));
}

function clearAllDismissed() {
    localStorage.removeItem(DISMISSED_STORAGE_KEY);
}

function dismissAllNotifs(ids) {
    const dismissed = getDismissedNotifs();
    const now = Date.now();
    ids.forEach(id => { dismissed[id] = now; });
    localStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify(dismissed));
}

// ── Generate a unique ID per notification ──

function notifId(type, alert) {
    if (type === 'expiry') return `exp-${alert.batch_number}-${alert.item_id}`;
    return `stk-${alert.item_id || alert.product_name}`;
}

// ── Keep a module-level ref so we can re-render after dismiss ──
let _lastDashboardData = null;

// ── Init ──

function initNotifications() {
    const bell = document.getElementById('notification-bell');
    const dropdown = document.getElementById('notification-dropdown');

    bell.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && !bell.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') dropdown.classList.remove('open');
    });
}

// ── Update (called from loadDashboard) ──

function updateNotifications(dashboardData) {
    _lastDashboardData = dashboardData;
    renderNotificationList();
}

function renderNotificationList() {
    const badge = document.getElementById('alert-badge');
    const countEl = document.getElementById('notif-count');
    const list = document.getElementById('notification-list');

    if (!_lastDashboardData) return;

    const dismissed = getDismissedNotifs();
    const expiryAlerts = (_lastDashboardData.expiry_alerts || [])
        .filter(a => !dismissed[notifId('expiry', a)]);
    const stockAlerts = (_lastDashboardData.stock_alerts || [])
        .filter(a => !dismissed[notifId('stock', a)]);
    const totalAlerts = expiryAlerts.length + stockAlerts.length;

    // Badge
    if (totalAlerts > 0) {
        badge.textContent = totalAlerts > 99 ? '99+' : totalAlerts;
        badge.classList.add('has-alerts');
    } else {
        badge.textContent = '';
        badge.classList.remove('has-alerts');
    }

    // Header count
    countEl.textContent = totalAlerts === 0
        ? 'All clear'
        : `${totalAlerts} alert${totalAlerts !== 1 ? 's' : ''}`;

    // Empty state
    if (totalAlerts === 0) {
        list.innerHTML = `
            <li class="empty-state">
                <span class="notif-empty-icon">🎉</span>
                No new alerts — all clear!
            </li>`;
        return;
    }

    let html = '';

    // Expiry notifications
    expiryAlerts.slice(0, 15).forEach(a => {
        const id = notifId('expiry', a);
        let icon = '⚠️', cssClass = 'notif-warning';
        if (a.status === 'expired') { icon = '⛔'; cssClass = 'notif-expired'; }
        else if (a.status === 'critical') { icon = '🔴'; cssClass = 'notif-critical'; }

        const timeText = a.days_left <= 0
            ? `Expired ${Math.abs(a.days_left)}d ago`
            : `${a.days_left} day${a.days_left !== 1 ? 's' : ''} left`;

        html += `
            <li class="${cssClass}" data-notif-id="${id}" onclick="handleNotifClick(this, '${id}', 'expiry')">
                <span class="notif-icon">${icon}</span>
                <div class="notif-body">
                    <span class="notif-title">${a.product_name}</span>
                    <span class="notif-detail">${timeText} · Batch: ${a.batch_number} · ${a.quantity} units</span>
                </div>
                <span class="notif-dismiss" title="Dismiss" onclick="event.stopPropagation(); dismissSingleNotif(this, '${id}')">✕</span>
            </li>`;
    });

    // Stock notifications
    stockAlerts.slice(0, 10).forEach(a => {
        const id = notifId('stock', a);
        html += `
            <li class="notif-lowstock" data-notif-id="${id}" onclick="handleNotifClick(this, '${id}', 'inventory')">
                <span class="notif-icon">📉</span>
                <div class="notif-body">
                    <span class="notif-title">${a.product_name}</span>
                    <span class="notif-detail">Stock: ${a.current_stock} / Min: ${a.min_stock} · ${a.category}</span>
                </div>
                <span class="notif-dismiss" title="Dismiss" onclick="event.stopPropagation(); dismissSingleNotif(this, '${id}')">✕</span>
            </li>`;
    });

    list.innerHTML = html;
}

// ── Dismiss a single notification (✕ button) ──

function dismissSingleNotif(btn, id) {
    const li = btn.closest('li');
    li.classList.add('notif-slide-out');
    li.addEventListener('animationend', () => {
        dismissNotif(id);
        renderNotificationList();
    }, { once: true });
}

// ── Click a notification → dismiss + navigate ──

function handleNotifClick(el, id, page) {
    dismissNotif(id);
    el.classList.add('notif-slide-out');
    el.addEventListener('animationend', () => {
        renderNotificationList();
        document.getElementById('notification-dropdown').classList.remove('open');
        switchPage(page);
    }, { once: true });
}

// ── Clear All button ──

function clearAllNotifications() {
    if (!_lastDashboardData) return;
    const allIds = [];
    (_lastDashboardData.expiry_alerts || []).forEach(a => allIds.push(notifId('expiry', a)));
    (_lastDashboardData.stock_alerts || []).forEach(a => allIds.push(notifId('stock', a)));
    dismissAllNotifs(allIds);
    renderNotificationList();
    showToast('All notifications dismissed', 'info');
}

// ═══════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════

// ── Animated counter helper ──
function animateValue(el, newText, isCurrency = false) {
    const oldText = el.textContent;
    if (oldText === newText) return; // no change

    // Extract numeric value for animation
    const extractNum = (t) => parseFloat(t.replace(/[₹,—]/g, '')) || 0;
    const oldNum = extractNum(oldText);
    const newNum = extractNum(newText);

    // If not a number or first load just set directly
    if (oldText === '—' || isNaN(oldNum) || isNaN(newNum)) {
        el.textContent = newText;
        el.classList.add('kpi-flash');
        setTimeout(() => el.classList.remove('kpi-flash'), 600);
        return;
    }

    // Smooth count animation
    const duration = 600;
    const startTime = performance.now();

    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // ease-out quad
        const ease = 1 - (1 - progress) * (1 - progress);
        const current = oldNum + (newNum - oldNum) * ease;

        if (isCurrency) {
            el.textContent = formatCurrency(current);
        } else {
            el.textContent = Math.round(current);
        }

        if (progress < 1) {
            requestAnimationFrame(tick);
        } else {
            el.textContent = newText;
            // Flash if the value actually changed
            if (oldNum !== newNum) {
                el.classList.add('kpi-flash');
                setTimeout(() => el.classList.remove('kpi-flash'), 600);
            }
        }
    }
    requestAnimationFrame(tick);
}

// ── Apply KPI values with animation ──
function setKPIs(data) {
    animateValue(document.getElementById('stat-total-products'), String(data.total_products));
    animateValue(document.getElementById('stat-total-batches'), String(data.total_batches));
    animateValue(document.getElementById('stat-revenue'), formatCurrency(data.total_revenue), true);
    animateValue(document.getElementById('stat-stock-value'), formatCurrency(data.total_stock_value), true);
    animateValue(document.getElementById('stat-wastage'), formatCurrency(data.total_wastage_loss), true);
    animateValue(document.getElementById('stat-expiring'), String(data.expiring_soon));
    animateValue(document.getElementById('stat-lowstock'), String(data.low_stock_count));
}

// ── Lightweight KPI-only refresh (fast polling) ──
let _kpiPollTimer = null;

async function refreshKPIs() {
    try {
        const data = await fetch(API + '/api/dashboard/kpi').then(r => r.json());
        setKPIs(data);
    } catch (e) { /* silent */ }
}

function startKPIPolling() {
    if (_kpiPollTimer) return; // already running
    _kpiPollTimer = setInterval(refreshKPIs, 10000); // every 10 s
}

function stopKPIPolling() {
    clearInterval(_kpiPollTimer);
    _kpiPollTimer = null;
}

async function loadDashboard() {
    try {
        const data = await apiFetch('/api/dashboard');

        // KPI values (animated)
        setKPIs(data);

        // Update notification bell & dropdown
        updateNotifications(data);

        // Expiry alerts list
        renderExpiryAlerts(data.expiry_alerts);

        // Stock alerts list
        renderStockAlerts(data.stock_alerts);

        // Charts
        renderCategorySalesChart(data.category_sales);
        loadRevenueTrend();

        // Start live polling for KPIs
        startKPIPolling();
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function renderExpiryAlerts(alerts) {
    const list = document.getElementById('expiry-alerts-list');
    if (!list) return;

    if (!alerts || !alerts.length) {
        list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:1rem">No expiry alerts 🎉</p>';
        return;
    }

    // Sort by days_left
    alerts.sort((a, b) => a.days_left - b.days_left);

    list.innerHTML = alerts.slice(0, 15).map(a => `
        <div class="alert-item ${a.status}">
            <div class="alert-info">
                <strong>${a.product_name}</strong>
                <div style="font-size:0.78rem;color:var(--text-muted)">Batch: ${a.batch_number}</div>
            </div>
            <div class="alert-meta" style="flex-direction:column;align-items:flex-end;gap:4px">
                <div>${a.days_left <= 0 ? '⛔ EXPIRED' : `${a.days_left}d left`} • ${a.quantity} units</div>
                <button class="btn btn-sm btn-danger" style="padding:2px 8px;font-size:0.7rem;width:100%"
                    onclick="showWastageModal('${a.batch_id}', '${a.product_name.replace(/'/g, "\\'")}', '${a.product_id}')">
                    🗑 Waste
                </button>
            </div>
        </div>
    `).join('');
}

function renderStockAlerts(alerts) {
    const list = document.getElementById('stock-alerts-list');
    if (!list) return;

    if (!alerts || !alerts.length) {
        list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:1rem">All items in stock ✅</p>';
        return;
    }
    list.innerHTML = alerts.slice(0, 15).map(a => `
        <div class="alert-item low-stock">
            <div class="alert-info">
                <strong>${a.product_name}</strong>
                <div style="font-size:0.78rem;color:var(--text-muted)">${a.category}</div>
            </div>
            <div class="alert-meta" style="flex-direction:column;align-items:flex-end;gap:4px">
                <div>${a.current_stock} / ${a.min_stock}</div>
                <button class="btn btn-sm btn-primary" style="padding:2px 8px;font-size:0.7rem;width:100%"
                    onclick="showRestockModal('${a.product_id}', '${a.product_name.replace(/'/g, "\\'")}')">
                    📦 Restock
                </button>
            </div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════
// CHARTS
// ═══════════════════════════════════════

const chartColors = [
    '#6c63ff', '#00d4ff', '#00e676', '#ffd740',
    '#ff9100', '#ff5252', '#ff4081', '#b388ff', '#69f0ae'
];

function renderCategorySalesChart(data) {
    const ctx = document.getElementById('chart-category-sales');
    if (charts.categorySales) charts.categorySales.destroy();

    charts.categorySales = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.category),
            datasets: [{
                data: data.map(d => d.total_sales),
                backgroundColor: chartColors,
                borderColor: '#1c1c2e',
                borderWidth: 3,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#9595b5', font: { size: 11 }, padding: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ₹${ctx.parsed.toLocaleString()}`
                    }
                }
            }
        }
    });
}

async function loadRevenueTrend() {
    try {
        const data = await apiFetch('/api/analytics/revenue?days=30');
        const ctx = document.getElementById('chart-revenue-trend');
        if (charts.revenueTrend) charts.revenueTrend.destroy();

        charts.revenueTrend = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.date.slice(5)),
                datasets: [
                    {
                        label: 'Revenue',
                        data: data.map(d => d.revenue),
                        backgroundColor: 'rgba(0, 230, 118, 0.4)',
                        borderColor: '#00e676',
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                    {
                        label: 'Wastage',
                        data: data.map(d => d.wastage),
                        backgroundColor: 'rgba(255, 82, 82, 0.4)',
                        borderColor: '#ff5252',
                        borderWidth: 1,
                        borderRadius: 4,
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        grid: { color: 'rgba(42,42,69,0.5)' },
                        ticks: { color: '#9595b5', font: { size: 10 }, maxRotation: 45 }
                    },
                    y: {
                        grid: { color: 'rgba(42,42,69,0.5)' },
                        ticks: { color: '#9595b5', callback: v => '₹' + v }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#9595b5' } }
                }
            }
        });
    } catch (err) {
        console.error('Revenue chart error:', err);
    }
}

// ═══════════════════════════════════════
// INVENTORY
// ═══════════════════════════════════════

async function loadInventory(search = '') {
    try {
        let url = '/api/products';
        const params = new URLSearchParams();
        const catFilter = document.getElementById('category-filter').value;
        if (catFilter) params.set('category', catFilter);
        if (search) params.set('search', search);
        if (params.toString()) url += '?' + params.toString();

        const products = await apiFetch(url);
        productsCache = products;

        const tbody = document.getElementById('inventory-tbody');
        tbody.innerHTML = products.map(p => {
            let statusClass, statusText;
            if (p.total_stock === 0) {
                statusClass = 'out-of-stock';
                statusText = 'Out of Stock';
            } else if (p.total_stock < p.min_stock) {
                statusClass = 'low-stock';
                statusText = 'Low Stock';
            } else {
                statusClass = 'in-stock';
                statusText = 'In Stock';
            }

            return `<tr>
                <td><code>${p.item_id}</code></td>
                <td><strong>${p.name}</strong></td>
                <td>${p.category}</td>
                <td><code style="color:var(--accent-cyan);cursor:pointer" onclick="quickBarcodeLookup('${p.barcode || ''}')" title="Click to lookup">${p.barcode || '—'}</code></td>
                <td>${formatCurrency(p.mrp)}</td>
                <td><strong>${p.total_stock}</strong></td>
                <td>${p.min_stock}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="viewBatches(${p.id})">📋</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})">🗑</button>
                </td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.error('Inventory load error:', err);
    }
}

async function loadCategories() {
    try {
        const cats = await apiFetch('/api/categories');
        const selects = [
            document.getElementById('category-filter'),
            document.getElementById('ml-category-select')
        ];
        selects.forEach(sel => {
            if (!sel) return;
            const firstOption = sel.querySelector('option');
            sel.innerHTML = '';
            sel.appendChild(firstOption);
            cats.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                sel.appendChild(opt);
            });
        });

        // Add filter listener
        document.getElementById('category-filter').addEventListener('change', () => loadInventory());
    } catch (err) { }
}

async function viewBatches(productId) {
    try {
        const product = await apiFetch(`/api/products/${productId}`);
        let html = `<h4 style="margin-bottom:1rem;color:var(--accent-cyan)">${product.name} — Batches</h4>`;

        if (!product.batches.length) {
            html += '<p style="color:var(--text-muted)">No batches found.</p>';
        } else {
            html += product.batches.map(b => `
                <div class="detail-row">
                    <span class="label">${b.batch_number}</span>
                    <span>
                        <span class="status-badge ${b.expiry_status}">${b.expiry_status}</span>
                        Qty: ${b.quantity} | Exp: ${b.expiry_date} (${b.days_until_expiry}d)
                    </span>
                </div>
            `).join('');
        }

        // Quick modal
        const result = document.getElementById('scanner-result');
        result.innerHTML = html;
        switchPage('scanner');
    } catch (err) { }
}

async function deleteProduct(id) {
    if (!confirm('Delete this product?')) return;
    try {
        await apiFetch(`/api/products/${id}`, { method: 'DELETE' });
        showToast('Product deleted', 'success');
        loadInventory();
    } catch (err) { }
}

// ═══════════════════════════════════════
// INVENTORY BARCODE SCANNER
// ═══════════════════════════════════════

function initInventoryScanner() {
    document.getElementById('btn-inv-start-scan').addEventListener('click', startInventoryScanner);
    document.getElementById('btn-inv-stop-scan').addEventListener('click', stopInventoryScanner);
    document.getElementById('btn-inv-barcode-lookup').addEventListener('click', () => {
        const code = document.getElementById('inv-barcode-input').value.trim();
        if (code) inventoryBarcodeLookup(code);
    });
    document.getElementById('inv-barcode-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const code = e.target.value.trim();
            if (code) inventoryBarcodeLookup(code);
        }
    });
}

async function startInventoryScanner() {
    try {
        invQrCode = new Html5Qrcode('inv-barcode-reader');
        await invQrCode.start(
            { facingMode: 'environment' },
            {
                fps: 10,
                qrbox: { width: 250, height: 80 },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.QR_CODE,
                ]
            },
            (decodedText) => {
                document.getElementById('inv-barcode-input').value = decodedText;
                inventoryBarcodeLookup(decodedText);
                stopInventoryScanner();
            },
            () => { }
        );
        document.getElementById('btn-inv-start-scan').disabled = true;
        document.getElementById('btn-inv-stop-scan').disabled = false;
        showToast('Inventory scanner started', 'info');
    } catch (err) {
        showToast('Camera access denied or unavailable', 'error');
    }
}

function stopInventoryScanner() {
    if (invQrCode) {
        invQrCode.stop().then(() => invQrCode.clear()).catch(() => { });
    }
    document.getElementById('btn-inv-start-scan').disabled = false;
    document.getElementById('btn-inv-stop-scan').disabled = true;
}

async function inventoryBarcodeLookup(code) {
    const resultDiv = document.getElementById('inv-barcode-result');
    resultDiv.innerHTML = '<div class="placeholder-text" style="padding:1.5rem"><p>🔍 Searching...</p></div>';

    // 1. Try barcode lookup
    try {
        const product = await apiFetch(`/api/products/barcode/${code}`);
        showInventoryFoundProduct(product);
        highlightInventoryRow(product.barcode);
        return;
    } catch (e) { }

    // 2. Try search by item_id / name
    try {
        const products = await apiFetch(`/api/products?search=${encodeURIComponent(code)}`);
        if (products.length > 0) {
            const product = await apiFetch(`/api/products/${products[0].id}`);
            showInventoryFoundProduct(product);
            highlightInventoryRow(product.barcode);
            return;
        }
    } catch (e) { }

    // 3. Not found — offer to add new product
    showNewProductPrompt(code);
}

function showInventoryFoundProduct(product) {
    const resultDiv = document.getElementById('inv-barcode-result');
    let statusClass, statusText;
    if (product.total_stock === 0) { statusClass = 'out-of-stock'; statusText = 'Out of Stock'; }
    else if (product.total_stock < product.min_stock) { statusClass = 'low-stock'; statusText = 'Low Stock'; }
    else { statusClass = 'in-stock'; statusText = 'In Stock'; }

    resultDiv.innerHTML = `
        <div style="padding:1.25rem;width:100%">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem">
                <h4 style="color:var(--accent-cyan);margin:0;font-size:1.1rem">✅ Product Found</h4>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </div>
            <div class="detail-row"><span class="label">Name</span><span class="value">${product.name}</span></div>
            <div class="detail-row"><span class="label">Item ID</span><span class="value">${product.item_id}</span></div>
            <div class="detail-row"><span class="label">Category</span><span class="value">${product.category}</span></div>
            <div class="detail-row"><span class="label">MRP</span><span class="value">${formatCurrency(product.mrp)}</span></div>
            <div class="detail-row"><span class="label">Barcode</span><span class="value" style="color:var(--accent-cyan)">${product.barcode || 'N/A'}</span></div>
            <div class="detail-row"><span class="label">Stock</span><span class="value" style="font-size:1.1rem">${product.total_stock} units</span></div>
            ${product.batches && product.batches.length > 0 ? `
                <h4 style="color:var(--accent-blue);margin:0.75rem 0 0.5rem;font-size:0.9rem">Batches</h4>
                ${product.batches.slice(0, 3).map(b => `
                    <div class="detail-row" style="font-size:0.8rem">
                        <span class="label">${b.batch_number}</span>
                        <span><span class="status-badge ${b.expiry_status}">${b.expiry_status}</span> Qty: ${b.quantity}</span>
                    </div>
                `).join('')}
            ` : ''}
        </div>
    `;
    showToast(`Found: ${product.name}`, 'success');
}

function showNewProductPrompt(barcode) {
    const resultDiv = document.getElementById('inv-barcode-result');
    resultDiv.innerHTML = `
        <div style="padding:1.5rem;text-align:center;width:100%">
            <p style="font-size:2rem;margin-bottom:0.5rem">🆕</p>
            <h4 style="color:var(--accent-yellow);margin-bottom:0.5rem">Product Not Found</h4>
            <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:1rem">
                No product matches barcode: <code style="color:var(--accent-cyan)">${barcode}</code>
            </p>
            <button class="btn btn-primary" onclick="openAddProductWithBarcode('${barcode}')">
                ➕ Add New Product with This Barcode
            </button>
        </div>
    `;
    showToast('Product not found — add it as new', 'info');
}

function openAddProductWithBarcode(barcode) {
    // Pre-fill the barcode field in the Add Product modal
    document.getElementById('pf-barcode').value = barcode;
    // Auto-generate an item ID
    const randomId = 'ITM' + String(Math.floor(Math.random() * 9000) + 1000).padStart(4, '0');
    document.getElementById('pf-item-id').value = randomId;
    // Open the modal
    document.getElementById('product-modal').classList.add('show');
    // Focus on the name field
    setTimeout(() => document.getElementById('pf-name').focus(), 300);
    showToast('Barcode pre-filled! Fill in the product details.', 'info');
}

function highlightInventoryRow(barcode) {
    if (!barcode) return;
    // Remove any existing highlights
    document.querySelectorAll('.data-table tbody tr.highlight-row').forEach(r => r.classList.remove('highlight-row'));
    // Find the row with this barcode and highlight it
    const rows = document.querySelectorAll('#inventory-tbody tr');
    for (const row of rows) {
        const barcodeCell = row.querySelector('td:nth-child(4) code');
        if (barcodeCell && barcodeCell.textContent === barcode) {
            row.classList.add('highlight-row');
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            break;
        }
    }
}

// ═══════════════════════════════════════
// EXPIRY MONITOR
// ═══════════════════════════════════════

async function loadExpiry() {
    try {
        // Fetch expiry alerts and active POs in parallel
        // Also ensure products cache is populated for category lookup
        const [alerts, pos] = await Promise.all([
            apiFetch('/api/batches/expiring?days=365'),
            apiFetch('/api/purchase-orders?status=draft').catch(() => [])
        ]);
        if (!productsCache.length) {
            productsCache = await apiFetch('/api/products').catch(() => []);
        }

        // Build PO lookup: product item_id → PO info
        const poByProduct = {};
        for (const po of pos) {
            if (po.product_name) {
                poByProduct[po.product_name] = po;
            }
        }

        // Category-based lead times (days) for items without active POs
        const categoryLeadTime = {
            'Dairy': 2, 'Fruits & Vegetables': 3, 'Frozen Foods': 5,
            'Baking Goods': 4, 'Snack Foods': 3, 'Soft Drinks': 3,
            'Canned': 5, 'Health and Hygiene': 4, 'Household': 4,
        };

        // Stats
        const expired = alerts.filter(a => a.status === 'expired').length;
        const critical = alerts.filter(a => a.status === 'critical').length;
        const warning = alerts.filter(a => a.status === 'warning').length;
        const good = alerts.filter(a => a.status === 'good').length;

        document.getElementById('expiry-stats').innerHTML = `
            <div class="expiry-stat-card">
                <span class="stat-number" style="color:var(--accent-red)">${expired}</span>
                <span class="stat-label">⛔ Expired</span>
            </div>
            <div class="expiry-stat-card">
                <span class="stat-number" style="color:var(--accent-red)">${critical}</span>
                <span class="stat-label">🔴 Critical (&lt;7d)</span>
            </div>
            <div class="expiry-stat-card">
                <span class="stat-number" style="color:var(--accent-yellow)">${warning}</span>
                <span class="stat-label">🟡 Warning (7-15d)</span>
            </div>
            <div class="expiry-stat-card">
                <span class="stat-number" style="color:var(--accent-green)">${good}</span>
                <span class="stat-label">🟢 Healthy (&gt;15d)</span>
            </div>
        `;

        // Table
        const tbody = document.getElementById('expiry-tbody');
        tbody.innerHTML = alerts.map(a => {
            let dotClass = 'dot-green';
            let label = 'Healthy';
            let labelClass = 'good';

            if (a.status === 'expired') { dotClass = 'dot-red'; label = 'Expired'; labelClass = 'expired'; }
            else if (a.status === 'critical') { dotClass = 'dot-red'; label = 'Critical'; labelClass = 'critical'; }
            else if (a.status === 'warning') { dotClass = 'dot-yellow'; label = 'Warning'; labelClass = 'warning'; }

            // Restock ETA logic
            let restockEta = '—';
            if (a.status === 'expired' || a.status === 'critical') {
                const po = poByProduct[a.product_name];
                if (po) {
                    // PO exists — estimate delivery ~3 days from PO creation
                    const poDate = new Date(po.created_at);
                    const deliveryDate = new Date(poDate.getTime() + 3 * 86400000);
                    const now = new Date();
                    const daysUntil = Math.max(1, Math.ceil((deliveryDate - now) / 86400000));
                    restockEta = `<span class="restock-po">📦 PO: ~${daysUntil}d</span>`;
                } else {
                    // No PO — use category lead time estimate
                    const lead = categoryLeadTime[a.product_name] || 4;
                    // Find category from product cache if possible
                    const cached = productsCache.find(p => p.item_id === a.item_id);
                    const catLead = cached ? (categoryLeadTime[cached.category] || 4) : 4;
                    restockEta = `<span class="restock-est">~${catLead}d</span>`;
                }
            } else if (a.status === 'warning') {
                restockEta = `<span style="color:var(--text-muted);font-size:0.8rem">Monitoring</span>`;
            }

            return `<tr>
                <td><span class="dot ${dotClass}"></span> <span class="status-badge ${labelClass}">${label}</span></td>
                <td><strong>${a.product_name}</strong></td>
                <td>${a.batch_number}</td>
                <td>${a.expiry_date}</td>
                <td><strong>${a.days_left <= 0 ? (Math.abs(a.days_left) + 'd ago') : a.days_left + 'd'}</strong></td>
                <td>${a.quantity}</td>
                <td>${restockEta}</td>
                <td>
                    ${(a.status === 'expired' || a.status === 'critical') ?
                    `<button class="btn btn-sm btn-danger" onclick="showWastageModal('${a.batch_id}', '${a.product_name.replace(/'/g, "\\'")}', '${a.product_id}')">🗑 Waste</button>` :
                    `<span style="color:var(--accent-green);font-size:0.8rem">✔ No Action</span>`}
                </td>
            </tr>`;
        }).join('');
    } catch (err) { console.error('Expiry load error:', err); }
}

async function markWastage(itemId, qty, batchId) {
    if (!confirm('Mark this batch as wastage? This will remove stock.')) return;

    // Ensure products cache is loaded or fetch product
    let product = productsCache.find(p => p.item_id === itemId);
    if (!product) {
        // Fallback fetch if cache empty
        try {
            const products = await apiFetch('/api/products');
            productsCache = products;
            product = products.find(p => p.item_id === itemId);
        } catch (e) { }
    }

    if (!product) {
        showToast('Product not found (refresh page)', 'error');
        return;
    }

    try {
        await apiFetch('/api/transactions', {
            method: 'POST',
            body: JSON.stringify({
                product_id: product.id,
                batch_id: batchId,
                transaction_type: 'wastage',
                quantity: qty,
                unit_price: product.mrp,
                notes: 'Expired — marked from expiry monitor'
            })
        });
        showToast('Wastage recorded', 'success');
        loadExpiry(); // Refresh list
        refreshKPIs(); // Live-update dashboard numbers
    } catch (err) { console.error(err); }
}

// ═══════════════════════════════════════
// POS / SALES  (Cart + Receipt)
// ═══════════════════════════════════════

let posCart = [];
let receiptCounter = 1000;
let currentPulse = null; // holds pulse discount info for selected product

async function loadPOS() {
    try {
        const products = await apiFetch('/api/products');
        productsCache = products;
        const sel = document.getElementById('pos-product');

        sel.innerHTML = products
            .filter(p => p.total_stock > 0)
            .map(p =>
                `<option value="${p.id}" data-mrp="${p.mrp}" data-name="${p.name}" data-stock="${p.total_stock}">${p.name} (${p.item_id}) — Stock: ${p.total_stock}</option>`
            ).join('');

        sel.onchange = () => {
            const opt = sel.selectedOptions[0];
            if (opt) {
                document.getElementById('pos-price').value = opt.dataset.mrp;
                checkPulseDiscount(parseInt(opt.value));
            }
        };
        sel.dispatchEvent(new Event('change'));
    } catch (err) { }
}

async function checkPulseDiscount(productId) {
    const panel = document.getElementById('pulse-info');
    try {
        const pulse = await apiFetch(`/api/products/${productId}/pulse`);
        currentPulse = pulse;
        if (pulse.has_discount) {
            document.getElementById('pulse-original-price').textContent = formatCurrency(pulse.original_price);
            document.getElementById('pulse-discount-price').textContent = formatCurrency(pulse.discounted_price);
            document.getElementById('pulse-pct-badge').textContent = `−${pulse.discount_pct}%`;
            document.getElementById('pulse-reason').textContent = pulse.reason;
            // Auto-update price field
            document.getElementById('pos-price').value = pulse.discounted_price;
            panel.style.display = 'flex';
        } else {
            currentPulse = null;
            panel.style.display = 'none';
        }
    } catch (err) {
        currentPulse = null;
        panel.style.display = 'none';
    }
}

function initPOSForm() {
    // Barcode input on POS
    document.getElementById('btn-pos-barcode-go').addEventListener('click', () => {
        posBarcodeLookup(document.getElementById('pos-barcode-input').value.trim());
    });
    document.getElementById('pos-barcode-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') posBarcodeLookup(e.target.value.trim());
    });

    // Add to cart
    document.getElementById('pos-add-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const sel = document.getElementById('pos-product');
        const opt = sel.selectedOptions[0];
        if (!opt) return;

        const productId = parseInt(opt.value);
        const name = opt.dataset.name;
        const stock = parseInt(opt.dataset.stock);
        const qty = parseInt(document.getElementById('pos-qty').value);
        const price = parseFloat(document.getElementById('pos-price').value);
        const originalPrice = parseFloat(opt.dataset.mrp);
        const isFlashSale = currentPulse && currentPulse.has_discount && currentPulse.product_id === productId;

        if (qty <= 0) { showToast('Quantity must be at least 1', 'error'); return; }

        const existing = posCart.find(c => c.productId === productId);
        const totalInCart = existing ? existing.qty + qty : qty;
        if (totalInCart > stock) {
            showToast(`Only ${stock} in stock (${existing ? existing.qty + ' already in cart' : '0 in cart'})`, 'error');
            return;
        }

        if (existing) {
            existing.qty += qty;
            existing.subtotal = existing.qty * existing.price;
            existing.originalSubtotal = existing.qty * existing.originalPrice;
        } else {
            posCart.push({
                productId, name, qty, price, originalPrice,
                subtotal: qty * price,
                originalSubtotal: qty * originalPrice,
                isFlashSale
            });
        }

        document.getElementById('pos-qty').value = 1;
        renderCart();
        showToast(`${name} ×${qty} added${isFlashSale ? ' ⚡ Flash Sale price!' : ''}`, 'success');
    });

    // Clear cart
    document.getElementById('btn-clear-cart').addEventListener('click', () => {
        posCart = [];
        renderCart();
        showToast('Cart cleared', 'info');
    });

    // Checkout
    document.getElementById('btn-checkout').addEventListener('click', () => checkout());

    // Receipt modal
    document.getElementById('btn-print-receipt').addEventListener('click', () => {
        const content = document.getElementById('receipt-content').innerHTML;
        const win = window.open('', '_blank', 'width=420,height=600');
        win.document.write(`
            <html><head><title>Receipt</title>
            <style>
                body { font-family: 'Courier New', monospace; padding: 10px; font-size: 13px; color: #000; }
                table { width: 100%; border-collapse: collapse; }
                td, th { padding: 3px 0; }
                .dashed { border-top: 1px dashed #000; margin: 6px 0; }
                h2, h3 { margin: 4px 0; }
                @media print { body { margin: 0; } }
            </style>
            </head><body>${content}</body></html>
        `);
        win.document.close();
        win.print();
    });

    document.getElementById('btn-close-receipt').addEventListener('click', () => {
        document.getElementById('receipt-modal').classList.remove('show');
    });
}

async function posBarcodeLookup(code) {
    if (!code) return;
    try {
        const product = await apiFetch(`/api/products/barcode/${code}`);
        // Select this product in the dropdown
        const sel = document.getElementById('pos-product');
        const option = [...sel.options].find(o => o.value === String(product.id));
        if (option) {
            sel.value = product.id;
            sel.dispatchEvent(new Event('change'));
            showToast(`Found: ${product.name}`, 'success');
        } else {
            showToast(`${product.name} is out of stock`, 'error');
        }
    } catch (err) {
        showToast('Product not found for this barcode', 'error');
    }
    document.getElementById('pos-barcode-input').value = '';
}

function renderCart() {
    const cartDiv = document.getElementById('pos-cart');
    const btnClear = document.getElementById('btn-clear-cart');
    const btnCheckout = document.getElementById('btn-checkout');

    if (posCart.length === 0) {
        cartDiv.innerHTML = '<p class="placeholder-text" style="padding:1.5rem">Cart is empty — scan a barcode or select a product</p>';
        btnClear.disabled = true;
        btnCheckout.disabled = true;
    } else {
        cartDiv.innerHTML = posCart.map((item, i) => `
            <div class="tx-item sale" style="display:flex;align-items:center;justify-content:space-between">
                <div style="flex:1">
                    <strong>${item.name}</strong>
                    ${item.isFlashSale ? '<span class="cart-flash-badge">⚡ FLASH SALE</span>' : ''}
                    <div style="font-size:0.78rem;color:var(--text-muted)">
                        ${item.qty} × ${formatCurrency(item.price)}
                        ${item.isFlashSale ? `<span style="text-decoration:line-through;margin-left:0.3rem;font-size:0.7rem">${formatCurrency(item.originalPrice)}</span>` : ''}
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem">
                    <strong>${formatCurrency(item.subtotal)}</strong>
                    <button class="btn btn-sm btn-danger" onclick="removeFromCart(${i})" title="Remove">✕</button>
                </div>
            </div>
        `).join('');
        btnClear.disabled = false;
        btnCheckout.disabled = false;
    }

    // Update summary
    const totalQty = posCart.reduce((s, c) => s + c.qty, 0);
    const totalAmt = posCart.reduce((s, c) => s + c.subtotal, 0);
    const totalOriginal = posCart.reduce((s, c) => s + c.originalSubtotal, 0);
    const savings = totalOriginal - totalAmt;

    document.getElementById('cart-item-count').textContent = posCart.length;
    document.getElementById('cart-total-qty').textContent = totalQty;
    document.getElementById('cart-total-amount').textContent = formatCurrency(totalAmt);

    // Show savings row if there are flash sale items
    const savingsRow = document.getElementById('cart-savings-row');
    if (savings > 0.01) {
        savingsRow.style.display = 'flex';
        document.getElementById('cart-savings').textContent = `−${formatCurrency(savings)}`;
    } else {
        savingsRow.style.display = 'none';
    }
}

function removeFromCart(index) {
    const removed = posCart.splice(index, 1)[0];
    renderCart();
    showToast(`Removed ${removed.name}`, 'info');
}

async function checkout() {
    if (posCart.length === 0) return;
    const btn = document.getElementById('btn-checkout');
    btn.disabled = true;
    btn.textContent = '⏳ Processing...';

    const results = [];
    let allSuccess = true;

    try {
        for (const item of posCart) {
            try {
                const tx = await apiFetch('/api/transactions', {
                    method: 'POST',
                    body: JSON.stringify({
                        product_id: item.productId,
                        transaction_type: 'sale',
                        quantity: item.qty,
                        unit_price: item.price,
                        notes: item.isFlashSale ? `⚡ Flash Sale (−20%) — original ₹${item.originalPrice.toFixed(2)}` : null
                    })
                });
                results.push({ ...item, success: true, txId: tx.id });
            } catch (err) {
                results.push({ ...item, success: false, error: err.message });
                allSuccess = false;
            }
        }

        generateReceipt(results);

        posCart = [];
        renderCart();
        loadPOS(); // Refresh product list (removes zero-stock items)
        refreshKPIs(); // Live-update dashboard KPI numbers

        // Broadcast update to other tabs/components
        appBus.postMessage({ type: 'INVENTORY_UPDATE' });

        // Invalidate cached dashboard so next visit is fresh
        _dashboardStale = true;

        if (allSuccess) {
            showToast('Sale completed! Receipt generated.', 'success');
        } else {
            showToast('Some items failed — check receipt', 'error');
        }
    } finally {
        // ALWAYS re-enable the button
        btn.disabled = false;
        btn.textContent = '💳 Checkout & Print Receipt';
    }
}

function generateReceipt(items) {
    receiptCounter++;
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const receiptNo = `RCP-${receiptCounter}`;

    const successItems = items.filter(i => i.success);
    const failedItems = items.filter(i => !i.success);

    const totalQty = successItems.reduce((s, i) => s + i.qty, 0);
    const grandTotal = successItems.reduce((s, i) => s + i.subtotal, 0);
    const originalTotal = successItems.reduce((s, i) => s + i.originalSubtotal, 0);
    const totalSavings = originalTotal - grandTotal;

    let html = `
        <div style="text-align:center;margin-bottom:10px">
            <h2 style="margin:0;font-size:1.3rem">🏪 CAMPUS STORE</h2>
            <div style="font-size:0.75rem;color:#666">Smart Campus Inventory System</div>
            <div style="font-size:0.75rem;color:#666">Tel: +91-XXXXX-XXXXX</div>
        </div>
        <div class="dashed"></div>
        <div style="display:flex;justify-content:space-between;font-size:0.78rem">
            <span><strong>Receipt:</strong> ${receiptNo}</span>
            <span>${dateStr}</span>
        </div>
        <div style="font-size:0.78rem;color:#666;margin-bottom:6px">Time: ${timeStr}</div>
        <div class="dashed"></div>

        <table>
            <thead>
                <tr style="border-bottom:1px solid #000">
                    <th style="text-align:left">Item</th>
                    <th style="text-align:center">Qty</th>
                    <th style="text-align:right">Price</th>
                    <th style="text-align:right">Total</th>
                </tr>
            </thead>
            <tbody>
                ${successItems.map(item => `
                    <tr>
                        <td style="text-align:left;font-size:0.82rem">
                            ${item.name}
                            ${item.isFlashSale ? '<br><span style="font-size:0.7rem;color:#e65100">⚡ FLASH SALE −20%</span>' : ''}
                        </td>
                        <td style="text-align:center">${item.qty}</td>
                        <td style="text-align:right">
                            ${item.isFlashSale ? `<span style="text-decoration:line-through;font-size:0.7rem;color:#999">₹${item.originalPrice.toFixed(2)}</span><br>` : ''}
                            ₹${item.price.toFixed(2)}
                        </td>
                        <td style="text-align:right"><strong>₹${item.subtotal.toFixed(2)}</strong></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>

        <div class="dashed"></div>
        <div style="display:flex;justify-content:space-between;font-size:0.85rem">
            <span>Total Items:</span><span>${successItems.length}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.85rem">
            <span>Total Qty:</span><span>${totalQty}</span>
        </div>
    `;

    if (totalSavings > 0.01) {
        html += `
            <div style="display:flex;justify-content:space-between;font-size:0.85rem;color:#e65100">
                <span>⚡ Flash Sale Savings:</span><span>−₹${totalSavings.toFixed(2)}</span>
            </div>
        `;
    }

    html += `
        <div class="dashed"></div>
        <div style="display:flex;justify-content:space-between;font-size:1.3rem;font-weight:bold">
            <span>GRAND TOTAL</span><span>₹${grandTotal.toFixed(2)}</span>
        </div>
        <div class="dashed"></div>
    `;

    if (failedItems.length > 0) {
        html += `
            <div style="color:red;font-size:0.78rem;margin-top:6px">
                <strong>⚠ Failed Items:</strong><br>
                ${failedItems.map(i => `${i.name} — ${i.error}`).join('<br>')}
            </div>
            <div class="dashed"></div>
        `;
    }

    html += `
        <div style="text-align:center;font-size:0.75rem;color:#888;margin-top:8px">
            <div>Thank you for shopping at Campus Store!</div>
            <div style="margin-top:4px">— Powered by The Pulse Engine —</div>
        </div>
    `;

    document.getElementById('receipt-content').innerHTML = html;
    document.getElementById('receipt-modal').classList.add('show');
}


// ═══════════════════════════════════════
// ANALYTICS
// ═══════════════════════════════════════

async function loadAnalytics() {
    loadCategoryStockChart();
    loadWastageChart();
    loadRevenueLineChart();
}

async function loadCategoryStockChart() {
    try {
        const data = await apiFetch('/api/analytics/categories');
        const ctx = document.getElementById('chart-category-stock');
        if (charts.categoryStock) charts.categoryStock.destroy();

        charts.categoryStock = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.category),
                datasets: [{
                    label: 'Stock Value (₹)',
                    data: data.map(d => d.stock_value),
                    backgroundColor: chartColors.map(c => c + '88'),
                    borderColor: chartColors,
                    borderWidth: 2,
                    borderRadius: 6,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                scales: {
                    x: {
                        grid: { color: 'rgba(42,42,69,0.5)' },
                        ticks: { color: '#9595b5', callback: v => '₹' + (v / 1000).toFixed(0) + 'k' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#9595b5', font: { size: 11 } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: ctx => ` ₹${ctx.parsed.x.toLocaleString()}` }
                    }
                }
            }
        });
    } catch (err) { }
}

async function loadWastageChart() {
    try {
        const data = await apiFetch('/api/analytics/wastage');
        const ctx = document.getElementById('chart-wastage');
        if (charts.wastage) charts.wastage.destroy();

        charts.wastage = new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.map(d => d.category),
                datasets: [{
                    data: data.map(d => d.total_loss),
                    backgroundColor: chartColors.map(c => c + '66'),
                    borderColor: chartColors,
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    r: {
                        grid: { color: 'rgba(42,42,69,0.5)' },
                        ticks: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#9595b5', font: { size: 11 }, padding: 10 }
                    }
                }
            }
        });
    } catch (err) { }
}

async function loadRevenueLineChart() {
    try {
        const data = await apiFetch('/api/analytics/revenue?days=30');
        const ctx = document.getElementById('chart-revenue-line');
        if (charts.revenueLine) charts.revenueLine.destroy();

        charts.revenueLine = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date.slice(5)),
                datasets: [
                    {
                        label: 'Net Revenue',
                        data: data.map(d => d.net),
                        borderColor: '#6c63ff',
                        backgroundColor: 'rgba(108,99,255,0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                    },
                    {
                        label: 'Revenue',
                        data: data.map(d => d.revenue),
                        borderColor: '#00e676',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderDash: [5, 5],
                        pointRadius: 2,
                    },
                    {
                        label: 'Wastage',
                        data: data.map(d => d.wastage),
                        borderColor: '#ff5252',
                        backgroundColor: 'transparent',
                        tension: 0.4,
                        borderDash: [5, 5],
                        pointRadius: 2,
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        grid: { color: 'rgba(42,42,69,0.3)' },
                        ticks: { color: '#9595b5', font: { size: 10 } }
                    },
                    y: {
                        grid: { color: 'rgba(42,42,69,0.3)' },
                        ticks: { color: '#9595b5', callback: v => '₹' + v }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#9595b5' } }
                }
            }
        });
    } catch (err) { }
}

// ═══════════════════════════════════════
// BARCODE SCANNER
// ═══════════════════════════════════════

function initScanner() {
    document.getElementById('btn-start-scan').addEventListener('click', startScanner);
    document.getElementById('btn-stop-scan').addEventListener('click', stopScanner);
    document.getElementById('btn-lookup-barcode').addEventListener('click', () => {
        const code = document.getElementById('manual-barcode').value.trim();
        if (code) lookupBarcode(code);
    });
    document.getElementById('manual-barcode').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const code = e.target.value.trim();
            if (code) lookupBarcode(code);
        }
    });
}

async function startScanner() {
    try {
        html5QrCode = new Html5Qrcode("barcode-reader");
        await html5QrCode.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 250, height: 100 },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.QR_CODE,
                ]
            },
            (decodedText) => {
                lookupBarcode(decodedText);
                stopScanner();
            },
            () => { }
        );
        document.getElementById('btn-start-scan').disabled = true;
        document.getElementById('btn-stop-scan').disabled = false;
        showToast('Scanner started', 'info');
    } catch (err) {
        showToast('Camera access denied or unavailable', 'error');
    }
}

function stopScanner() {
    if (html5QrCode) {
        html5QrCode.stop().then(() => {
            html5QrCode.clear();
        }).catch(() => { });
    }
    document.getElementById('btn-start-scan').disabled = false;
    document.getElementById('btn-stop-scan').disabled = true;
}

function renderProductResult(product) {
    return `
        <div class="product-detail-card">
            <h4>${product.name}</h4>
            <div class="detail-row"><span class="label">Item ID</span><span class="value">${product.item_id}</span></div>
            <div class="detail-row"><span class="label">Category</span><span class="value">${product.category}</span></div>
            <div class="detail-row"><span class="label">MRP</span><span class="value">${formatCurrency(product.mrp)}</span></div>
            <div class="detail-row"><span class="label">Total Stock</span><span class="value">${product.total_stock}</span></div>
            <div class="detail-row"><span class="label">Barcode</span><span class="value" style="color:var(--accent-cyan)">${product.barcode || 'N/A'}</span></div>
            <h4 style="margin-top:1rem">Batches</h4>
            ${product.batches.length ? product.batches.map(b => `
                <div class="detail-row">
                    <span class="label">${b.batch_number}</span>
                    <span>
                        <span class="status-badge ${b.expiry_status}">${b.expiry_status}</span>
                        Qty: ${b.quantity} | ${b.days_until_expiry}d left
                    </span>
                </div>
            `).join('') : '<p style="color:var(--text-muted)">No batches found.</p>'}
        </div>
    `;
}

async function lookupBarcode(code) {
    const result = document.getElementById('scanner-result');
    try {
        // Try barcode lookup first
        const product = await apiFetch(`/api/products/barcode/${code}`);
        result.innerHTML = renderProductResult(product);
        showToast(`Found: ${product.name}`, 'success');
    } catch (err) {
        // Fallback: try searching by item_id or name
        try {
            const products = await apiFetch(`/api/products?search=${encodeURIComponent(code)}`);
            if (products.length > 0) {
                // Get full product with batches
                const product = await apiFetch(`/api/products/${products[0].id}`);
                result.innerHTML = renderProductResult(product);
                showToast(`Found: ${product.name} (matched by ID/name)`, 'success');
                return;
            }
        } catch (e) { }
        result.innerHTML = `
            <div style="text-align:center;padding:2rem">
                <p style="font-size:2rem;margin-bottom:0.5rem">❌</p>
                <p>No product found for: <strong>${code}</strong></p>
                <p style="font-size:0.82rem;color:var(--text-muted);margin-top:0.5rem">Try a barcode from the directory below, or search by product name or Item ID.</p>
            </div>
        `;
    }
}

// ═══════════════════════════════════════
// ML INSIGHTS
// ═══════════════════════════════════════

async function loadMLInsights() {
    try {
        // Load PO Drafts
        loadPurchaseOrders();

        // Seasonal chart
        const predictions = await apiFetch('/api/ml/seasonal');
        renderSeasonalChart(predictions);

        // Category insights
        const insights = await apiFetch('/api/ml/insights');
        renderMLInsightCards(insights);

        // Filter listener
        document.getElementById('ml-category-select').addEventListener('change', async (e) => {
            const cat = e.target.value;
            let filtered = [...predictions];
            if (cat) filtered = predictions.filter(p => p.category === cat);
            renderSeasonalChart(filtered);
        });
    } catch (err) {
        document.getElementById('ml-insights-grid').innerHTML =
            '<p style="color:var(--text-muted);text-align:center;grid-column:1/-1;padding:2rem">ML model not yet trained. Ensure the CSV dataset is available.</p>';
    }
}

async function loadPurchaseOrders() {
    const list = document.getElementById('po-drafts-list');
    try {
        const result = await apiFetch('/api/purchase-orders?status=draft');
        if (result.length === 0) {
            list.innerHTML = `<p class="placeholder-text" style="padding:1.5rem">No stock-out risks detected. Inventory healthy.</p>`;
            return;
        }

        list.innerHTML = result.map(po => `
            <div class="tx-item warning" style="display:flex;align-items:center;justify-content:space-between;padding:1rem;background:var(--bg-secondary);border-left:4px solid var(--accent-orange);margin-bottom:0.5rem;border-radius:var(--radius-sm)">
                <div style="display:flex;flex-direction:column;gap:0.3rem">
                    <div style="font-weight:600;font-size:1rem;color:var(--text-primary)">
                        📦 ${po.product_name || 'Unknown Product'}
                    </div>
                    <div style="font-size:0.8rem;color:var(--text-secondary)">
                        Supplier: <strong style="color:var(--accent-blue)">${po.supplier_name || 'Unknown'}</strong>
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:0.75rem;color:var(--accent-orange);font-weight:700;margin-bottom:0.2rem">PREDICTED STOCK-OUT</div>
                    <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary)">
                        ${po.predicted_stockout_date ? new Date(po.predicted_stockout_date).toLocaleDateString() : 'Within 48h'}
                    </div>
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.2rem">
                        Draft Order: <strong>${po.quantity} units</strong>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        list.innerHTML = `<p class="placeholder-text error">Failed to load drafts: ${err.message}</p>`;
    }
}

function renderSeasonalChart(predictions) {
    const ctx = document.getElementById('chart-seasonal');
    if (charts.seasonal) charts.seasonal.destroy();

    // Group by category
    const categories = [...new Set(predictions.map(p => p.category))];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    const datasets = categories.map((cat, i) => ({
        label: cat,
        data: predictions
            .filter(p => p.category === cat)
            .sort((a, b) => a.month - b.month)
            .map(p => p.predicted_demand),
        borderColor: chartColors[i % chartColors.length],
        backgroundColor: chartColors[i % chartColors.length] + '20',
        fill: false,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 7,
    }));

    charts.seasonal = new Chart(ctx, {
        type: 'line',
        data: { labels: months, datasets },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    grid: { color: 'rgba(42,42,69,0.3)' },
                    ticks: { color: '#9595b5' }
                },
                y: {
                    grid: { color: 'rgba(42,42,69,0.3)' },
                    ticks: { color: '#9595b5' },
                    title: { display: true, text: 'Predicted Demand', color: '#9595b5' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#9595b5', font: { size: 11 } },
                    position: 'bottom',
                }
            }
        }
    });
}

function renderMLInsightCards(insights) {
    const grid = document.getElementById('ml-insights-grid');
    grid.innerHTML = insights.map(i => `
        <div class="ml-insight-card">
            <h4>📊 ${i.category}</h4>
            <div class="insight-row">
                <span class="label">Mean Demand</span>
                <span class="value">${i.mean_demand}</span>
            </div>
            <div class="insight-row">
                <span class="label">Peak Month</span>
                <span class="value" style="color:var(--accent-green)">📈 ${i.peak_month}</span>
            </div>
            <div class="insight-row">
                <span class="label">Low Month</span>
                <span class="value" style="color:var(--accent-red)">📉 ${i.low_month}</span>
            </div>
            <div class="insight-row">
                <span class="label">Peak Demand</span>
                <span class="value">${i.peak_demand}</span>
            </div>
            <div class="insight-row">
                <span class="label">Volatility</span>
                <span class="value">${i.volatility}</span>
            </div>
            <div class="insight-row">
                <span class="label">Confidence</span>
                <span class="value">${(i.confidence * 100).toFixed(0)}%</span>
            </div>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width:${i.confidence * 100}%"></div>
            </div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════
// MODALS
// ═══════════════════════════════════════

function initModals() {
    const modal = document.getElementById('product-modal');
    document.getElementById('btn-add-product').addEventListener('click', () => {
        modal.classList.add('show');
    });
    document.getElementById('modal-close').addEventListener('click', () => {
        modal.classList.remove('show');
    });
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('show');
    });

    // Product form
    document.getElementById('product-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            item_id: document.getElementById('pf-item-id').value,
            name: document.getElementById('pf-name').value,
            category: document.getElementById('pf-category').value,
            mrp: parseFloat(document.getElementById('pf-mrp').value),
            barcode: document.getElementById('pf-barcode').value || null,
            min_stock: parseInt(document.getElementById('pf-min-stock').value),
        };

        try {
            await apiFetch('/api/products', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showToast('Product added!', 'success');
            modal.classList.remove('show');
            document.getElementById('product-form').reset();
            loadInventory();
        } catch (err) { }
    });
}


// ═══════════════════════════════════════
// BARCODE DIRECTORY
// ═══════════════════════════════════════

async function loadBarcodeDirectory() {
    try {
        const products = await apiFetch('/api/products');
        productsCache = products;
        renderBarcodeDirectory(products);

        // Live search filter
        const searchInput = document.getElementById('barcode-dir-search');
        searchInput.addEventListener('input', () => {
            const q = searchInput.value.toLowerCase().trim();
            const filtered = products.filter(p =>
                p.name.toLowerCase().includes(q) ||
                p.item_id.toLowerCase().includes(q) ||
                (p.barcode || '').toLowerCase().includes(q) ||
                p.category.toLowerCase().includes(q)
            );
            renderBarcodeDirectory(filtered);
        });
    } catch (err) {
        console.error('Barcode directory error:', err);
    }
}

function renderBarcodeDirectory(products) {
    const tbody = document.getElementById('barcode-dir-tbody');
    tbody.innerHTML = products.map(p => {
        const barcode = p.barcode || '—';
        const hasBarcode = !!p.barcode;
        return `<tr>
            <td><code>${p.item_id}</code></td>
            <td>${p.name}</td>
            <td>${p.category}</td>
            <td><code style="color:var(--accent-cyan);font-size:0.9rem">${barcode}</code></td>
            <td>${p.total_stock}</td>
            <td>
                ${hasBarcode
                ? `<button class="btn btn-sm btn-primary" onclick="quickBarcodeLookup('${p.barcode}')">🔍 Lookup</button>`
                : `<span style="color:var(--text-muted);font-size:0.78rem">No barcode</span>`
            }
            </td>
        </tr>`;
    }).join('');
}

function quickBarcodeLookup(barcode) {
    if (!barcode) {
        showToast('No barcode assigned to this product', 'error');
        return;
    }
    // Navigate to scanner page if not there
    const scannerPage = document.getElementById('page-scanner');
    if (!scannerPage.classList.contains('active')) {
        switchPage('scanner');
    }
    // Fill the manual input and trigger lookup
    document.getElementById('manual-barcode').value = barcode;
    lookupBarcode(barcode);
    // Scroll to top of scanner
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ═══════════════════════════════════════
// RESTOCK & WASTAGE MODALS
// ═══════════════════════════════════════

function showRestockModal(productId, productName) {
    document.getElementById('restock-product-id').value = productId;
    document.getElementById('restock-product-name').value = productName;
    document.getElementById('restock-qty').value = '';
    document.getElementById('restock-cost').value = '';

    // Set expiry default: today + 365 days
    const d = new Date();
    d.setDate(d.getDate() + 365);
    try {
        document.getElementById('restock-exp').value = d.toISOString().split('T')[0];
        document.getElementById('modal-restock').classList.add('show');
    } catch (e) { console.error(e); }
}

function closeRestockModal() {
    document.getElementById('modal-restock').classList.remove('show');
}

async function submitRestock() {
    const pid = document.getElementById('restock-product-id').value;
    const qty = parseInt(document.getElementById('restock-qty').value);
    const cost = parseFloat(document.getElementById('restock-cost').value);
    const mfg = document.getElementById('restock-mfg').value || null;
    const exp = document.getElementById('restock-exp').value;

    if (!pid || !qty || qty <= 0 || !exp) {
        showToast('Please verify quantity and expiry date', 'error');
        return;
    }

    try {
        await apiFetch('/api/batches', {
            method: 'POST',
            body: JSON.stringify({
                product_id: parseInt(pid),
                quantity: qty,
                cost_price: cost || 0,
                manufacture_date: mfg,
                expiry_date: exp
            })
        });
        showToast('Stock added successfully!', 'success');
        closeRestockModal();
        appBus.postMessage({ type: 'INVENTORY_UPDATE' });
        loadDashboard();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function showWastageModal(batchId, productName, productId) {
    document.getElementById('wastage-batch-id').value = batchId;
    document.getElementById('wastage-product-id').value = productId;
    document.getElementById('wastage-product-name').value = productName;
    document.getElementById('wastage-qty').value = '';
    document.getElementById('wastage-notes').value = '';
    document.getElementById('modal-wastage').classList.add('show');
}

function closeWastageModal() {
    document.getElementById('modal-wastage').classList.remove('show');
}

async function submitWastage() {
    const batchId = document.getElementById('wastage-batch-id').value;
    const productId = document.getElementById('wastage-product-id').value;
    const qty = parseInt(document.getElementById('wastage-qty').value);
    const reason = document.getElementById('wastage-reason').value;
    const notes = document.getElementById('wastage-notes').value;

    if (!qty || qty <= 0) {
        showToast('Please enter a valid quantity', 'error');
        return;
    }

    try {
        await apiFetch('/api/transactions', {
            method: 'POST',
            body: JSON.stringify({
                product_id: parseInt(productId),
                batch_id: parseInt(batchId),
                transaction_type: 'wastage',
                quantity: qty,
                notes: `${reason}: ${notes}`
            })
        });
        showToast('Wastage recorded', 'success');
        closeWastageModal();
        appBus.postMessage({ type: 'INVENTORY_UPDATE' });
        loadDashboard();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function exportInventoryCSV() {
    if (!window.productsCache || !window.productsCache.length) {
        // Try direct fetch if cache empty
        apiFetch('/api/products').then(products => {
            window.productsCache = products;
            exportInventoryCSV();
        }).catch(() => showToast('No data to export', 'error'));
        return;
    }

    let csv = 'Item ID,Name,Category,MRP,Stock,Min Stock,Status\n';
    window.productsCache.forEach(p => {
        const stockStatus = p.total_stock < p.min_stock ? 'Low' : 'OK';
        // Escape quotes in name
        const safeName = (p.name || '').replace(/"/g, '""');
        csv += `${p.item_id},"${safeName}",${p.category},${p.mrp},${p.total_stock},${p.min_stock},${stockStatus}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inventory_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    setTimeout(() => document.body.removeChild(a), 100);
}
