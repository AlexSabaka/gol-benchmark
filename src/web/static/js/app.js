/* GoL Benchmark — minimal vanilla JS helpers alongside HTMX */

/** Show a flash message */
function flash(message, type = 'info') {
  const container = document.getElementById('flash');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `flash-msg ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

/** Populate a <select> or checkbox list from an API endpoint */
async function loadOptions(url, targetId, { valueKey = 'name', labelKey = 'display_name', type = 'select' } = {}) {
  try {
    const resp = await fetch(url);
    const data = await resp.json();
    const items = Array.isArray(data) ? data : data.models || data.plugins || [];
    const target = document.getElementById(targetId);
    if (!target) return;

    if (type === 'select') {
      target.innerHTML = items.map(
        i => `<option value="${i[valueKey]}">${i[labelKey] || i[valueKey]}</option>`
      ).join('');
    } else if (type === 'checkboxes') {
      target.innerHTML = items.map(
        i => `<label><input type="checkbox" name="${targetId}" value="${i[valueKey]}"> ${i[labelKey] || i[valueKey]}</label>`
      ).join('');
    }
  } catch (e) {
    console.error(`loadOptions(${url})`, e);
    flash(`Failed to load options from ${url}`, 'error');
  }
}

/** Collect checked values from a checkbox group */
function getChecked(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(cb => cb.value);
}

/** Format seconds to human-readable */
function fmtDuration(s) {
  if (s == null) return '—';
  if (s < 60) return `${Math.round(s)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s % 60)}s`;
}

/** Format accuracy as percentage */
function fmtPct(v) {
  if (v == null) return '—';
  return `${(v * 100).toFixed(1)}%`;
}

/**
 * Start polling a job's status. Calls onUpdate(data) on each poll,
 * stops when state is completed/failed/cancelled.
 */
function pollJob(jobId, onUpdate, intervalMs = 3000) {
  const poll = async () => {
    try {
      const resp = await fetch(`/api/jobs/${jobId}/status`);
      const data = await resp.json();
      onUpdate(data);
      if (['completed', 'failed', 'cancelled'].includes(data.state)) return;
      setTimeout(poll, intervalMs);
    } catch (e) {
      console.error('pollJob error', e);
      setTimeout(poll, intervalMs * 2);
    }
  };
  poll();
}

/**
 * Build the GenerateRequest JSON from the configure form.
 * Reads task checkboxes, per-task params, prompt config, global settings.
 */
function buildGeneratePayload() {
  const tasks = [];
  document.querySelectorAll('.task-panel[data-task-type]').forEach(panel => {
    const taskType = panel.dataset.taskType;
    const cb = document.querySelector(`input[name="tasks"][value="${taskType}"]`);
    if (!cb || !cb.checked) return;

    // Collect generation params from inputs inside this panel
    const generation = {};
    const seen = new Set();
    panel.querySelectorAll('[data-param]').forEach(input => {
      const key = input.dataset.param;
      const ptype = input.dataset.paramType || 'number';

      if (ptype === 'multi-select') {
        if (seen.has(key)) return; // collect once per key
        seen.add(key);
        const vals = Array.from(panel.querySelectorAll(`[data-param="${key}"]:checked`)).map(c => {
          const v = c.value;
          return isNaN(v) ? v : Number(v);
        });
        generation[key] = vals;
      } else if (ptype === 'number') {
        generation[key] = Number(input.value);
      } else if (ptype === 'boolean') {
        generation[key] = input.checked;
      } else if (ptype === 'range') {
        if (!generation[key]) generation[key] = [null, null];
        const pos = input.dataset.rangePos;
        generation[key][pos === 'min' ? 0 : 1] = Number(input.value);
      } else if (ptype === 'weight_map') {
        if (!generation[key]) generation[key] = {};
        generation[key][input.dataset.weightKey] = Number(input.value);
      } else {
        generation[key] = input.value;
      }
    });

    // Prompt configs
    const userStyles = getChecked('user_style');
    const sysStyles = getChecked('system_style');
    const lang = document.getElementById('language')?.value || 'en';
    const promptConfigs = [];
    for (const us of (userStyles.length ? userStyles : ['minimal'])) {
      for (const ss of (sysStyles.length ? sysStyles : ['analytical'])) {
        promptConfigs.push({ user_style: us, system_style: ss, language: lang });
      }
    }

    tasks.push({ type: taskType, generation, prompt_configs: promptConfigs });
  });

  return {
    name: document.getElementById('cfg-name')?.value || 'web_benchmark',
    description: document.getElementById('cfg-desc')?.value || '',
    tasks,
    temperature: Number(document.getElementById('temperature')?.value || 0.1),
    max_tokens: Number(document.getElementById('max_tokens')?.value || 2048),
    no_thinking: document.getElementById('no_think')?.checked ?? true,
    seed: Number(document.getElementById('seed')?.value || 42),
    cell_markers: ['1', '0'],
  };
}
