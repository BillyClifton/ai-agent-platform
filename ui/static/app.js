/**
 * AI Agent Platform – frontend application
 * Requires:  TailwindCSS CDN (loaded in index.html), Lucide icons CDN
 */

const API = ''; // same-origin; set to e.g. 'http://localhost:8000' for standalone dev

/* ─── Utilities ─────────────────────────────────────────────────────────── */

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

function statusBadge(status) {
  const map = {
    pending:   'bg-gray-700 text-gray-300',
    running:   'bg-yellow-900/60 text-yellow-300',
    completed: 'bg-green-900/60 text-green-300',
    failed:    'bg-red-900/60 text-red-300',
    cancelled: 'bg-gray-700 text-gray-400',
    active:    'bg-green-900/60 text-green-300',
    inactive:  'bg-gray-700 text-gray-400',
    error:     'bg-red-900/60 text-red-300',
  };
  const cls = map[status] || 'bg-gray-700 text-gray-300';
  const dot = status === 'running'
    ? '<span class="w-1.5 h-1.5 rounded-full bg-yellow-400 pulse-dot inline-block"></span>'
    : '';
  return `<span class="badge ${cls}">${dot}${status}</span>`;
}

function relativeTime(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

function shortId(id) {
  return id ? id.slice(0, 8) + '…' : '—';
}

function showToast(msg, type = 'info') {
  const icons = { info: '💡', success: '✅', error: '❌', warning: '⚠️' };
  document.getElementById('toast-icon').textContent = icons[type] || '💡';
  document.getElementById('toast-msg').textContent = msg;
  const t = document.getElementById('toast');
  t.classList.remove('hidden');
  clearTimeout(t._hide);
  t._hide = setTimeout(() => t.classList.add('hidden'), 3500);
}

/* ─── Navigation ─────────────────────────────────────────────────────────── */

const VIEWS = ['dashboard', 'agents', 'tasks', 'run', 'tools'];
const TITLES = {
  dashboard: 'Dashboard',
  agents:    'Agents',
  tasks:     'Tasks',
  run:       'Run Agent',
  tools:     'MCP Tools',
};
let currentView = 'dashboard';

function navigate(view) {
  if (!VIEWS.includes(view)) return;
  currentView = view;

  VIEWS.forEach(v => {
    document.getElementById(`view-${v}`).classList.toggle('hidden', v !== view);
  });

  document.querySelectorAll('.sidebar-link').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });

  document.getElementById('page-title').textContent = TITLES[view] || view;

  loadView(view);
}

document.querySelectorAll('[data-view]').forEach(el => {
  el.addEventListener('click', e => { e.preventDefault(); navigate(el.dataset.view); });
});

/* ─── Connection probe ───────────────────────────────────────────────────── */

async function checkConnection() {
  const dot = document.getElementById('conn-dot');
  const lbl = document.getElementById('conn-label');
  try {
    await api('/api/v1/tasks/stats');
    dot.className = 'w-2 h-2 rounded-full bg-green-400';
    lbl.textContent = 'Connected';
    lbl.className = 'text-green-400 text-xs';
  } catch {
    dot.className = 'w-2 h-2 rounded-full bg-red-500';
    lbl.textContent = 'Offline';
    lbl.className = 'text-red-400 text-xs';
  }
}

/* ─── Dashboard ──────────────────────────────────────────────────────────── */

async function loadDashboard() {
  try {
    const stats = await api('/api/v1/tasks/stats');
    document.getElementById('stat-agents').textContent = stats.total_agents;
    document.getElementById('stat-agents-active').textContent =
      `${stats.active_agents} active`;
    document.getElementById('stat-total').textContent = stats.total_tasks;
    document.getElementById('stat-running').textContent = stats.running_tasks;
    document.getElementById('stat-completed').textContent = stats.completed_tasks;
    document.getElementById('stat-failed').textContent = stats.failed_tasks;
    const done = stats.completed_tasks + stats.failed_tasks;
    const rate = done > 0 ? Math.round((stats.completed_tasks / done) * 100) : '—';
    document.getElementById('stat-rate').textContent = typeof rate === 'number' ? `${rate}%` : rate;
  } catch (e) {
    showToast('Failed to load stats: ' + e.message, 'error');
  }

  try {
    const tasks = await api('/api/v1/tasks?limit=10');
    renderTasksTable(document.getElementById('recent-tasks-table'), tasks, true);
  } catch (e) {
    document.getElementById('recent-tasks-table').innerHTML =
      '<p class="text-sm text-gray-500 py-4 text-center">Could not load tasks.</p>';
  }
}

