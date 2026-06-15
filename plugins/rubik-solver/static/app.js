const colors = {
  Y: '#ffd500',
  W: '#ffffff',
  G: '#009b48',
  B: '#0046ad',
  O: '#ff5800',
  R: '#b71234',
};

const faceOrder = ['U', 'L', 'F', 'R', 'B', 'D'];
const phaseDagIds = [
  'rubik_init',
  'rubik_solve_cross',
  'rubik_solve_white_corners',
  'rubik_solve_middle_layer',
  'rubik_solve_yellow_cross',
  'rubik_solve_yellow_face',
  'rubik_solve_yellow_corners',
  'rubik_solve_yellow_edges',
  'rubik_complete',
];

let selectedSnapshot = null;
let latestHistoryRows = [];
let playbackTimer = null;

function badgeClass(state) {
  if (!state) return 'unknown';
  const normalized = String(state).toLowerCase();
  if (['success', 'complete'].includes(normalized)) return 'success';
  if (['running'].includes(normalized)) return 'running';
  if (['failed', 'upstream_failed'].includes(normalized)) return 'failed';
  if (['queued', 'scheduled', 'pending'].includes(normalized)) return 'queued';
  return 'unknown';
}

function renderCube(cube) {
  const target = document.getElementById('cube');
  target.innerHTML = '';

  if (!cube || !cube.U) {
    target.textContent = 'No cube state found yet. Start a solve to populate state.';
    return;
  }

  for (const face of faceOrder) {
    const wrap = document.createElement('div');
    wrap.className = `face-wrap face-${face}`;

    const label = document.createElement('div');
    label.className = 'face-label';
    label.textContent = face;

    const grid = document.createElement('div');
    grid.className = 'face';

    for (const sticker of cube[face]) {
      const cell = document.createElement('div');
      cell.className = 'sticker';
      cell.style.background = colors[sticker] || '#999';
      grid.appendChild(cell);
    }

    wrap.appendChild(label);
    wrap.appendChild(grid);
    target.appendChild(wrap);
  }
}

function renderSummary(state, history) {
  const session = history.sessions?.[history.active_session_id];
  const status = state.status || session?.status || 'idle';
  const phase = state.phase || 'not started';
  const moves = state.total_moves || 0;
  const iteration = state.iteration || 0;
  document.getElementById('summary').textContent = `Status: ${status} | Phase: ${phase} | Iteration: ${iteration} | Total moves: ${moves}`;
}

function renderHistory(history) {
  const target = document.getElementById('history');
  target.innerHTML = '';
  const session = history.sessions?.[history.active_session_id];
  const rows = session?.history || [];
  latestHistoryRows = rows;

  if (!rows.length) {
    target.textContent = 'No history snapshots yet.';
    return;
  }

  for (const row of [...rows].reverse()) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'history-row';
    const moveLabel = row.move_number ? `Move ${row.move_number}` : 'Phase checkpoint';
    item.innerHTML = `
      <strong>${moveLabel}: ${row.phase || 'unknown phase'} / ${row.task_id}</strong>
      <span>${new Date(row.timestamp).toLocaleString()}</span>
      <span>Move: ${(row.moves || []).join(' ') || 'none'} | Total: ${row.total_moves || 0}</span>
    `;
    item.addEventListener('click', () => {
      stopPlayback();
      selectedSnapshot = row;
      renderCube(row.cube);
    });
    target.appendChild(item);
  }
}

function renderDagRuns(payload) {
  const target = document.getElementById('dag-runs');
  target.innerHTML = '';
  const byDag = Object.fromEntries((payload.dags || []).map((row) => [row.dag_id, row.latest_run]));

  for (const dagId of phaseDagIds) {
    const run = byDag[dagId];
    const state = run?.state || 'pending';
    const row = document.createElement('div');
    row.className = 'dag-row';
    row.innerHTML = `
      <strong>${dagId}</strong>
      <span class="badge ${badgeClass(state)}">${state}</span>
      <span>${run?.dag_run_id || 'No run yet'}</span>
    `;
    target.appendChild(row);
  }
}

async function fetchJson(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function refresh() {
  try {
    const [state, history] = await Promise.all([
      fetchJson('api/state'),
      fetchJson('api/history'),
    ]);
    renderSummary(state, history);
    renderHistory(history);
    if (!selectedSnapshot) {
      renderCube(state.cube);
    }
  } catch (error) {
    document.getElementById('summary').textContent = `Unable to load state: ${error.message}`;
  }

  try {
    renderDagRuns(await fetchJson('api/dag-runs'));
  } catch (error) {
    document.getElementById('dag-runs').textContent = `DAG run tracking unavailable: ${error.message}`;
  }
}

function stopPlayback() {
  if (playbackTimer) {
    clearInterval(playbackTimer);
    playbackTimer = null;
  }
}

function playHistory() {
  stopPlayback();
  if (!latestHistoryRows.length) {
    return;
  }

  selectedSnapshot = latestHistoryRows[0];
  let index = 0;
  renderCube(latestHistoryRows[index].cube);
  playbackTimer = setInterval(() => {
    index += 1;
    if (index >= latestHistoryRows.length) {
      stopPlayback();
      return;
    }
    selectedSnapshot = latestHistoryRows[index];
    renderCube(latestHistoryRows[index].cube);
  }, 350);
}

document.getElementById('play-history').addEventListener('click', playHistory);
document.getElementById('live-view').addEventListener('click', () => {
  stopPlayback();
  selectedSnapshot = null;
  refresh();
});

document.getElementById('start-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  stopPlayback();
  selectedSnapshot = null;
  const button = event.target.querySelector('button');
  button.disabled = true;
  try {
    await fetchJson('api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scramble: document.getElementById('scramble').value.trim() }),
    });
    await refresh();
  } catch (error) {
    alert(`Unable to start solve: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

refresh();
setInterval(refresh, 3000);
