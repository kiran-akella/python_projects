let historyData = [];

// Format date to "DDth Month YYYY"
function formatDate(date) {
    const day = date.getDate();
    const month = date.toLocaleString('default', { month: 'long' });
    const year = date.getFullYear();
    return `${day}-${month} ${year}`;
}

// Format time to "HH:MM:SS"
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
    });
}

// Update current date and time
function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-date').textContent = formatDate(now);
    document.getElementById('current-time').textContent = formatTime(now);
}

// Fetch current status
async function fetchStatus() {
    try {
        const response = await fetch('/status');
        if (!response.ok) throw new Error('Failed to fetch status');
        const data = await response.json();
        
        document.getElementById('cpu').textContent = `${data.cpu_percent.toFixed(1)}%`;
        document.getElementById('mem').textContent = `${data.memory_percent.toFixed(1)}%`;
        document.getElementById('disk').textContent = `${data.disk_percent.toFixed(1)}%`;
        
        updateResourceColors('cpu', data.cpu_percent);
        updateResourceColors('mem', data.memory_percent);
        updateResourceColors('disk', data.disk_percent);
    } catch (err) {
        showError('Failed to update status');
    }
}

// Fetch disk I/O
async function fetchDiskIO() {
    try {
        const response = await fetch('/diskio');
        if (!response.ok) throw new Error('Failed to fetch disk I/O');
        const data = await response.json();
        const total = data.total_speed;
        document.getElementById('disk-io').textContent = `${total.toFixed(1)} MB/s`;
        // Update average if needed
        const diskIOAvg = document.getElementById('disk-io-avg');
        if (diskIOAvg) {
            let currentAvg = parseFloat(diskIOAvg.getAttribute('data-avg') || '0');
            let count = parseInt(diskIOAvg.getAttribute('data-count') || '0');
            currentAvg = (currentAvg * count + total) / (count + 1);
            diskIOAvg.setAttribute('data-avg', currentAvg);
            diskIOAvg.setAttribute('data-count', count + 1);
            diskIOAvg.textContent = `${currentAvg.toFixed(1)} MB/s`;
        }
    } catch (err) {
        showError('Failed to update disk I/O');
    }
}

// Update resource color based on usage
function updateResourceColors(id, value) {
    const element = document.getElementById(id);
    if (value >= 80) {
        element.style.color = '#dc3545';
    } else if (value >= 60) {
        element.style.color = '#ffc107';
    } else {
        element.style.color = '#28a745';
    }
}

// Fetch and update history table
async function fetchHistory() {
    try {
        const response = await fetch('/history');
        if (!response.ok) throw new Error('Failed to fetch history');
        historyData = await response.json();
        updateHistoryTable(historyData);
    } catch (err) {
        showError('Failed to load history');
    }
}

function updateHistoryTable(data, isFiltered = false) {
    const tbody = document.getElementById('history-body');
    tbody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No historical data available.</td></tr>';
        return;
    }
    
    // Take only the most recent entries first
    let entries = isFiltered ? data : data.slice(0, 10);
    
    entries.forEach(row => {
        try {
            const tr = document.createElement('tr');
            const timestamp = new Date(row.timestamp);
            const ioSpeed = parseFloat(row.disk_io_mb_sec) || 0;
            
            tr.innerHTML = `
                <td>${timestamp.toLocaleString()}</td>
                <td>${parseFloat(row.cpu_percent).toFixed(1)}</td>
                <td>${parseFloat(row.memory_percent).toFixed(1)}</td>
                <td>${parseFloat(row.disk_percent).toFixed(1)}</td>
                <td>${ioSpeed.toFixed(1)} MB/s</td>
            `;
            tbody.appendChild(tr);
        } catch (err) {
            console.error('Error rendering row:', err, row);
        }
    });
}

function applyFilter() {
    const fromDate = new Date(document.getElementById('from-date').value);
    const toDate = new Date(document.getElementById('to-date').value);
    
    const filteredData = historyData.filter(row => {
        const rowDate = new Date(row.timestamp);
        return rowDate >= fromDate && rowDate <= toDate;
    });
    
    updateHistoryTable(filteredData, true);  // Pass true to indicate filtered view
}

function resetFilter() {
    document.getElementById('from-date').value = '';
    document.getElementById('to-date').value = '';
    updateHistoryTable(historyData, false);  // Pass false to show only 10 rows
}

function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.style.display = 'block';
    setTimeout(() => {
        error.style.display = 'none';
    }, 5000);
}

// Update system uptime
function updateUptime() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            if (data.uptime) {
                document.getElementById('uptime').textContent = data.uptime;
            }
        })
        .catch(err => console.error('Failed to update uptime:', err));
}

// Initialize
updateCurrentTime();
setInterval(updateCurrentTime, 1000);
setInterval(updateUptime, 1000);
setInterval(fetchStatus, 5000);
setInterval(fetchDiskIO, 5000);
fetchHistory();
setInterval(fetchHistory, 5000);