/* ─── Agents view ────────────────────────────────────────────────────────── */

async function loadAgents() {
  const grid = document.getElementById('agents-grid');
  grid.innerHTML = '<p class="text-sm text-gray-500 col-span-3">Loading…</p>';
  try {
    const agents = await api('/api/v1/agents');
    if (!agents.length) {
      grid.innerHTML = '<p class="text-sm text-gray-500 col-span-3">No agents registered yet.</p>';
      return;
    }
    grid.innerHTML = agents.map(a => `
      <div class="card flex flex-col gap-3">
        <div class="flex items-start justify-between">
          <div class="w-9 h-9 rounded-lg bg-brand/20 flex items-center justify-center shrink-0">
            <i data-lucide="bot" class="w-4 h-4 text-brand-light"></i>
          </div>
          ${statusBadge(a.status)}
        </div>
        <div>
          <h3 class="font-semibold text-white">${escHtml(a.name)}</h3>
          <p class="text-xs text-gray-400 mt-0.5 line-clamp-2">${escHtml(a.description || '—')}</p>
        </div>
        <div class="text-xs text-gray-500 mt-auto space-y-0.5">
          <p>Model: <span class="text-gray-300">${escHtml(a.config?.model || '—')}</span></p>
          <p>Tools: <span class="text-gray-300">${(a.config?.tools || []).join(', ') || '—'}</span></p>
          <p>Created: <span class="text-gray-300">${relativeTime(a.created_at)}</span></p>
        </div>
        <button class="btn-primary text-xs mt-1"
          onclick="runFromAgent('${escHtml(a.name)}')">
          ▶ Run Task
        </button>
      </div>
    `).join('');
    lucide.createIcons();
  } catch (e) {
    grid.innerHTML = `<p class="text-sm text-red-400 col-span-3">${e.message}</p>`;
  }
}

function runFromAgent(name) {
  navigate('run');
  setTimeout(() => {
    const sel = document.getElementById('run-agent-select');
    for (const opt of sel.options) {
      if (opt.value === name) { sel.value = name; break; }
    }
  }, 100);
}

// Register agent form
document.getElementById('add-agent-btn').addEventListener('click', () => {
  document.getElementById('register-form').classList.toggle('hidden');
});
document.getElementById('cancel-agent-btn').addEventListener('click', () => {
  document.getElementById('register-form').classList.add('hidden');
});
document.getElementById('submit-agent-btn').addEventListener('click', async () => {
  const name = document.getElementById('f-name').value.trim();
  const desc = document.getElementById('f-desc').value.trim();
  const configStr = document.getElementById('f-config').value.trim() || '{}';
  const errEl = document.getElementById('agent-form-error');
  errEl.classList.add('hidden');
  if (!name) { errEl.textContent = 'Name is required.'; errEl.classList.remove('hidden'); return; }
  let config;
  try { config = JSON.parse(configStr); } catch {
    errEl.textContent = 'Config must be valid JSON.'; errEl.classList.remove('hidden'); return;
  }
  try {
    await api('/api/v1/agents', {
      method: 'POST',
      body: JSON.stringify({ name, description: desc, config }),
    });
    showToast(`Agent '${name}' registered.`, 'success');
    document.getElementById('register-form').classList.add('hidden');
    loadAgents();
  } catch (e) {
    errEl.textContent = e.message; errEl.classList.remove('hidden');
  }
});

/* ─── Tasks view ─────────────────────────────────────────────────────────── */

let taskFilter = '';

