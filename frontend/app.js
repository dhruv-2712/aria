// frontend/app.js

const PIPELINE_STAGES = [
  { id: 'researcher',  label: 'Searching the web',         progress: 14 },
  { id: 'classifier',  label: 'Classifying domains',        progress: 28 },
  { id: 'analyst',     label: 'Extracting insights',        progress: 43 },
  { id: 'devil',       label: 'Stress-testing claims',      progress: 57 },
  { id: 'synthesizer', label: 'Synthesizing findings',      progress: 71 },
  { id: 'visualizer',  label: 'Structuring report',         progress: 85 },
  { id: 'writer',      label: 'Writing report (streaming)', progress: 95 },
];

const STATUS_TO_STAGE = {
  researching:  'researcher',
  classifying:  'classifier',
  analyzing:    'analyst',
  critiquing:   'devil',
  synthesizing: 'synthesizer',
  structuring:  'visualizer',
  writing:      'writer',
  done:         'done',
};

let currentSessionId  = null;
let currentTab        = 'executive';
let reportData        = null;
let streamingBuffer   = '';
let streamingDone     = false;
let streamRenderTimer = null;
let reportStreamSrc   = null;

// ── Clock ────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('topbarClock');
  if (el) el.textContent = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}
updateClock();
setInterval(updateClock, 1000);

// ── Example queries ──────────────────────────────────────────────
function setQuery(el) {
  document.getElementById('queryInput').value = el.textContent;
  document.getElementById('queryInput').focus();
}

// ── Start Research ───────────────────────────────────────────────
async function startResearch() {
  const query = document.getElementById('queryInput').value.trim();
  if (!query) return;

  document.getElementById('submitBtn').disabled = true;
  document.getElementById('querySection').classList.add('hidden');
  document.getElementById('pipelineSection').classList.remove('hidden');
  document.getElementById('reportSection').classList.add('hidden');

  resetAgentCards();
  streamingBuffer = '';
  streamingDone   = false;
  reportData      = null;
  setLog('Connecting to ARIA backend...');

  try {
    const res = await fetch('/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    currentSessionId = data.session_id;

    const sessionEl = document.getElementById('pipelineSession');
    if (sessionEl) sessionEl.textContent = `SESSION // ${currentSessionId.slice(0, 8).toUpperCase()}`;

    setLog('Pipeline initialised. Searching the web...');
    startStreaming();
  } catch (err) {
    setLog('ERROR: Failed to connect to ARIA backend.');
    document.getElementById('submitBtn').disabled = false;
    console.error(err);
  }
}

// ── Pipeline SSE ─────────────────────────────────────────────────
function startStreaming() {
  const evtSource = new EventSource(`/stream/${currentSessionId}`);

  evtSource.onmessage = async (e) => {
    const data = JSON.parse(e.data);
    updatePipelineUI(data.status);

    if (data.status === 'done') {
      evtSource.close();
      setProgress(100);
      setLog('Pipeline complete. Finalising report...');
      await loadReport(currentSessionId);
    } else if (data.status === 'failed') {
      evtSource.close();
      setLog('ERROR: Pipeline encountered a failure.');
      document.getElementById('submitBtn').disabled = false;
    }
  };

  evtSource.onerror = () => {
    evtSource.close();
    const interval = setInterval(async () => {
      try {
        const res  = await fetch(`/status/${currentSessionId}`);
        const data = await res.json();
        updatePipelineUI(data.status);
        if (data.status === 'done') {
          clearInterval(interval);
          setProgress(100);
          await loadReport(currentSessionId);
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setLog('ERROR: Pipeline failed.');
        }
      } catch (_) {}
    }, 2500);
  };
}

// ── Pipeline UI ──────────────────────────────────────────────────
function updatePipelineUI(status) {
  const stageId = STATUS_TO_STAGE[status];
  if (!stageId || stageId === 'done') return;

  const stageIndex = PIPELINE_STAGES.findIndex(s => s.id === stageId);
  if (stageIndex === -1) return;

  PIPELINE_STAGES.forEach((stage, i) => {
    const node = document.getElementById(`agent-${stage.id}`);
    if (!node) return;
    node.classList.remove('active', 'done');
    const statusEl = node.querySelector('.node-status');
    if (i < stageIndex) {
      node.classList.add('done');
      statusEl.textContent = 'Complete';
    } else if (i === stageIndex) {
      node.classList.add('active');
      statusEl.textContent = 'Running...';
    } else {
      statusEl.textContent = 'Standby';
    }
  });

  const stage = PIPELINE_STAGES[stageIndex];
  setProgress(stage.progress);
  setLog(stage.label + '...');

  // When writer starts, open report section and begin streaming
  if (stageId === 'writer' && currentSessionId) {
    startReportStream();
  }
}

function setProgress(pct) {
  document.getElementById('progressFill').style.width = `${pct}%`;
}

function setLog(msg) {
  const el = document.getElementById('logLine');
  if (el) el.textContent = msg;
}

function resetAgentCards() {
  PIPELINE_STAGES.forEach(stage => {
    const node = document.getElementById(`agent-${stage.id}`);
    if (!node) return;
    node.classList.remove('active', 'done');
    node.querySelector('.node-status').textContent = 'Standby';
  });
  setProgress(0);
}

// ── Report Streaming (executive tab live) ────────────────────────
function startReportStream() {
  if (reportStreamSrc) return; // already started

  document.getElementById('reportSection').classList.remove('hidden');
  document.getElementById('pipelineSection').classList.remove('hidden');

  // Prime the executive tab with a cursor
  _setStreamingContent('');

  reportStreamSrc = new EventSource(`/stream-report/${currentSessionId}`);

  reportStreamSrc.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.done) {
      reportStreamSrc.close();
      reportStreamSrc = null;
      streamingDone   = true;
      clearInterval(streamRenderTimer);
      // Final render of whatever we have (loadReport will overwrite with authoritative data)
      if (streamingBuffer && currentTab === 'executive') {
        document.getElementById('reportContent').innerHTML = renderMarkdown(streamingBuffer);
      }
    } else if (data.token) {
      streamingBuffer += data.token;
    }
  };

  reportStreamSrc.onerror = () => {
    if (reportStreamSrc) { reportStreamSrc.close(); reportStreamSrc = null; }
    clearInterval(streamRenderTimer);
  };

  // Throttled live render every 150ms
  streamRenderTimer = setInterval(() => {
    if (streamingBuffer && !streamingDone && currentTab === 'executive') {
      _setStreamingContent(streamingBuffer);
    }
  }, 150);
}

