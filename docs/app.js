'use strict';

const CAMERAS = ['static', 'slow_push', 'pull', 'pan_left', 'pan_right', 'tilt_up', 'tilt_down', 'tracking'];
const MOTIONS = ['walking', 'turning', 'hair_movement', 'blinking', 'facial_expression', 'environment_movement'];
const CHAR_FIELDS = [
  ['name', 'Name'], ['age', 'Age'], ['hairstyle', 'Hairstyle'], ['hair_color', 'Hair color'],
  ['eye_color', 'Eye color'], ['clothing', 'Clothing'], ['body_proportions', 'Body proportions'],
  ['accessories', 'Accessories'], ['personality', 'Personality'], ['visual_style', 'Visual style'],
];
const STYLE_FIELDS = [['environment', 'Environment'], ['animation_style', 'Animation style'], ['mood', 'Mood'], ['lighting', 'Lighting'], ['shot_type', 'Shot type']];

const $ = (s, r) => (r || document).querySelector(s);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function el(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid !== null && kid !== undefined && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}

const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
};

const state = { backend: store.get('oas.backend', 'http://127.0.0.1:8000'), caps: null, plan: null, busy: false };
const base = () => state.backend.replace(/[/]+$/, '');
const fileUrl = (rel) => base() + '/files/' + state.plan.project_id + '/' + rel + '?t=' + Date.now();

async function api(path, opts) {
  const o = opts || {};
  const res = await fetch(base() + path, { ...o, headers: { 'Content-Type': 'application/json', ...(o.headers || {}) } });
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch (e) { /* keep status text */ }
    throw new Error(msg);
  }
  return res.json();
}

function setStatus(msg, kind) {
  const s = $('#status');
  s.textContent = msg;
  s.className = 'status ' + (kind || '');
}

function setBusy(b) {
  document.querySelectorAll('button.act').forEach((x) => { x.disabled = b; });
}

async function guarded(label, fn) {
  if (state.busy) return;
  state.busy = true;
  setBusy(true);
  setStatus(label);
  try { await fn(); } catch (e) { setStatus(e.message, 'err'); } finally { state.busy = false; setBusy(false); }
}

/* ---------- connection / layers ---------- */

function layerCard(title, sub, items) {
  return el('div', { class: 'layer' },
    el('h3', {}, title),
    el('p', { class: 'muted' }, sub),
    el('ul', {}, items.map((i) => el('li', { class: i[1] ? 'ok' : 'bad' }, (i[1] ? '● ' : '○ ') + i[0] + (i[2] ? ' - ' + i[2] : '')))));
}

function renderLayers(h) {
  let host = '';
  try { host = new URL(state.backend).hostname; } catch (e) { host = ''; }
  const local = host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
  const l1 = layerCard('1. Frontend', 'Static files only (GitHub Pages or /ui). Cannot run models.', [['This page', true, location.origin === 'null' ? 'file' : location.origin]]);
  const l2 = layerCard('2. Local AI inference', 'Runs on your machine or GPU server.', h ? [
    ['Backend', true, state.backend], ['FFmpeg', h.ffmpeg], ['ComfyUI', h.comfyui, h.comfyui_url], ['Ollama (planner)', h.ollama, h.ollama_model],
  ] : [['Backend', false, 'not reachable']]);
  const l3 = layerCard('3. Optional external inference', 'Only if you point the Backend URL at a server you run elsewhere.', [
    [local ? 'Not in use (backend is local)' : 'Remote backend: ' + host, !local],
    ['Paid generation APIs', false, 'never used'],
  ]);
  $('#layers').replaceChildren(l1, l2, l3);
}

function renderFeatures(c) {
  const rows = Object.entries(c.features).map(([k, v]) => el('tr', {},
    el('td', {}, k.replace(/_/g, ' ')), el('td', {}, el('span', { class: 'badge b-' + v.status }, v.status.replace(/_/g, ' '))), el('td', {}, v.note)));
  $('#features').replaceChildren(el('table', {}, el('tr', {}, el('th', {}, 'Feature'), el('th', {}, 'Status'), el('th', {}, 'Notes')), rows));
}