function renderTasksTable(container, tasks, compact = false) {
  if (!tasks.length) {
    container.innerHTML = '<p class="text-sm text-gray-500 py-6 text-center">No tasks found.</p>';
    return;
  }
  const cols = compact
    ? ['ID', 'Agent', 'Status', 'Input', 'Created']
    : ['ID', 'Agent', 'Status', 'Input', 'Created', 'Actions'];

  container.innerHTML = `
    <table class="w-full text-sm">
      <thead>
        <tr class="text-left text-xs text-gray-500 border-b border-gray-800">
          ${cols.map(c => `<th class="pb-2 pr-4 font-medium">${c}</th>`).join('')}
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-800">
        ${tasks.map(t => `
          <tr class="hover:bg-white/[0.02] cursor-pointer" onclick="openTaskDetail('${t.id}')">
            <td class="py-2.5 pr-4 font-mono text-gray-400">${shortId(t.id)}</td>
            <td class="py-2.5 pr-4 text-gray-300">${escHtml(t.agent_id ? shortId(t.agent_id) : '—')}</td>
            <td class="py-2.5 pr-4">${statusBadge(t.status)}</td>
            <td class="py-2.5 pr-4 text-gray-400 max-w-[200px] truncate">${escHtml(t.input_text)}</td>
            <td class="py-2.5 pr-4 text-gray-500">${relativeTime(t.created_at)}</td>
            ${!compact ? `<td class="py-2.5"><button class="btn-ghost text-xs" onclick="event.stopPropagation();openTaskDetail('${t.id}')">Details</button></td>` : ''}
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

async function loadTasks() {
  const container = document.getElementById('tasks-table');
  container.innerHTML = '<p class="text-sm text-gray-500 py-6 text-center">Loading…</p>';
  try {
    const url = taskFilter ? `/api/v1/tasks?limit=100&status_filter=${taskFilter}` : '/api/v1/tasks?limit=100';
    const tasks = await api(url);
    renderTasksTable(container, tasks);
  } catch (e) {
    container.innerHTML = `<p class="text-sm text-red-400 p-4">${e.message}</p>`;
  }
}

// Filter buttons
document.querySelectorAll('.task-filter').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.task-filter').forEach(b => b.classList.remove('active-filter', 'text-brand-light'));
    btn.classList.add('active-filter', 'text-brand-light');
    taskFilter = btn.dataset.status;
    loadTasks();
  });
});

