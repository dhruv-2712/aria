// frontend/app.js

const PIPELINE_STAGES = [
    { id: 'researcher', label: 'Researching', progress: 14 },
    { id: 'classifier', label: 'Classifying', progress: 28 },
    { id: 'analyst', label: 'Analyzing', progress: 42 },
    { id: 'devil', label: 'Critiquing', progress: 57 },
    { id: 'synthesizer', label: 'Synthesizing', progress: 71 },
    { id: 'visualizer', label: 'Structuring', progress: 85 },
    { id: 'writer', label: 'Writing', progress: 95 },
];

const STATUS_TO_STAGE = {
    researching: 'researcher',
    classifying: 'classifier',
    analyzing: 'analyst',
    critiquing: 'devil',
    synthesizing: 'synthesizer',
    structuring: 'visualizer',
    writing: 'writer',
    done: 'done',
};

let pollInterval = null;
let currentSessionId = null;
let currentTab = 'executive';
let reportData = null;

// ── Start Research ──────────────────────────────────────────────
// Replace startResearch() in app.js with this:
async function startResearch() {
    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;

    document.getElementById('submitBtn').disabled = true;
    document.getElementById('querySection').classList.add('hidden');
    document.getElementById('pipelineSection').classList.remove('hidden');
    document.getElementById('reportSection').classList.add('hidden');

    resetAgentCards();
    setStatus('Sending query to ARIA...');

    try {
        const res = await fetch('/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        currentSessionId = data.session_id;  // use the real ID from response
        startPolling();
    } catch (err) {
        setStatus('Failed to connect to ARIA backend.');
        console.error(err);
    }
}

// Replace pollStatus() with this:
async function pollStatus() {
    if (!currentSessionId) return;
    try {
        const res = await fetch(`/status/${currentSessionId}`);
        const data = await res.json();
        const status = data.status;

        updatePipelineUI(status);

        if (status === 'done') {
            clearInterval(pollInterval);
            setProgress(100);
            setStatus('Pipeline complete. Loading report...');
            await loadReport(currentSessionId);
        } else if (status === 'failed') {
            clearInterval(pollInterval);
            setStatus('Pipeline encountered an error. Check terminal for details.');
            document.getElementById('submitBtn').disabled = false;
        }
    } catch (err) {
        console.error('Poll error:', err);
    }
}

// ── Polling ─────────────────────────────────────────────────────
function startPolling() {
    const evtSource = new EventSource(`/stream/${currentSessionId}`);
    evtSource.onmessage = async (e) => {
        const data = JSON.parse(e.data);
        updatePipelineUI(data.status);
        if (data.status === 'done') {
            evtSource.close();
            setProgress(100);
            await loadReport(currentSessionId);
        } else if (data.status === 'failed') {
            evtSource.close();
            setStatus('Pipeline failed. Check terminal.');
        }
    };
}

async function pollStatus() {
    try {
        const res = await fetch('/status/latest');
        const data = await res.json();

        const status = data.status;
        const sessionId = data.session_id;

        if (sessionId) currentSessionId = sessionId;

        updatePipelineUI(status);

        if (status === 'done') {
            clearInterval(pollInterval);
            setProgress(100);
            setStatus('Pipeline complete. Loading report...');
            await loadReport(sessionId);
        } else if (status === 'failed') {
            clearInterval(pollInterval);
            setStatus('Pipeline encountered an error. Check logs.');
        }
    } catch (err) {
        console.error('Poll error:', err);
    }
}

// ── UI Updates ───────────────────────────────────────────────────
function updatePipelineUI(status) {
    const stageId = STATUS_TO_STAGE[status];
    if (!stageId || stageId === 'done') return;

    const stageIndex = PIPELINE_STAGES.findIndex(s => s.id === stageId);
    if (stageIndex === -1) return;

    // Mark previous stages done, current active
    PIPELINE_STAGES.forEach((stage, i) => {
        const card = document.getElementById(`agent-${stage.id}`);
        if (!card) return;
        card.classList.remove('active', 'done');
        if (i < stageIndex) {
            card.classList.add('done');
            card.querySelector('.agent-status').textContent = '✓ Done';
        } else if (i === stageIndex) {
            card.classList.add('active');
            card.querySelector('.agent-status').textContent = 'Running...';
        } else {
            card.querySelector('.agent-status').textContent = 'Waiting';
        }
    });

    setProgress(PIPELINE_STAGES[stageIndex].progress);
    setStatus(`${PIPELINE_STAGES[stageIndex].label}...`);
}

function setProgress(pct) {
    document.getElementById('progressFill').style.width = `${pct}%`;
}

function setStatus(msg) {
    document.getElementById('statusText').textContent = msg;
}

function resetAgentCards() {
    PIPELINE_STAGES.forEach(stage => {
        const card = document.getElementById(`agent-${stage.id}`);
        if (!card) return;
        card.classList.remove('active', 'done');
        card.querySelector('.agent-status').textContent = 'Waiting';
    });
    setProgress(0);
}

// ── Report Loading ───────────────────────────────────────────────
async function loadReport(sessionId) {
    try {
        const res = await fetch(`/report/${sessionId}`);
        reportData = await res.json();

        // Mark all agents done
        PIPELINE_STAGES.forEach(stage => {
            const card = document.getElementById(`agent-${stage.id}`);
            if (card) {
                card.classList.remove('active');
                card.classList.add('done');
                card.querySelector('.agent-status').textContent = '✓ Done';
            }
        });

        // Populate metadata
        const statusRes = await fetch(`/status/${sessionId}`);
        const statusData = await statusRes.json();
        const meta = statusData.metadata || {};

        document.getElementById('reportMeta').innerHTML = `
      <span>🔍 <strong>${meta.total_findings ?? '–'}</strong> findings</span>
      <span>💡 <strong>${meta.insights_generated ?? '–'}</strong> insights</span>
      <span>📊 Confidence: <strong>${meta.pipeline_confidence ? (meta.pipeline_confidence * 100).toFixed(0) + '%' : '–'}</strong></span>
      <span>🔗 <strong>${meta.cross_domain_connections ?? '–'}</strong> connections</span>
      <span>⚠️ Weak claims: <strong>${meta.weak_claims_ratio ? (meta.weak_claims_ratio * 100).toFixed(0) + '%' : '–'}</strong></span>
    `;

        document.getElementById('pipelineSection').classList.add('hidden');
        document.getElementById('reportSection').classList.remove('hidden');
        showTab('executive');

    } catch (err) {
        setStatus('Error loading report.');
        console.error(err);
    }
}

// ── Tab Switching ────────────────────────────────────────────────
function showTab(tab) {
    currentTab = tab;

    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab')[
        ['executive', 'standard', 'technical', 'citations'].indexOf(tab)
    ].classList.add('active');

    const content = document.getElementById('reportContent');

    if (!reportData) {
        content.textContent = 'No report data available.';
        return;
    }

    if (tab === 'citations') {
        const citations = reportData.citations_json
            ? JSON.parse(reportData.citations_json)
            : reportData.citations || [];

        if (!citations.length) {
            content.innerHTML = '<p style="color:var(--text-muted)">No citations recorded.</p>';
            return;
        }
        content.innerHTML = citations.map((c, i) =>
            `<div class="citation-item">
        [${i + 1}] <a href="${c.url}" target="_blank">${c.url}</a>
        <span style="color:var(--text-muted);float:right">conf: ${c.confidence?.toFixed(2) ?? '–'}</span>
      </div>`
        ).join('');
        return;
    }

    const fieldMap = {
        executive: 'executive',
        standard: 'standard',
        technical: 'technical'
    };
    const raw = reportData[fieldMap[tab]] || 'Content not available.';

    // Render basic markdown (##, **bold**)
    content.innerHTML = raw
        .replace(/## (.+)/g, '<h2>$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

// ── Reset ────────────────────────────────────────────────────────
function resetUI() {
    clearInterval(pollInterval);
    currentSessionId = null;
    reportData = null;

    document.getElementById('queryInput').value = '';
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('querySection').classList.remove('hidden');
    document.getElementById('pipelineSection').classList.add('hidden');
    document.getElementById('reportSection').classList.add('hidden');
    resetAgentCards();
}

// Allow Enter key to submit
document.getElementById('queryInput')
    .addEventListener('keydown', e => { if (e.key === 'Enter') startResearch(); });