function fillProviders(c) {
  const fill = (id, list) => {
    const s = $('#' + id);
    s.replaceChildren(...list.map((p) => el('option', { value: p.id, textContent: p.name + (p.configured ? '' : ' (needs setup)') })));
    const ok = list.find((p) => p.configured);
    if (ok) s.value = ok.id;
  };
  fill('image-provider', c.image_providers);
  fill('video-provider', c.video_providers);
  const show = () => {
    const lines = [];
    for (const pair of [['image-provider', c.image_providers], ['video-provider', c.video_providers]]) {
      const p = pair[1].find((x) => x.id === $('#' + pair[0]).value);
      if (p) lines.push(p.name + ': ' + (p.configured ? 'ready.' : p.detail) + ' ' + (p.license_note || ''));
    }
    $('#provider-detail').textContent = lines.join('   |   ');
  };
  $('#image-provider').onchange = show;
  $('#video-provider').onchange = show;
  show();
}

async function connect() {
  state.backend = $('#backend').value.trim() || state.backend;
  store.set('oas.backend', state.backend);
  setStatus('Connecting...');
  try {
    const results = await Promise.all([api('/health'), api('/capabilities')]);
    state.caps = results[1];
    renderLayers(results[0]);
    renderFeatures(results[1]);
    fillProviders(results[1]);
    setStatus('Connected to backend.', 'ok');
  } catch (e) {
    state.caps = null;
    renderLayers(null);
    setStatus('Cannot reach the backend at ' + state.backend + ' (' + e.message + '). Start it as described in the README. If this page is on https and your browser blocks http://127.0.0.1, open http://127.0.0.1:8000/ui/ instead.', 'err');
  }
}

/* ---------- input form ---------- */

function textField(id, label, o) {
  const opt = o || {};
  const input = opt.multiline ? el('textarea', { id: id, rows: opt.rows || 3 }) : el('input', { id: id, type: 'text' });
  if (opt.value) input.value = opt.value;
  if (opt.placeholder) input.placeholder = opt.placeholder;
  return el('label', { class: 'field' + (opt.wide ? ' wide' : '') }, el('span', {}, label), input);
}

function selectField(id, label, options, selected) {
  const s = el('select', { id: id }, options.map((o) => el('option', { value: o[0], textContent: o[1] })));
  s.value = selected;
  return el('label', { class: 'field' }, el('span', {}, label), s);
}

function buildForm() {
  const f = $('#input-form');
  f.append(
    textField('f-description', 'Anime video description', { multiline: true, rows: 4, wide: true, placeholder: 'What happens in the video?' }),
    el('h3', {}, 'Character (the same profile is reused in every scene)'),
    el('div', { class: 'grid' },
      textField('c-description', 'Character description', { wide: true }),
      CHAR_FIELDS.map((c) => textField('c-' + c[0], c[1], c[0] === 'visual_style' ? { value: 'anime' } : {}))),
    el('h3', {}, 'Scene settings'),
    el('div', { class: 'grid' },
      STYLE_FIELDS.map((c) => textField('f-' + c[0], c[1], c[0] === 'animation_style' ? { value: 'modern anime, cel shading' } : c[0] === 'shot_type' ? { value: 'medium shot' } : {})),
      selectField('f-camera', 'Camera movement', CAMERAS.map((c) => [c, c.replace(/_/g, ' ')]), 'slow_push'),
      selectField('f-aspect', 'Aspect ratio', [['16:9', '16:9'], ['9:16', '9:16'], ['1:1', '1:1']], '16:9'),
      el('label', { class: 'field' }, el('span', {}, 'Total duration (seconds)'), el('input', { id: 'f-duration', type: 'number', min: 1, max: 60, step: 0.5, value: 5 }))),
    el('h3', {}, 'Dialogue'),
    el('div', { class: 'grid' },
      textField('f-dialogue', 'Dialogue, one line each (optional Name: text)', { multiline: true, wide: true }),
      selectField('f-dlang', 'Language you wrote it in', [['en', 'English'], ['ja', 'Japanese'], ['fa', 'Persian']], 'en')),
    el('fieldset', {}, el('legend', {}, 'Motion'),
      MOTIONS.map((m) => el('label', { class: 'check' }, el('input', { type: 'checkbox', class: 'motion', value: m }), m.replace(/_/g, ' ')))),
    el('button', { type: 'submit', class: 'primary act' }, 'Create scene plan'));
  f.addEventListener('submit', (ev) => { ev.preventDefault(); makePlan(); });
}