async function openTaskDetail(taskId) {
  const panel = document.getElementById('task-detail');
  const body = document.getElementById('task-detail-body');
  panel.classList.remove('hidden');
  document.getElementById('task-detail-title').textContent = `Task ${shortId(taskId)}`;
  body.innerHTML = '<p class="text-sm text-gray-500">Loading…</p>';
  panel.scrollIntoView({ behavior: 'smooth' });

  try {
    const task = await api(`/api/v1/tasks/${taskId}`);
    body.innerHTML = `
      <div class="grid sm:grid-cols-2 gap-3 text-sm">
        <div><span class="text-gray-500">ID:</span> <span class="font-mono text-gray-300">${task.id}</span></div>
        <div><span class="text-gray-500">Status:</span> ${statusBadge(task.status)}</div>
        <div><span class="text-gray-500">Created:</span> <span class="text-gray-300">${new Date(task.created_at).toLocaleString()}</span></div>
        <div><span class="text-gray-500">Completed:</span> <span class="text-gray-300">${task.completed_at ? new Date(task.completed_at).toLocaleString() : '—'}</span></div>
        ${task.workflow_id ? `<div class="col-span-2"><span class="text-gray-500">Workflow:</span> <span class="font-mono text-xs text-gray-400">${task.workflow_id}</span></div>` : ''}
      </div>
      <div>
        <p class="text-xs text-gray-500 mb-1">Input</p>
        <pre class="bg-gray-800 rounded-lg p-3 text-sm text-gray-300">${escHtml(task.input_text)}</pre>
      </div>
      ${task.output_text ? `
        <div>
          <p class="text-xs text-gray-500 mb-1">Output</p>
          <pre class="bg-gray-800 rounded-lg p-3 text-sm text-gray-300">${escHtml(task.output_text)}</pre>
        </div>
      ` : ''}
      ${task.error_message ? `
        <div>
          <p class="text-xs text-red-400 mb-1">Error</p>
          <pre class="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-300">${escHtml(task.error_message)}</pre>
        </div>
      ` : ''}
      ${task.tool_calls && task.tool_calls.length ? `
        <div>
          <p class="text-xs text-gray-500 mb-2">Tool Calls (${task.tool_calls.length})</p>
          <div class="space-y-2">
            ${task.tool_calls.map(tc => `
              <div class="bg-gray-800 rounded-lg p-3 text-xs space-y-1">
                <div class="flex items-center justify-between">
                  <span class="font-medium text-brand-light">${escHtml(tc.tool_name)}</span>
                  ${tc.duration_ms ? `<span class="text-gray-500">${tc.duration_ms}ms</span>` : ''}
                </div>
                <div class="text-gray-400">Args: <code>${escHtml(JSON.stringify(tc.arguments))}</code></div>
                ${tc.result ? `<div class="text-gray-300">Result: <code>${escHtml(JSON.stringify(tc.result))}</code></div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;
  } catch (e) {
    body.innerHTML = `<p class="text-sm text-red-400">${e.message}</p>`;
  }
}

document.getElementById('close-detail-btn').addEventListener('click', () => {
  document.getElementById('task-detail').classList.add('hidden');
});

/* ─── Run Agent view ──────────────────────────────────────────────────────── */

async function populateAgentSelect() {
  const sel = document.getElementById('run-agent-select');
  try {
    const agents = await api('/api/v1/agents');
    const active = agents.filter(a => a.status === 'active');
    if (!active.length) {
      sel.innerHTML = '<option value="">No active agents</option>';
      return;
    }
    sel.innerHTML = '<option value="">— select an agent —</option>' +
      active.map(a => `<option value="${escAttr(a.name)}">${escHtml(a.name)}</option>`).join('');
  } catch {
    sel.innerHTML = '<option value="">Failed to load agents</option>';
  }
}

document.getElementById('run-btn').addEventListener('click', async () => {
  const agentName = document.getElementById('run-agent-select').value;
  const inputText = document.getElementById('run-input').value.trim();
  const errEl = document.getElementById('run-error');
  errEl.classList.add('hidden');

  if (!agentName) { errEl.textContent = 'Please select an agent.'; errEl.classList.remove('hidden'); return; }
  if (!inputText) { errEl.textContent = 'Please enter a prompt.'; errEl.classList.remove('hidden'); return; }

  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.innerHTML = '<svg class="w-4 h-4 spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> Submitting…';

  const result = document.getElementById('run-result');
  const resultBody = document.getElementById('run-result-body');
  result.classList.remove('hidden');
  resultBody.innerHTML = '<p class="text-gray-500 text-xs">Submitting task…</p>';

  try {
    const task = await api('/api/v1/tasks', {
      method: 'POST',
      body: JSON.stringify({ agent_name: agentName, input_text: inputText }),
    });
    showToast('Task submitted!', 'success');
    pollTask(task.id, resultBody);
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
    resultBody.innerHTML = '';
    result.classList.add('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg> Submit Task';
  }
});

async function pollTask(taskId, container) {
  const badge = document.getElementById('run-status-badge');
  let attempts = 0;
  const maxAttempts = 150; // 5 min at 2s intervals

  const poll = async () => {
    if (attempts++ > maxAttempts) {
      container.innerHTML = '<p class="text-yellow-400 text-xs">Polling timeout. Check the Tasks view.</p>';
      return;
    }
    try {
      const task = await api(`/api/v1/tasks/${taskId}`);
      badge.innerHTML = statusBadge(task.status);

      if (task.status === 'running' || task.status === 'pending') {
        container.innerHTML = `
          <div class="flex items-center gap-2 text-sm text-yellow-300">
            <svg class="w-4 h-4 spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
            Agent is working… (${attempts * 2}s elapsed)
          </div>`;
        setTimeout(poll, 2000);
        return;
      }

      if (task.status === 'completed') {
        container.innerHTML = `
          <pre class="bg-gray-800 rounded-lg p-3 text-sm text-gray-200 max-h-96 overflow-y-auto">${escHtml(task.output_text || '(no output)')}</pre>
          ${task.tool_calls && task.tool_calls.length ? `
            <details class="mt-2">
              <summary class="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                Tool calls (${task.tool_calls.length})
              </summary>
              <div class="mt-2 space-y-1">
                ${task.tool_calls.map(tc => `
                  <div class="bg-gray-800 rounded px-3 py-1.5 text-xs text-gray-400">
                    <span class="text-brand-light font-medium">${escHtml(tc.tool_name)}</span>
                    ${tc.duration_ms ? `<span class="text-gray-600 ml-2">${tc.duration_ms}ms</span>` : ''}
                  </div>`).join('')}
              </div>
            </details>` : ''}
          <p class="text-xs text-gray-500 mt-2">Task ID: <code class="font-mono">${taskId}</code>
            <a class="text-brand-light ml-2 hover:underline" href="#" onclick="event.preventDefault();navigate('tasks');setTimeout(()=>openTaskDetail('${taskId}'),200)">
              View full details →
            </a>
          </p>`;
      } else {
        container.innerHTML = `<p class="text-red-400 text-sm">${escHtml(task.error_message || 'Task failed.')}</p>`;
      }
    } catch (e) {
      container.innerHTML = `<p class="text-red-400 text-xs">${e.message}</p>`;
    }
  };
  await poll();
}

/* ─── Tools view ──────────────────────────────────────────────────────────── */

const MCP_TOOLS = [
  { name: 'list_agents',      desc: 'Return all registered AI agents and their current status.',         icon: 'bot' },
  { name: 'run_agent',        desc: 'Submit a task to a named agent and receive a task ID.',              icon: 'play-circle' },
  { name: 'get_task_status',  desc: 'Poll the status of a running or pending task.',                     icon: 'loader' },
  { name: 'get_task_result',  desc: 'Retrieve the full output and tool calls of a completed task.',       icon: 'file-check' },
  { name: 'list_tools',       desc: 'Enumerate all MCP tools available in this gateway.',                 icon: 'wrench' },
];

function loadTools() {
  const grid = document.getElementById('tools-grid');
  grid.innerHTML = MCP_TOOLS.map(t => `
    <div class="card flex flex-col gap-3">
      <div class="w-9 h-9 rounded-lg bg-brand/20 flex items-center justify-center">
        <i data-lucide="${t.icon}" class="w-4 h-4 text-brand-light"></i>
      </div>
      <div>
        <h3 class="font-semibold text-white font-mono">${t.name}()</h3>
        <p class="text-xs text-gray-400 mt-1">${t.desc}</p>
      </div>
    </div>
  `).join('');
  lucide.createIcons();

  document.getElementById('mcp-sse-url').textContent = window.location.origin + '/mcp/mcp';
}

/* ─── View loader ─────────────────────────────────────────────────────────── */

function loadView(view) {
  switch (view) {
    case 'dashboard': loadDashboard(); break;
    case 'agents':    loadAgents(); break;
    case 'tasks':     loadTasks(); break;
    case 'run':       populateAgentSelect(); break;
    case 'tools':     loadTools(); break;
  }
  document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

/* ─── Refresh button ──────────────────────────────────────────────────────── */

document.getElementById('refresh-btn').addEventListener('click', () => {
  loadView(currentView);
  checkConnection();
});

/* ─── HTML helpers ────────────────────────────────────────────────────────── */

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escAttr(str) {
  if (str == null) return '';
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* ─── Init ────────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  checkConnection();
  loadView('dashboard');

  // Auto-refresh every 30 s
  setInterval(() => {
    if (currentView === 'dashboard' || currentView === 'tasks') {
      loadView(currentView);
    }
    checkConnection();
  }, 30000);
});
