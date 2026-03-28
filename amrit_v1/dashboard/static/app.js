const CORE_SERVICES = ['frontend', 'catalogue', 'orders', 'payment', 'user', 'carts', 'shipping'];

let slaTimer = null;
let secondsElapsed = 0;
let isAnomalyActive = false;

// DOM Elements
const gridEl = document.getElementById('service-grid');
const consoleEL = document.getElementById('console-box');
const statusBadge = document.getElementById('ai-status');
const chaosBtn = document.getElementById('chaos-btn');
const timeDisplay = document.getElementById('resolution-time');

// Initialize grid structure
function initGrid() {
    gridEl.innerHTML = '';
    CORE_SERVICES.forEach(service => {
        const node = document.createElement('div');
        node.className = `node healthy`;
        node.id = `node-${service}`;
        node.innerHTML = `
            <span class="node-name">${service}</span>
            <span class="node-status"></span>
        `;
        gridEl.appendChild(node);
    });
}

function updateState() {
    fetch('/api/state')
        .then(r => r.json())
        .then(data => {
            // Update Grid Status
            CORE_SERVICES.forEach(service => {
                const node = document.getElementById(`node-${service}`);
                if (!node) return;
                
                // If service is flagged, render anomaly effects
                const normalizedVictim = data.last_victim.replace(/-/g, '');
                const isFlagged = data.flagged_containers.some(c => c.replace(/-/g, '').includes(service.replace(/-/g, '')));
                
                if (isFlagged || normalizedVictim.includes(service.replace(/-/g, ''))) {
                    node.className = 'node anomaly';
                } else {
                    node.className = 'node healthy';
                }
            });

            // Update Logs
            consoleEL.innerHTML = '';
            data.logs.forEach(log => {
                const p = document.createElement('p');
                p.className = 'console-line text-grey';
                p.textContent = log;
                consoleEL.appendChild(p);
            });
            
            // Append explicit AI correlation thoughts directly to the tail of the log feed
            if (data.status.includes("Confirmed") || data.status.includes("Chaos")) {
                const p = document.createElement('p');
                p.className = 'console-line text-red';
                p.textContent = `[DistilBERT & LSTM] >>> ${data.status.toUpperCase()} <<<`;
                consoleEL.appendChild(p);
            }
            if (data.status.includes("Remediation Executed")) {
                const p = document.createElement('p');
                p.className = 'console-line text-green';
                p.textContent = `[Medic Bot] >>> SUCCESSFULLY REBOOTED ${data.last_remediated.toUpperCase()} <<<`;
                consoleEL.appendChild(p);
                
                // Brief green pulse
                const normRemediated = data.last_remediated.replace(/-/g, '');
                const healedNode = Array.from(gridEl.children).find(n => n.id.replace(/-/g, '').includes(normRemediated));
                if(healedNode) healedNode.style.boxShadow = "0 0 20px #1fcc6e";
                setTimeout(() => { if(healedNode) healedNode.style.boxShadow = ""; }, 1500);
            }
            
            consoleEL.scrollTop = consoleEL.scrollHeight;

            // Status Badge Colors
            statusBadge.textContent = data.status;
            statusBadge.className = 'status-badge';
            
            if (data.flagged_containers.length > 0 || data.last_victim !== "-") {
                statusBadge.classList.add('alert');
                
                // Logic to start Hackathon Timer
                if (!isAnomalyActive) {
                    isAnomalyActive = true;
                    secondsElapsed = 0;
                    chaosBtn.disabled = true;
                    timeDisplay.className = 'sla-fail';
                    clearInterval(slaTimer);
                    slaTimer = setInterval(() => {
                        secondsElapsed += 0.1;
                        timeDisplay.textContent = secondsElapsed.toFixed(2) + 's';
                    }, 100);
                }
            } else if (data.status.includes("Remediation") && isAnomalyActive) {
                // Freeze Timer when Medic fixes it
                isAnomalyActive = false;
                clearInterval(slaTimer);
                chaosBtn.disabled = false;
                
                // SLA Check
                if (secondsElapsed <= 15.0) {
                    timeDisplay.className = 'sla-pass';
                } else {
                    timeDisplay.className = 'sla-fail';
                }
            } else if (!isAnomalyActive && (timeDisplay.textContent === '00.00s' || timeDisplay.className === '')) {
                 chaosBtn.disabled = false;
            }
            
        })
        .catch(err => console.error("Could not fetch state:", err));
}

// Chaos Injection Hook
chaosBtn.addEventListener('click', () => {
    chaosBtn.disabled = true;
    chaosBtn.innerHTML = '<span class="btn-icon">⚡</span> Injecting...';
    
    // Reset timer forcibly to begin the race
    clearInterval(slaTimer);
    secondsElapsed = 0;
    timeDisplay.textContent = '00.00s';
    timeDisplay.className = '';
    isAnomalyActive = false; // Reset to allow trigger logic via state cycle
    
    fetch('/api/anomaly', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            console.log("Admin targeted:", data);
            setTimeout(() => {
                chaosBtn.innerHTML = '<span class="btn-icon">⚡</span> Inject Anomaly';
            }, 1500);
            updateState(); // Immediate pull
        });
});

// Boot loop
initGrid();
setInterval(updateState, 1500);
