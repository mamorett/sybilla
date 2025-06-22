// Add status polling
let statusInterval;

function startStatusPolling() {
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            updateStatusDisplay(status);
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 1000); // Poll every second
}

function stopStatusPolling() {
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

function updateStatusDisplay(status) {
    const statusDiv = document.getElementById('status-display');
    if (!statusDiv) return;
    
    if (status.running) {
        statusDiv.innerHTML = `
            <div class="status-running">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${status.progress}%"></div>
                </div>
                <p><strong>${status.step}</strong>: ${status.message}</p>
                <small>Progress: ${status.progress}%</small>
            </div>
        `;
    } else if (status.error) {
        statusDiv.innerHTML = `
            <div class="status-error">
                <p><strong>Error:</strong> ${status.error}</p>
                <small>Step: ${status.step}</small>
            </div>
        `;
    } else if (status.step === 'complete') {
        statusDiv.innerHTML = `
            <div class="status-complete">
                <p><strong>✅ Analysis Complete!</strong></p>
                <small>Last update: ${status.last_update}</small>
            </div>
        `;
    }
}

// Add to your existing JavaScript
async function startAnalysis() {
    try {
        const response = await fetch('/api/start-analysis', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            startStatusPolling();
        } else {
            alert('Failed to start analysis: ' + result.error);
        }
    } catch (error) {
        alert('Error starting analysis: ' + error.message);
    }
}

// Add status display to your HTML
document.addEventListener('DOMContentLoaded', function() {
    // Add status display div
    const statusDiv = document.createElement('div');
    statusDiv.id = 'status-display';
    statusDiv.className = 'status-container';
    document.body.insertBefore(statusDiv, document.body.firstChild);
    
    // Add start analysis button
    const startBtn = document.createElement('button');
    startBtn.textContent = 'Start Analysis';
    startBtn.onclick = startAnalysis;
    statusDiv.appendChild(startBtn);
});
