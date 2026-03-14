const HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sovreign AI \u2014 Malaysia Content Moderation</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0c0e13;
    --surface: #14171f;
    --surface-2: #1c2029;
    --border: #2a2e3a;
    --text: #e8e6e3;
    --text-dim: #8b8d94;
    --accent: #d4a853;
    --accent-glow: rgba(212, 168, 83, 0.15);
    --safe: #3dd68c;
    --safe-bg: rgba(61, 214, 140, 0.08);
    --unsafe: #f25f5c;
    --unsafe-bg: rgba(242, 95, 92, 0.08);
    --s0: #3dd68c;
    --s1: #f2c94c;
    --s2: #f2994a;
    --s3: #f25f5c;
    --radius: 12px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
  }
  header {
    padding: 32px 48px;
    display: flex;
    align-items: baseline;
    gap: 16px;
    border-bottom: 1px solid var(--border);
  }
  .logo {
    font-family: 'Instrument Serif', serif;
    font-size: 28px;
    color: var(--accent);
    letter-spacing: -0.5px;
  }
  .logo-sub {
    font-size: 14px;
    color: var(--text-dim);
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .model-badge {
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-dim);
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 6px 14px;
    border-radius: 20px;
    letter-spacing: 0.5px;
  }
  main {
    max-width: 880px;
    margin: 0 auto;
    padding: 48px 24px 120px;
  }
  .hero {
    text-align: center;
    margin-bottom: 48px;
    animation: fadeUp 0.6s ease-out;
  }
  .hero h1 {
    font-family: 'Instrument Serif', serif;
    font-size: 44px;
    font-weight: 400;
    line-height: 1.2;
    margin-bottom: 12px;
    background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hero p {
    font-size: 16px;
    color: var(--text-dim);
    font-weight: 300;
    max-width: 560px;
    margin: 0 auto;
    line-height: 1.6;
  }
  .input-section { animation: fadeUp 0.6s ease-out 0.1s both; }
  .input-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: border-color 0.3s;
  }
  .input-card:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent), 0 0 40px var(--accent-glow);
  }
  .input-label {
    padding: 16px 20px 0;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 500;
  }
  textarea {
    width: 100%;
    min-height: 140px;
    padding: 12px 20px 16px;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-family: 'Outfit', sans-serif;
    font-size: 16px;
    font-weight: 300;
    line-height: 1.7;
    resize: vertical;
  }
  textarea::placeholder { color: var(--text-dim); opacity: 0.5; }
  .input-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    border-top: 1px solid var(--border);
    background: var(--surface-2);
  }
  .char-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-dim);
  }
  button.analyze {
    font-family: 'Outfit', sans-serif;
    font-size: 14px;
    font-weight: 500;
    padding: 10px 28px;
    background: var(--accent);
    color: var(--bg);
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.3px;
  }
  button.analyze:hover {
    background: #e0b45e;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px var(--accent-glow);
  }
  button.analyze:active { transform: translateY(0); }
  button.analyze:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .examples {
    margin-top: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    animation: fadeUp 0.6s ease-out 0.2s both;
  }
  .examples-label {
    font-size: 12px;
    color: var(--text-dim);
    width: 100%;
    margin-bottom: 4px;
    font-weight: 400;
  }
  .example-chip {
    font-family: 'Outfit', sans-serif;
    font-size: 12px;
    padding: 6px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    color: var(--text-dim);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .example-chip:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-glow);
  }
  .loading-overlay {
    display: none;
    text-align: center;
    padding: 48px;
    animation: fadeUp 0.3s ease-out;
  }
  .loading-overlay.visible { display: block; }
  .spinner {
    width: 40px;
    height: 40px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 16px;
  }
  .loading-text { font-size: 14px; color: var(--text-dim); font-weight: 300; }
  .result-section {
    display: none;
    margin-top: 32px;
    animation: fadeUp 0.5s ease-out;
  }
  .result-section.visible { display: block; }
  .verdict-banner {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 24px 28px;
    border-radius: var(--radius);
    margin-bottom: 20px;
    animation: slideIn 0.4s ease-out;
  }
  .verdict-banner.safe {
    background: var(--safe-bg);
    border: 1px solid rgba(61, 214, 140, 0.2);
  }
  .verdict-banner.unsafe {
    background: var(--unsafe-bg);
    border: 1px solid rgba(242, 95, 92, 0.2);
  }
  .verdict-icon {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
  }
  .safe .verdict-icon { background: rgba(61, 214, 140, 0.15); }
  .unsafe .verdict-icon { background: rgba(242, 95, 92, 0.15); }
  .verdict-text h2 {
    font-family: 'Instrument Serif', serif;
    font-size: 28px;
    font-weight: 400;
    margin-bottom: 4px;
  }
  .safe .verdict-text h2 { color: var(--safe); }
  .unsafe .verdict-text h2 { color: var(--unsafe); }
  .verdict-text p { font-size: 14px; color: var(--text-dim); font-weight: 300; }
  .severity-badge {
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 8px;
    flex-shrink: 0;
  }
  .severity-S0 { color: var(--s0); background: rgba(61, 214, 140, 0.1); }
  .severity-S1 { color: var(--s1); background: rgba(242, 201, 76, 0.1); }
  .severity-S2 { color: var(--s2); background: rgba(242, 153, 74, 0.1); }
  .severity-S3 { color: var(--s3); background: rgba(242, 95, 92, 0.1); }
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }
  .detail-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    animation: fadeUp 0.4s ease-out;
  }
  .detail-card.full { grid-column: 1 / -1; }
  .detail-card h3 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-dim);
    margin-bottom: 12px;
    font-weight: 500;
  }
  .detail-card p { font-size: 14px; line-height: 1.7; font-weight: 300; color: var(--text); }
  .tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 5px 12px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--accent);
    letter-spacing: 0.3px;
  }
  .tag.risk {
    color: var(--unsafe);
    border-color: rgba(242, 95, 92, 0.2);
    background: var(--unsafe-bg);
  }
  .tag.none { color: var(--text-dim); font-style: italic; }
  .reasoning-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 20px;
    animation: fadeUp 0.4s ease-out 0.1s both;
  }
  .reasoning-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.2s;
  }
  .reasoning-header:hover { background: var(--surface-2); }
  .reasoning-header h3 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 500;
  }
  .reasoning-toggle {
    margin-left: auto;
    font-size: 11px;
    color: var(--text-dim);
    transition: transform 0.3s;
  }
  .reasoning-body {
    padding: 20px;
    font-size: 14px;
    line-height: 1.8;
    color: var(--text);
    font-weight: 300;
    border-left: 3px solid var(--accent);
    margin: 0 20px 20px;
    padding-left: 16px;
    font-style: italic;
    opacity: 0.9;
  }
  .reasoning-body.collapsed { display: none; }
  .rewrite-card {
    background: var(--surface);
    border: 1px solid rgba(212, 168, 83, 0.2);
    border-radius: var(--radius);
    padding: 20px;
    animation: fadeUp 0.4s ease-out 0.2s both;
  }
  .rewrite-card h3 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent);
    margin-bottom: 12px;
    font-weight: 500;
  }
  .rewrite-card p { font-size: 14px; line-height: 1.7; font-weight: 300; }
  footer {
    text-align: center;
    padding: 32px;
    border-top: 1px solid var(--border);
    margin-top: 64px;
  }
  footer p { font-size: 12px; color: var(--text-dim); font-weight: 300; letter-spacing: 0.5px; }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (max-width: 640px) {
    header { padding: 20px 24px; flex-wrap: wrap; }
    .model-badge { margin-left: 0; margin-top: 8px; }
    .hero h1 { font-size: 32px; }
    main { padding: 32px 16px 80px; }
    .detail-grid { grid-template-columns: 1fr; }
    .verdict-banner { flex-wrap: wrap; }
    .severity-badge { margin-left: 0; }
  }
