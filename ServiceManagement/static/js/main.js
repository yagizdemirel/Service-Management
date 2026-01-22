document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch
    fetchStats();
    fetchServices();
    startClock();

    // Auto-refresh every 5 seconds
    setInterval(() => {
        fetchStats();
        fetchServices(false); // false = don't show loading spinner/flicker if possible
    }, 5000);

    // Search filter
    document.getElementById('search-input').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        filterServices(searchTerm);
    });
});

let currentServices = [];
let currentLogService = null;

function startClock() {
    const timeEl = document.getElementById('system-time');
    setInterval(() => {
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString();
    }, 1000);
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        document.getElementById('stat-cpu').textContent = `${data.cpu_percent}%`;
        document.getElementById('prog-cpu').style.width = `${data.cpu_percent}%`;

        document.getElementById('stat-ram').textContent = `${data.ram_percent}%`;
        document.getElementById('prog-ram').style.width = `${data.ram_percent}%`;

    } catch (err) {
        console.error('Error fetching stats:', err);
    }
}

async function fetchServices(showLoading = true) {
    if (showLoading) {
        // Optional: Add loading state if needed for first load
    }

    try {
        const res = await fetch('/api/services');
        const data = await res.json();
        currentServices = data;

        updateStatsCounters(data);
        renderServices(data);
    } catch (err) {
        console.error('Error fetching services:', err);
    }
}

function updateStatsCounters(services) {
    const total = services.length;
    const running = services.filter(s => s.status === 'running').length;
    const failed = services.filter(s => s.status === 'failed').length;

    animateValue('stat-total', parseInt(document.getElementById('stat-total').textContent), total, 500);
    animateValue('stat-running', parseInt(document.getElementById('stat-running').textContent), running, 500);
    animateValue('stat-failed', parseInt(document.getElementById('stat-failed').textContent), failed, 500);
}

function renderServices(services) {
    const tbody = document.getElementById('services-body');
    const searchTerm = document.getElementById('search-input').value.toLowerCase();

    // Filter
    const filtered = services.filter(s =>
        s.name.toLowerCase().includes(searchTerm) ||
        s.description.toLowerCase().includes(searchTerm)
    );

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">No services found.</td></tr>`;
        return;
    }

    // Build HTML
    // We try to minimize DOM thrashing by rebuilding mostly, but for a small list it's fine.
    // Ideally we would diff, but innerHTML is simpler here.
    const html = filtered.map(s => {
        let badgeClass = 'badge-stopped';
        let icon = 'bi-stop-circle';

        if (s.status === 'running') {
            badgeClass = 'badge-running';
            icon = 'bi-check-circle-fill';
        } else if (s.status === 'failed') {
            badgeClass = 'badge-failed';
            icon = 'bi-x-circle-fill';
        }

        return `
            <tr>
                <td class="ps-4 fw-bold font-monospace text-dark">${s.name}</td>
                <td>
                    <span class="badge-status ${badgeClass}">
                        <i class="bi ${icon}"></i> ${s.status.toUpperCase()}
                    </span>
                </td>
                <td class="text-secondary small text-truncate" style="max-width: 300px;">${s.description}</td>
                <td class="text-end pe-4">
                    <button class="btn btn-sm btn-white border shadow-sm hover-primary" onclick="openLogs('${s.name}')">
                        <i class="bi bi-file-text"></i> Logs
                    </button>
                    <!-- Future actions: Start/Stop buttons -->
                </td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = html;
}

function filterServices(term) {
    renderServices(currentServices);
}

async function openLogs(serviceName) {
    currentLogService = serviceName;
    const modal = new bootstrap.Modal(document.getElementById('logModal'));
    modal.show();

    document.getElementById('logModalLabel').innerHTML = `<i class="bi bi-terminal me-2"></i>Logs: ${serviceName}`;
    document.getElementById('log-content').textContent = "Loading logs...";

    await refreshCurrentLogs();
}

async function refreshCurrentLogs() {
    if (!currentLogService) return;

    const container = document.getElementById('log-content');
    try {
        const res = await fetch(`/api/services/${currentLogService}/logs`);
        const data = await res.json();

        // Simple formatting
        container.textContent = data.logs;
        container.scrollTop = container.scrollHeight; // Auto scroll to bottom
    } catch (err) {
        container.textContent = "Error loading logs.";
    }
}

// Helper animation for numbers
function animateValue(id, start, end, duration) {
    if (start === end) return;
    const range = end - start;
    let current = start;
    const increment = end > start ? 1 : -1;
    const stepTime = Math.abs(Math.floor(duration / range));
    const obj = document.getElementById(id);
    const timer = setInterval(function () {
        current += increment;
        obj.innerHTML = current;
        if (current == end) {
            clearInterval(timer);
        }
    }, stepTime);
}
