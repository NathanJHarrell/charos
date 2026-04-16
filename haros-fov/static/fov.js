/* HAROS-FOV — Client logic: hash routing, xterm.js terminals, WebSocket management */

const REFRESH_MS = 5000;
const TERM_THEME = {
  background: '#1a1a1a',
  foreground: '#e8e8e8',
  cursor: '#FF5900',
  cursorAccent: '#1a1a1a',
  selectionBackground: 'rgba(255, 89, 0, 0.3)',
  black: '#1a1a1a',
  red: '#ff4444',
  green: '#66CC88',
  yellow: '#ffaa00',
  blue: '#6699ff',
  magenta: '#B48CFF',
  cyan: '#66cccc',
  white: '#e8e8e8',
  brightBlack: '#555555',
  brightRed: '#ff6666',
  brightGreen: '#88eebb',
  brightYellow: '#ffcc44',
  brightBlue: '#88bbff',
  brightMagenta: '#cc99ff',
  brightCyan: '#88eeee',
  brightWhite: '#ffffff',
};

const FONT_FAMILY = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace";

// ── State ──────────────────────────────────────────────

let activeTerminals = [];  // [{term, ws, fitAddon, el}]
let refreshTimer = null;

// ── Helpers ────────────────────────────────────────────

function formatAge(seconds) {
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}${path}`;
}

// ── Cleanup ────────────────────────────────────────────

function destroyTerminals() {
  for (const t of activeTerminals) {
    if (t.ws && t.ws.readyState <= 1) t.ws.close();
    if (t.term) t.term.dispose();
  }
  activeTerminals = [];
}

function stopRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

// ── Router ─────────────────────────────────────────────

function route() {
  stopRefresh();
  destroyTerminals();

  const hash = location.hash || '#/';
  const app = document.getElementById('app');
  const breadcrumb = document.getElementById('header-breadcrumb');
  breadcrumb.textContent = '';

  // Landing page
  if (hash === '#/' || hash === '#/builds' || hash === '') {
    renderLanding(app);
    return;
  }

  // Build page: #/build/{machine}/{name}
  const buildMatch = hash.match(/^#\/build\/([^/]+)\/([^/]+)$/);
  if (buildMatch) {
    const [, machine, build] = buildMatch;
    breadcrumb.textContent = `› ${machine} › ${build}`;
    renderBuild(app, machine, build);
    return;
  }

  // Full view: #/build/{machine}/{name}/{label}
  const fullMatch = hash.match(/^#\/build\/([^/]+)\/([^/]+)\/(.+)$/);
  if (fullMatch) {
    const [, machine, build, label] = fullMatch;
    breadcrumb.textContent = `› ${machine} › ${build} › ${label}`;
    renderFullView(app, machine, build, label);
    return;
  }

  // Fallback
  app.innerHTML = '<div class="no-builds">Unknown route</div>';
}

// ── Landing Page ───────────────────────────────────────

async function fetchAllBuilds() {
  const builds = [];

  // Local builds
  try {
    const res = await fetch('/api/builds');
    const local = await res.json();
    builds.push(...local);
  } catch (e) {
    console.error('Failed to fetch local builds:', e);
  }

  // Remote builds
  try {
    const machRes = await fetch('/api/machines');
    const machines = await machRes.json();

    for (const m of machines) {
      if (m.local || !m.reachable) continue;
      try {
        const res = await fetch(`/api/machines/${m.hostname}/builds`);
        const remote = await res.json();
        if (Array.isArray(remote)) builds.push(...remote);
      } catch (e) {
        console.error(`Failed to fetch builds from ${m.hostname}:`, e);
      }
    }

    // Update machine status indicators
    renderMachineStatus(machines);
  } catch (e) {
    console.error('Failed to fetch machines:', e);
  }

  return builds;
}

function renderMachineStatus(machines) {
  const el = document.getElementById('machine-status');
  el.innerHTML = machines.map(m =>
    `<span class="machine-dot ${m.reachable ? 'online' : 'offline'}"></span>${m.hostname}`
  ).join('  ');
}

async function renderLanding(app) {
  async function update() {
    const builds = await fetchAllBuilds();

    if (builds.length === 0) {
      app.innerHTML = `
        <div class="no-builds">
          No active HAROS builds
          <div class="hint">Start a build with: haros spawn &lt;build&gt; &lt;label&gt;</div>
        </div>`;
      return;
    }

    app.innerHTML = `<div class="builds-grid">${builds.map(b => `
      <div class="build-card" onclick="location.hash='#/build/${b.machine}/${b.name}'">
        <div class="build-card-header">
          <span class="build-name">${b.name}</span>
          <span class="build-machine">${b.machine}</span>
        </div>
        <div class="build-meta">${b.session_count} session${b.session_count !== 1 ? 's' : ''} · started ${formatAge(b.age_seconds)}</div>
        <div class="build-sessions">
          ${b.sessions.map(s => `
            <span class="session-tag ${s.attached ? 'attached' : 'detached'}">${s.label}</span>
          `).join('')}
        </div>
      </div>
    `).join('')}</div>`;
  }

  await update();
  refreshTimer = setInterval(update, REFRESH_MS);
}

// ── Build Page (Overview) ──────────────────────────────

async function renderBuild(app, machine, buildName) {
  // Fetch build data
  let build;
  try {
    const res = await fetch(machine === location.hostname || isLocalMachine(machine)
      ? `/api/builds/${buildName}`
      : `/api/machines/${machine}/builds`);
    const data = await res.json();

    if (Array.isArray(data)) {
      build = data.find(b => b.name === buildName);
    } else {
      build = data;
    }
  } catch (e) {
    app.innerHTML = `<div class="no-builds">Failed to load build: ${e.message}</div>`;
    return;
  }

  if (!build || !build.sessions) {
    app.innerHTML = `<div class="no-builds">Build "${buildName}" not found on ${machine}</div>`;
    return;
  }

  // Build the grid
  app.innerHTML = `<div class="terminal-grid" id="term-grid"></div>`;
  const grid = document.getElementById('term-grid');

  for (const session of build.sessions) {
    const tile = document.createElement('div');
    tile.className = 'terminal-tile';
    tile.innerHTML = `
      <div class="tile-header">
        <span class="tile-label">${session.label}</span>
        <span class="tile-status ${session.attached ? 'attached' : ''}">${session.attached ? 'attached' : 'idle ' + formatAge(session.idle_seconds)}</span>
      </div>
      <div class="tile-terminal" id="term-${session.name}"></div>
    `;

    // Click to full view
    tile.addEventListener('click', (e) => {
      // Don't navigate if clicking inside the terminal
      if (e.target.closest('.xterm')) return;
      location.hash = `#/build/${machine}/${buildName}/${session.label}`;
    });

    grid.appendChild(tile);

    // Create terminal
    const termEl = tile.querySelector(`#term-${session.name}`);
    createTerminal(termEl, session.name, machine, {
      fontSize: 14,
      disableStdin: false,  // allow typing even in overview
    });
  }
}