</style>
</head>
<body>
<header>
  <span class="logo">Sovreign</span>
  <span class="logo-sub">Content Moderation</span>
  <span class="model-badge">Qwen3 0.6B CoT &middot; 73% accuracy</span>
</header>
<main>
  <div class="hero">
    <h1>Malaysia Content Moderator</h1>
    <p>Analyze Malaysian text for harmful content using a fine-tuned language model with chain-of-thought reasoning. Detects communal hostility, religious provocation, misinformation, and more.</p>
  </div>
  <div class="input-section">
    <div class="input-card">
      <div class="input-label">Input Text</div>
      <textarea id="input" placeholder="Masukkan teks untuk dianalisis... / Enter text to analyze..."></textarea>
      <div class="input-footer">
        <span class="char-count"><span id="charCount">0</span> chars</span>
        <button class="analyze" id="analyzeBtn" onclick="analyze()">Analyze</button>
      </div>
    </div>
    <div class="examples">
      <span class="examples-label">Try an example:</span>
      <span class="example-chip" onclick="loadExample(0)">Safe \u2014 everyday chat</span>
      <span class="example-chip" onclick="loadExample(1)">Safe \u2014 quoting to condemn</span>
      <span class="example-chip" onclick="loadExample(2)">Unsafe \u2014 communal hostility</span>
      <span class="example-chip" onclick="loadExample(3)">Unsafe \u2014 political sarcasm</span>
      <span class="example-chip" onclick="loadExample(4)">Safe \u2014 pro-social defense</span>
      <span class="example-chip" onclick="loadExample(5)">Unsafe \u2014 coded euphemism</span>
    </div>
  </div>
  <div class="loading-overlay" id="loading">
    <div class="spinner"></div>
    <div class="loading-text">Analyzing content with chain-of-thought reasoning...</div>
  </div>
  <div class="result-section" id="results"></div>
</main>
<footer>
  <p>Sovreign AI &middot; Malaysia Content Moderation &middot; Qwen3 0.6B fine-tuned with CoT reasoning</p>