function readInput() {
  const g = (id) => $('#' + id).value.trim();
  const character = { description: g('c-description') };
  CHAR_FIELDS.forEach((c) => { character[c[0]] = g('c-' + c[0]); });
  if (!character.name) character.name = 'Character';
  return {
    description: g('f-description'),
    character: character,
    environment: g('f-environment'),
    dialogue: $('#f-dialogue').value,
    dialogue_language: g('f-dlang'),
    duration: parseFloat(g('f-duration')) || 5,
    aspect_ratio: g('f-aspect'),
    camera_movement: g('f-camera'),
    animation_style: g('f-animation_style'),
    mood: g('f-mood'),
    lighting: g('f-lighting'),
    shot_type: g('f-shot_type'),
    motion: Array.from(document.querySelectorAll('.motion:checked')).map((x) => x.value),
  };
}

async function makePlan() {
  const input = readInput();
  if (!input.description) { setStatus('Write a video description first.', 'err'); return; }
  await guarded('Planning scenes...', async () => {
    state.plan = await api('/plan', { method: 'POST', body: JSON.stringify(input) });
    renderPlan();
    setStatus('Plan ready (' + state.plan.planner + ').', 'ok');
  });
}

/* ---------- plan / scenes ---------- */

const savePlan = () => api('/projects/' + state.plan.project_id + '/plan', { method: 'PUT', body: JSON.stringify(state.plan) });

async function reloadPlan() {
  state.plan = await api('/projects/' + state.plan.project_id);
  renderPlan();
}

async function runJob(path, body, label) {
  await savePlan();
  const started = await api(path, { method: 'POST', body: JSON.stringify(body) });
  for (;;) {
    const j = await api('/jobs/' + started.job_id);
    setStatus(label + ': ' + (j.message || j.status));
    if (j.status === 'done') return j.result;
    if (j.status === 'error') throw new Error(j.error);
    await sleep(2000);
  }
}

function bind(obj, key, multiline) {
  const e = el(multiline ? 'textarea' : 'input', multiline ? { rows: 3 } : { type: 'text' });
  e.value = obj[key] || '';
  e.addEventListener('input', () => { obj[key] = e.value; });
  return e;
}

function bindNum(obj, key) {
  const e = el('input', { type: 'number', min: 1, max: 8, step: 0.5 });
  e.value = obj[key];
  e.addEventListener('input', () => { const v = parseFloat(e.value); if (v) obj[key] = v; });
  return e;
}

function bindSelect(obj, key, options) {
  const s = el('select', {}, options.map((o) => el('option', { value: o, textContent: o.replace(/_/g, ' ') })));
  s.value = obj[key];
  s.addEventListener('change', () => { obj[key] = s.value; });
  return s;
}

const field = (label, input, wide) => el('label', { class: 'field' + (wide ? ' wide' : '') }, el('span', {}, label), input);

function dialogueEditor(scene) {
  const box = el('div', { class: 'dialogue' });
  const draw = () => {
    box.replaceChildren(el('h4', {}, 'Dialogue (subtitles use these texts; fill the languages you need)'));
    scene.dialogue.forEach((line, i) => {
      line.text = line.text || {};
      const speaker = el('input', { type: 'text', placeholder: 'Speaker' });
      speaker.value = line.speaker || '';
      speaker.addEventListener('input', () => { line.speaker = speaker.value; });
      const langs = ['en', 'ja', 'fa'].map((l) => {
        const t = el('input', { type: 'text', placeholder: l.toUpperCase() });
        t.value = line.text[l] || '';
        t.dir = l === 'fa' ? 'rtl' : 'auto';
        t.addEventListener('input', () => { line.text[l] = t.value; });
        return t;
      });
      box.append(el('div', { class: 'dline' }, speaker, langs, el('button', { type: 'button', class: 'ghost', onclick: () => { scene.dialogue.splice(i, 1); draw(); } }, 'x')));
    });
    box.append(el('button', { type: 'button', class: 'ghost', onclick: () => { scene.dialogue.push({ speaker: '', text: {} }); draw(); } }, '+ dialogue line'));
  };
  draw();
  return box;
}

function motionBoxes(scene) {
  return el('fieldset', {}, el('legend', {}, 'Motion'), MOTIONS.map((m) => {
    const cb = el('input', { type: 'checkbox' });
    cb.checked = scene.motion.includes(m);
    cb.addEventListener('change', () => { scene.motion = scene.motion.filter((x) => x !== m).concat(cb.checked ? [m] : []); });
    return el('label', { class: 'check' }, cb, m.replace(/_/g, ' '));
  }));
}