// ── Full View ──────────────────────────────────────────

function renderFullView(app, machine, buildName, label) {
  const sessionName = `haros-${buildName}-${label}`;

  app.innerHTML = `
    <div class="fullview-container">
      <div class="fullview-header">
        <span class="fullview-label">${label}</span>
        <a class="fullview-back" href="#/build/${machine}/${buildName}">← Back to overview</a>
      </div>
      <div class="fullview-terminal" id="fullview-term"></div>
    </div>
  `;

  const termEl = document.getElementById('fullview-term');
  createTerminal(termEl, sessionName, machine, {
    fontSize: 18,
    disableStdin: false,
  });

  // Escape key returns to overview
  document.addEventListener('keydown', function escHandler(e) {
    if (e.key === 'Escape') {
      document.removeEventListener('keydown', escHandler);
      location.hash = `#/build/${machine}/${buildName}`;
    }
  });
}

// ── Terminal Factory ───────────────────────────────────

function createTerminal(container, sessionName, machine, opts = {}) {
  const fitAddon = new FitAddon.FitAddon();

  const term = new Terminal({
    theme: TERM_THEME,
    fontFamily: FONT_FAMILY,
    fontSize: opts.fontSize || 14,
    cursorBlink: true,
    cursorStyle: 'bar',
    disableStdin: opts.disableStdin || false,
    convertEol: true,
    scrollback: 5000,
    allowProposedApi: true,
  });

  term.loadAddon(fitAddon);
  term.open(container);

  // Fit after a short delay to let the DOM settle
  setTimeout(() => fitAddon.fit(), 50);

  // Determine WebSocket path
  const isLocal = isLocalMachine(machine);
  const wsPath = isLocal
    ? `/ws/terminal/${sessionName}`
    : `/ws/proxy/${machine}/${sessionName}`;

  const ws = new WebSocket(wsUrl(wsPath));

  ws.onopen = () => {
    // Send initial size
    ws.send(JSON.stringify({
      type: 'resize',
      cols: term.cols,
      rows: term.rows,
    }));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'output') {
        term.write(msg.data);
      } else if (msg.type === 'error') {
        term.write(`\r\n\x1b[31m[FOV Error] ${msg.data}\x1b[0m\r\n`);
      }
    } catch (e) {
      // Raw text fallback
      term.write(event.data);
    }
  };

  ws.onclose = () => {
    term.write('\r\n\x1b[2m[Connection closed]\x1b[0m\r\n');
  };

  ws.onerror = () => {
    term.write('\r\n\x1b[31m[Connection error]\x1b[0m\r\n');
  };

  // Send keystrokes
  term.onData((data) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }));
    }
  });

  // Handle resize
  term.onResize(({ cols, rows }) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  });

  // Window resize -> refit
  const resizeHandler = () => fitAddon.fit();
  window.addEventListener('resize', resizeHandler);

  activeTerminals.push({ term, ws, fitAddon, resizeHandler });

  return { term, ws, fitAddon };
}

// ── Machine Detection ──────────────────────────────────

let _localHostname = null;

async function detectHostname() {
  try {
    const res = await fetch('/health');
    const data = await res.json();
    _localHostname = data.hostname;
  } catch (e) {
    _localHostname = 'localhost';
  }
}

function isLocalMachine(machine) {
  if (!_localHostname) return machine === 'localhost';
  return machine === _localHostname;
}

// ── Init ───────────────────────────────────────────────

window.addEventListener('hashchange', route);

(async () => {
  await detectHostname();
  route();
})();