</footer>
<script>
const EXAMPLES = [
  "Hari ini cuaca sangat panas. Jom minum air kelapa kat pantai!",
  "'Balik tongsan lah kalau tak suka!' \\u2014 overheard this at the kopitiam. 2024 and people still talk like this. Memalukan.",
  "Semua orang kaum X memang pemalas dan suka curi. Jangan bagi mereka peluang.",
  "Haha PM cakap rakyat didahulukan. Lawak terbaik 2024. Meanwhile kawan dia dapat projek billion.",
  "Eh jangan lah cakap macam tu pasal orang India. Kawan aku pun Indian, baik orangnya.",
  "Kawasan ni dulu ramai orang kita, sekarang dah jadi macam Little India. Tak selesa dah nak jalan."
];
const textarea = document.getElementById('input');
const charCount = document.getElementById('charCount');
textarea.addEventListener('input', () => { charCount.textContent = textarea.value.length; });
function loadExample(idx) {
  textarea.value = EXAMPLES[idx];
  charCount.textContent = textarea.value.length;
  textarea.focus();
}
async function analyze() {
  const text = textarea.value.trim();
  if (!text) return;
  const btn = document.getElementById('analyzeBtn');
  const loading = document.getElementById('loading');
  const results = document.getElementById('results');
  btn.disabled = true;
  loading.classList.add('visible');
  results.classList.remove('visible');
  try {
    const res = await fetch('/api/moderate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    results.innerHTML = '<div class="detail-card full"><h3>Error</h3><p>' + err.message + '</p></div>';
    results.classList.add('visible');
  } finally {
    btn.disabled = false;
    loading.classList.remove('visible');
  }
}
function renderResults(data) {
  const results = document.getElementById('results');
  const v = data.verdict || {};
  const isSafe = v.safe !== false;
  const severity = v.severity || 'S0';
  const reason = v.reason || 'No reason provided';
  const principles = v.triggered_principles || [];
  const risks = v.risk_labels || [];
  const reasoning = data.reasoning || '';
  const rewrite = v.suggested_rewrite || '';
  const needsRewrite = v.rewrite_required === true;
  const safeClass = isSafe ? 'safe' : 'unsafe';
  const safeLabel = isSafe ? 'Safe Content' : 'Unsafe Content';
  const safeDesc = isSafe ? 'This content is within acceptable guidelines.' : 'This content may violate moderation guidelines.';
  const safeIcon = isSafe ? '\\u2713' : '\\u2717';
  let html = '<div class="verdict-banner ' + safeClass + '">' +
    '<div class="verdict-icon">' + safeIcon + '</div>' +
    '<div class="verdict-text"><h2>' + safeLabel + '</h2><p>' + safeDesc + '</p></div>' +
    '<div class="severity-badge severity-' + severity + '">' + severity + '</div></div>';
  if (reasoning) {
    html += '<div class="reasoning-card"><div class="reasoning-header" onclick="toggleReasoning()">' +
      '<h3>Model Reasoning</h3><span class="reasoning-toggle" id="reasoningToggle">\\u25BC</span></div>' +
      '<div class="reasoning-body" id="reasoningBody">' + escapeHtml(reasoning) + '</div></div>';
  }
  html += '<div class="detail-grid">';
  html += '<div class="detail-card full"><h3>Reason</h3><p>' + escapeHtml(reason) + '</p></div>';
  html += '<div class="detail-card"><h3>Triggered Principles</h3><div class="tag-list">' +
    (principles.length > 0 ? principles.map(function(p) { return '<span class="tag">' + escapeHtml(p) + '</span>'; }).join('') : '<span class="tag none">None</span>') +
    '</div></div>';
  html += '<div class="detail-card"><h3>Risk Labels</h3><div class="tag-list">' +
    (risks.length > 0 ? risks.map(function(r) { return '<span class="tag risk">' + escapeHtml(r) + '</span>'; }).join('') : '<span class="tag none">None</span>') +
    '</div></div>';
  html += '</div>';
  if (needsRewrite && rewrite) {
    html += '<div class="rewrite-card"><h3>Suggested Rewrite</h3><p>' + escapeHtml(rewrite) + '</p></div>';
  }
  results.innerHTML = html;
  results.classList.add('visible');
}
function toggleReasoning() {
  const body = document.getElementById('reasoningBody');
  const toggle = document.getElementById('reasoningToggle');
  body.classList.toggle('collapsed');
  toggle.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
}
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
textarea.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); analyze(); }
});
</script>
</body>
</html>`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Serve the frontend
    if (url.pathname === "/" || url.pathname === "/index.html") {
      return new Response(HTML, {
        headers: { "Content-Type": "text/html;charset=utf-8" },
      });
    }

    // Proxy API calls to HuggingFace Space
    if (url.pathname === "/api/moderate" && request.method === "POST") {
      const backendUrl = `${env.HF_SPACE_URL}/api/moderate`;
      try {
        const body = await request.text();
        const resp = await fetch(backendUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
        });
        const data = await resp.text();
        return new Response(data, {
          status: resp.status,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        });
      } catch (err) {
        return new Response(
          JSON.stringify({ error: "Backend unavailable", detail: err.message }),
          { status: 502, headers: { "Content-Type": "application/json" } }
        );
      }
    }

    // Health check
    if (url.pathname === "/api/health") {
      return new Response(
        JSON.stringify({ status: "ok", backend: env.HF_SPACE_URL }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
};