async function sceneJob(scene, kind) {
  await guarded(scene.scene_id + ' ' + kind + '...', async () => {
    const pid = state.plan.project_id;
    const body = kind === 'keyframe'
      ? { provider: $('#image-provider').value, use_reference: $('#use-ref').checked }
      : { provider: $('#video-provider').value, fps: parseInt($('#fps').value, 10) || 24 };
    const r = await runJob('/projects/' + pid + '/scenes/' + scene.scene_id + '/' + kind, body, scene.scene_id + ' ' + kind);
    await reloadPlan();
    setStatus(scene.scene_id + ' ' + kind + ' finished. ' + (r.notes || []).join(' '), 'ok');
  });
}

function sceneCard(scene) {
  const media = el('div', { class: 'media' });
  if (scene.keyframe) media.append(el('img', { src: fileUrl(scene.keyframe), alt: 'keyframe ' + scene.scene_id }));
  if (scene.clip) media.append(el('video', { src: fileUrl(scene.clip), controls: true, loop: true }));
  return el('div', { class: 'scene' },
    el('header', {},
      el('strong', {}, 'Scene ' + scene.scene_id),
      el('div', { class: 'actions' },
        el('button', { type: 'button', class: 'act', onclick: () => sceneJob(scene, 'keyframe') }, scene.keyframe ? 'Regenerate keyframe' : 'Generate keyframe'),
        el('button', { type: 'button', class: 'act', disabled: !scene.keyframe, onclick: () => sceneJob(scene, 'video') }, scene.clip ? 'Regenerate clip' : 'Generate clip'))),
    el('div', { class: 'grid' },
      field('Duration (s)', bindNum(scene, 'duration')),
      field('Location', bind(scene, 'location')),
      field('Environment', bind(scene, 'environment')),
      field('Character actions', bind(scene, 'character_actions', true), true),
      field('Facial expression', bind(scene, 'facial_expression')),
      field('Camera angle', bind(scene, 'camera_angle')),
      field('Camera movement', bindSelect(scene, 'camera_movement', CAMERAS)),
      field('Lighting', bind(scene, 'lighting')),
      field('Visual style', bind(scene, 'visual_style')),
      field('Mood', bind(scene, 'mood'))),
    motionBoxes(scene),
    dialogueEditor(scene),
    el('div', { class: 'grid' },
      field('Keyframe prompt', bind(scene, 'image_prompt', true), true),
      field('Video prompt', bind(scene, 'video_prompt', true), true),
      field('Negative prompt', bind(scene, 'negative_prompt', true), true)),
    media);
}

async function uploadRef(file) {
  await guarded('Uploading reference image...', async () => {
    await savePlan();
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(base() + '/projects/' + state.plan.project_id + '/reference', { method: 'POST', body: fd });
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail; } catch (e) { /* keep */ } throw new Error(d); }
    state.plan = await res.json();
    renderPlan();
    setStatus('Reference image saved.', 'ok');
  });
}

async function rebuildPrompts() {
  await guarded('Rebuilding prompts...', async () => {
    await savePlan();
    state.plan = await api('/projects/' + state.plan.project_id + '/rebuild-prompts', { method: 'POST', body: '{}' });
    renderPlan();
    setStatus('Prompts rebuilt from the current scene fields.', 'ok');
  });
}

function renderPlan() {
  const plan = state.plan;
  $('#plan-section').hidden = false;
  $('#assemble-section').hidden = false;
  $('#plan-head').replaceChildren(
    el('p', {}, 'Project ' + plan.project_id + '  |  planner: ' + plan.planner + '  |  ' + plan.scenes.length + ' scene(s)'),
    plan.warnings.map((w) => el('p', { class: 'warn' }, 'Warning: ' + w)),
    el('div', { class: 'row' },
      field('Character reference image (optional)', el('input', { type: 'file', accept: 'image/png,image/jpeg,image/webp', onchange: (ev) => { if (ev.target.files[0]) uploadRef(ev.target.files[0]); } })),
      plan.character.reference_image ? el('span', { class: 'muted' }, 'Reference: ' + plan.character.reference_image) : null,
      el('button', { type: 'button', class: 'ghost act', onclick: rebuildPrompts }, 'Rebuild prompts from fields')));
  $('#scenes').replaceChildren(...plan.scenes.map(sceneCard));
}

/* ---------- assemble ---------- */