function _setStreamingContent(text) {
  const content = document.getElementById('reportContent');
  if (!content) return;
  content.innerHTML = (text ? renderMarkdown(text) : '') +
    '<span class="stream-cursor"></span>';
}

// ── Report Loading ────────────────────────────────────────────────
async function loadReport(sessionId) {
  try {
    const [reportRes, statusRes] = await Promise.all([
      fetch(`/report/${sessionId}`),
      fetch(`/status/${sessionId}`)
    ]);
    reportData = await reportRes.json();
    const meta = (await statusRes.json()).metadata || {};

    // All agents done
    PIPELINE_STAGES.forEach(stage => {
      const node = document.getElementById(`agent-${stage.id}`);
      if (!node) return;
      node.classList.remove('active');
      node.classList.add('done');
      node.querySelector('.node-status').textContent = 'Complete';
    });

    // Stats cards
    const stats = [
      { label: 'FINDINGS',    value: meta.total_findings        ?? '–' },
      { label: 'INSIGHTS',    value: meta.insights_generated    ?? '–' },
      { label: 'CONFIDENCE',  value: meta.pipeline_confidence != null
                                       ? (meta.pipeline_confidence * 100).toFixed(0) + '%' : '–' },
      { label: 'CONNECTIONS', value: meta.cross_domain_connections ?? '–' },
      { label: 'WEAK CLAIMS', value: meta.weak_claims_ratio != null
                                       ? (meta.weak_claims_ratio * 100).toFixed(0) + '%' : '–' },
    ];

    document.getElementById('reportMeta').innerHTML = stats.map(s => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value">${s.value}</div>
      </div>`).join('');

    document.getElementById('pipelineSection').classList.add('hidden');
    document.getElementById('reportSection').classList.remove('hidden');

    // Clear any streaming artifacts and render properly
    clearInterval(streamRenderTimer);
    showTab('executive');
  } catch (err) {
    setLog('ERROR: Failed to load report.');
    console.error(err);
  }
}

// ── Tab Switching ─────────────────────────────────────────────────
function showTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });

  const content = document.getElementById('reportContent');
  content.classList.remove('is-technical');

  if (!reportData) {
    // Still streaming — show buffer if executive, else placeholder
    if (tab === 'executive' && streamingBuffer) {
      _setStreamingContent(streamingBuffer);
    } else {
      content.innerHTML = '<p style="color:var(--text-muted);font-family:var(--mono);font-size:0.82rem">// Generating...</p>';
    }
    return;
  }

  if (tab === 'citations') {
    const citations = reportData.citations_json
      ? JSON.parse(reportData.citations_json)
      : (reportData.citations || []);
    if (!citations.length) {
      content.innerHTML = '<p style="color:var(--text-muted);font-family:var(--mono);font-size:0.82rem">// No citations recorded.</p>';
      return;
    }
    content.innerHTML = citations.map((c, i) => `
      <div class="citation-item">
        <span class="citation-index">[${String(i + 1).padStart(2, '0')}]</span>
        <span class="citation-url"><a href="${c.url}" target="_blank" rel="noopener">${c.url}</a></span>
        <span class="citation-conf">conf: ${c.confidence?.toFixed(2) ?? '–'}</span>
      </div>`).join('');
    return;
  }

  if (tab === 'technical') {
    content.classList.add('is-technical');
    content.textContent = reportData.technical || 'Not available.';
    return;
  }

  const raw = reportData[tab] || 'Content not available.';
  content.innerHTML = renderMarkdown(raw);
}

// ── Markdown renderer ─────────────────────────────────────────────
function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`([^`]+)`/g,     '<code>$1</code>')
    .replace(/((?:^[*\-] .+\n?)+)/gm, (match) => {
      const items = match.trim().split('\n')
        .map(l => `<li>${l.replace(/^[*\-] /, '')}</li>`).join('');
      return `<ul>${items}</ul>`;
    })
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^/, '<p>').replace(/$/, '</p>')
    .replace(/<p>(<(?:h[123]|ul|blockquote))/g, '$1')
    .replace(/(<\/(?:h[123]|ul|blockquote)>)<\/p>/g, '$1')
    .replace(/<p><\/p>/g, '');
}

// ── Export ────────────────────────────────────────────────────────
function downloadMarkdown() {
  if (!reportData) return;
  const tab  = currentTab === 'citations' || currentTab === 'technical' ? currentTab : currentTab;
  let content = '';
  if (tab === 'citations') {
    const citations = reportData.citations_json
      ? JSON.parse(reportData.citations_json) : (reportData.citations || []);
    content = citations.map((c, i) => `[${i+1}] ${c.url} (confidence: ${c.confidence?.toFixed(2)})`).join('\n');
  } else {
    content = reportData[tab] || '';
  }
  if (!content) return;
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `aria-${tab}-${currentSessionId?.slice(0,8) || 'report'}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function printReport() {
  if (!reportData) return;
  // Ensure executive tab is shown for print (most readable)
  showTab(currentTab);
  window.print();
}

// ── History ───────────────────────────────────────────────────────
let historyOpen = false;

function toggleHistory() {
  historyOpen = !historyOpen;
  const panel = document.getElementById('historyPanel');
  if (historyOpen) {
    panel.classList.remove('hidden');
    loadHistory();
  } else {
    panel.classList.add('hidden');
  }
}

async function loadHistory() {
  const list = document.getElementById('historyList');
  try {
    const res      = await fetch('/sessions');
    const sessions = await res.json();
    if (!sessions.length) {
      list.innerHTML = '<div class="history-empty">No completed sessions yet.</div>';
      return;
    }
    list.innerHTML = sessions.map(s => `
      <div class="history-item" onclick="loadHistoricalReport('${s.id}')">
        <div class="history-query">${escapeHtml(s.query)}</div>
        <div class="history-meta">
          <span>${s.created_at.replace('T', ' ').slice(0, 16)}</span>
          <span style="color:var(--success)">✓ done</span>
        </div>
      </div>`).join('');
  } catch (err) {
    list.innerHTML = '<div class="history-empty">Failed to load history.</div>';
  }
}

async function loadHistoricalReport(sessionId) {
  toggleHistory();
  document.getElementById('querySection').classList.add('hidden');
  document.getElementById('pipelineSection').classList.add('hidden');

  currentSessionId = sessionId;
  reportData = null;

  document.getElementById('reportSection').classList.remove('hidden');
  document.getElementById('reportContent').innerHTML =
    '<p style="color:var(--text-muted);font-family:var(--mono);font-size:0.82rem">// Loading report...</p>';

  try {
    const [reportRes, statusRes] = await Promise.all([
      fetch(`/report/${sessionId}`),
      fetch(`/status/${sessionId}`)
    ]);
    reportData = await reportRes.json();
    const meta = (await statusRes.json()).metadata || {};

    const stats = [
      { label: 'FINDINGS',    value: meta.total_findings        ?? '–' },
      { label: 'INSIGHTS',    value: meta.insights_generated    ?? '–' },
      { label: 'CONFIDENCE',  value: meta.pipeline_confidence != null
                                       ? (meta.pipeline_confidence * 100).toFixed(0) + '%' : '–' },
      { label: 'CONNECTIONS', value: meta.cross_domain_connections ?? '–' },
    ];
    document.getElementById('reportMeta').innerHTML = stats.map(s => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value">${s.value}</div>
      </div>`).join('');

    document.getElementById('submitBtn').disabled = false;
    showTab('executive');
  } catch (err) {
    document.getElementById('reportContent').innerHTML =
      '<p style="color:var(--error);font-family:var(--mono)">Failed to load report.</p>';
  }
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Reset ─────────────────────────────────────────────────────────
function resetUI() {
  currentSessionId  = null;
  reportData        = null;
  streamingBuffer   = '';
  streamingDone     = false;
  clearInterval(streamRenderTimer);
  if (reportStreamSrc) { reportStreamSrc.close(); reportStreamSrc = null; }

  document.getElementById('queryInput').value   = '';
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('querySection').classList.remove('hidden');
  document.getElementById('pipelineSection').classList.add('hidden');
  document.getElementById('reportSection').classList.add('hidden');
  resetAgentCards();
}

// Enter key
document.getElementById('queryInput')
  .addEventListener('keydown', e => { if (e.key === 'Enter') startResearch(); });

// Close history when clicking outside
document.addEventListener('click', (e) => {
  if (!historyOpen) return;
  const panel = document.getElementById('historyPanel');
  const btn   = document.getElementById('historyBtn');
  if (!panel.contains(e.target) && !btn.contains(e.target)) {
    historyOpen = false;
    panel.classList.add('hidden');
  }
});
