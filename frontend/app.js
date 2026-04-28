// frontend/app.js

const PIPELINE_STAGES = [
  { id: 'researcher',  label: 'Gathering intelligence',  progress: 14 },
  { id: 'classifier',  label: 'Classifying domains',     progress: 28 },
  { id: 'analyst',     label: 'Extracting insights',     progress: 43 },
  { id: 'devil',       label: 'Stress-testing claims',   progress: 57 },
  { id: 'synthesizer', label: 'Synthesizing findings',   progress: 71 },
  { id: 'visualizer',  label: 'Structuring report',      progress: 85 },
  { id: 'writer',      label: 'Writing final report',    progress: 95 },
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

let currentSessionId = null;
let currentTab       = 'executive';
let reportData       = null;

// ── Clock ───────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('topbarClock');
  if (el) el.textContent = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}
updateClock();
setInterval(updateClock, 1000);

// ── Example queries ─────────────────────────────────────────────
function setQuery(el) {
  document.getElementById('queryInput').value = el.textContent;
  document.getElementById('queryInput').focus();
}

// ── Start Research ──────────────────────────────────────────────
async function startResearch() {
  const query = document.getElementById('queryInput').value.trim();
  if (!query) return;

  document.getElementById('submitBtn').disabled = true;
  document.getElementById('querySection').classList.add('hidden');
  document.getElementById('pipelineSection').classList.remove('hidden');
  document.getElementById('reportSection').classList.add('hidden');

  resetAgentCards();
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

    setLog('Pipeline initialised. Starting research...');
    startStreaming();
  } catch (err) {
    setLog('ERROR: Failed to connect to ARIA backend.');
    document.getElementById('submitBtn').disabled = false;
    console.error(err);
  }
}

// ── Streaming (SSE) with polling fallback ───────────────────────
function startStreaming() {
  const evtSource = new EventSource(`/stream/${currentSessionId}`);

  evtSource.onmessage = async (e) => {
    const data = JSON.parse(e.data);
    updatePipelineUI(data.status);

    if (data.status === 'done') {
      evtSource.close();
      setProgress(100);
      setLog('Pipeline complete. Fetching report...');
      await loadReport(currentSessionId);
    } else if (data.status === 'failed') {
      evtSource.close();
      setLog('ERROR: Pipeline encountered a failure. Check server logs.');
      document.getElementById('submitBtn').disabled = false;
    }
  };

  evtSource.onerror = () => {
    evtSource.close();
    // Fallback to polling if SSE fails
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/status/${currentSessionId}`);
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

// ── Pipeline UI ─────────────────────────────────────────────────
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

// ── Report Loading ───────────────────────────────────────────────
async function loadReport(sessionId) {
  try {
    const [reportRes, statusRes] = await Promise.all([
      fetch(`/report/${sessionId}`),
      fetch(`/status/${sessionId}`)
    ]);
    reportData = await reportRes.json();
    const statusData = await statusRes.json();
    const meta = statusData.metadata || {};

    // Mark all agents done
    PIPELINE_STAGES.forEach(stage => {
      const node = document.getElementById(`agent-${stage.id}`);
      if (!node) return;
      node.classList.remove('active');
      node.classList.add('done');
      node.querySelector('.node-status').textContent = 'Complete';
    });

    // Stats
    const stats = [
      { label: 'FINDINGS',    value: meta.total_findings        ?? '–' },
      { label: 'INSIGHTS',    value: meta.insights_generated    ?? '–' },
      { label: 'CONFIDENCE',  value: meta.pipeline_confidence != null
                                       ? (meta.pipeline_confidence * 100).toFixed(0) + '%'
                                       : '–' },
      { label: 'CONNECTIONS', value: meta.cross_domain_connections ?? '–' },
      { label: 'WEAK CLAIMS', value: meta.weak_claims_ratio != null
                                       ? (meta.weak_claims_ratio * 100).toFixed(0) + '%'
                                       : '–' },
    ];

    document.getElementById('reportMeta').innerHTML = stats.map(s => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value">${s.value}</div>
      </div>`).join('');

    document.getElementById('pipelineSection').classList.add('hidden');
    document.getElementById('reportSection').classList.remove('hidden');
    showTab('executive');
  } catch (err) {
    setLog('ERROR: Failed to load report.');
    console.error(err);
  }
}

// ── Tab Switching ────────────────────────────────────────────────
function showTab(tab) {
  currentTab = tab;

  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });

  const content = document.getElementById('reportContent');
  content.classList.remove('is-technical');

  if (!reportData) {
    content.innerHTML = '<p style="color:var(--text-muted)">No report data.</p>';
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
    const raw = reportData.technical || reportData['technical'] || 'Not available.';
    content.textContent = raw;
    return;
  }

  const raw = reportData[tab] || 'Content not available.';
  content.innerHTML = renderMarkdown(raw);
}

// ── Markdown renderer ────────────────────────────────────────────
function renderMarkdown(text) {
  return text
    // Escape existing HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headings
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold / italic
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bullet lists (group consecutive lines)
    .replace(/((?:^[*\-] .+\n?)+)/gm, (match) => {
      const items = match.trim().split('\n')
        .map(l => `<li>${l.replace(/^[*\-] /, '')}</li>`).join('');
      return `<ul>${items}</ul>`;
    })
    // Blockquotes
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    // Paragraphs (double newlines)
    .replace(/\n{2,}/g, '</p><p>')
    // Single newlines
    .replace(/\n/g, '<br>')
    // Wrap in paragraph
    .replace(/^/, '<p>').replace(/$/, '</p>')
    // Clean up empty paragraphs around block elements
    .replace(/<p>(<(?:h[123]|ul|blockquote))/g, '$1')
    .replace(/(<\/(?:h[123]|ul|blockquote)>)<\/p>/g, '$1')
    .replace(/<p><\/p>/g, '');
}

// ── Reset ────────────────────────────────────────────────────────
function resetUI() {
  currentSessionId = null;
  reportData       = null;

  document.getElementById('queryInput').value  = '';
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('querySection').classList.remove('hidden');
  document.getElementById('pipelineSection').classList.add('hidden');
  document.getElementById('reportSection').classList.add('hidden');
  resetAgentCards();
}

// Enter key
document.getElementById('queryInput')
  .addEventListener('keydown', e => { if (e.key === 'Enter') startResearch(); });