function buildAssemble() {
  const sel = (id, label, opts, v) => selectField(id, label, opts, v);
  $('#assemble-form').append(
    el('div', { class: 'grid' },
      sel('a-aspect', 'Output format', [['16:9', '16:9 (1280x720)'], ['9:16', '9:16 (720x1280)'], ['1:1', '1:1 (960x960)']], '16:9'),
      el('label', { class: 'field' }, el('span', {}, 'Output FPS'), el('input', { id: 'a-fps', type: 'number', min: 8, max: 60, value: 24 })),
      sel('a-interp', 'Frame interpolation (FFmpeg, classical)', [['', 'off'], ['48', 'to 48 fps'], ['60', 'to 60 fps']], ''),
      el('label', { class: 'check' }, el('input', { id: 'a-denoise', type: 'checkbox' }), 'Light denoise (hqdn3d)')),
    el('h3', {}, 'Subtitles'),
    el('div', { class: 'grid' },
      el('label', { class: 'check' }, el('input', { id: 's-on', type: 'checkbox' }), 'Add subtitles'),
      sel('s-lang', 'Language', [['en', 'English'], ['ja', 'Japanese'], ['fa', 'Persian']], 'en'),
      el('label', { class: 'field' }, el('span', {}, 'Font family (must be installed or in backend/fonts)'), el('input', { id: 's-font', type: 'text', value: 'Arial', list: 'fonts' })),
      sel('s-pos', 'Position', [['bottom', 'bottom'], ['middle', 'middle'], ['top', 'top']], 'bottom'),
      el('label', { class: 'field' }, el('span', {}, 'Size'), el('input', { id: 's-size', type: 'number', min: 10, max: 200, value: 48 })),
      el('label', { class: 'field' }, el('span', {}, 'Outline'), el('input', { id: 's-outline', type: 'number', min: 0, max: 10, step: 0.5, value: 2 })),
      el('label', { class: 'field' }, el('span', {}, 'Timing offset (s)'), el('input', { id: 's-offset', type: 'number', min: -10, max: 10, step: 0.1, value: 0 })),
      el('label', { class: 'check' }, el('input', { id: 's-burn', type: 'checkbox', checked: true }), 'Burn into video (also writes .srt and .ass)')),
    el('datalist', { id: 'fonts' }, ['Arial', 'Vazirmatn', 'Noto Sans JP', 'Noto Sans Arabic'].map((f) => el('option', { value: f }))),
    el('p', {}, el('button', { type: 'button', class: 'primary act', onclick: assemble }, 'Assemble final MP4')));
}

async function assemble() {
  await guarded('Assembling...', async () => {
    const interp = $('#a-interp').value;
    const opts = {
      aspect_ratio: $('#a-aspect').value,
      fps: parseInt($('#a-fps').value, 10) || 24,
      interpolate_fps: interp ? parseInt(interp, 10) : null,
      denoise: $('#a-denoise').checked,
      subtitles: $('#s-on').checked ? {
        language: $('#s-lang').value,
        font: $('#s-font').value.trim() || 'Arial',
        position: $('#s-pos').value,
        size: parseInt($('#s-size').value, 10) || 48,
        outline: parseFloat($('#s-outline').value) || 0,
        offset: parseFloat($('#s-offset').value) || 0,
        burn_in: $('#s-burn').checked,
      } : null,
    };
    const r = await runJob('/projects/' + state.plan.project_id + '/assemble', opts, 'Assemble');
    const links = [el('a', { href: fileUrl(r.video), target: '_blank', rel: 'noopener', textContent: 'Open MP4' })];
    if (r.files && r.files.srt) links.push(el('a', { href: fileUrl(r.files.srt), target: '_blank', rel: 'noopener', textContent: '.srt' }));
    if (r.files && r.files.ass) links.push(el('a', { href: fileUrl(r.files.ass), target: '_blank', rel: 'noopener', textContent: '.ass' }));
    $('#final').replaceChildren(
      el('video', { src: fileUrl(r.video), controls: true }),
      el('p', {}, links),
      (r.warnings || []).map((w) => el('p', { class: 'warn' }, w)));
    setStatus('Final video ready (' + r.duration + ' s).', 'ok');
  });
}

/* ---------- boot ---------- */

window.addEventListener('DOMContentLoaded', () => {
  $('#backend').value = state.backend;
  $('#connect').addEventListener('click', connect);
  buildForm();
  buildAssemble();
  renderLayers(null);
  connect();
});
