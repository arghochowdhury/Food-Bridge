/* theme toggle + mobile menu */
(function () {
  const root = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  if (toggle) toggle.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('fb-theme', next); } catch (e) {}
  });
  const burger = document.getElementById('burger'), links = document.getElementById('links');
  if (burger && links) burger.addEventListener('click', () => links.classList.toggle('open'));
})();

/* animated background: rivers of light flowing under floating plates */
(function () {
  const c = document.getElementById('bg'); if (!c) return;
  const ctx = c.getContext('2d');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const icons = ['🍛', '🍲', '🥘', '🍗', '🥗', '🍚', '🍞', '🥭', '🌶️', '🍋'];
  let w, h, t = 0, plates = [];
  function size() {
    const d = window.devicePixelRatio || 1;
    w = innerWidth; h = innerHeight; c.width = w * d; c.height = h * d; ctx.setTransform(d, 0, 0, d, 0, 0);
    plates = Array.from({ length: Math.max(10, Math.round(w / 90)) }, () => ({
      x: Math.random() * w, y: Math.random() * h, s: 18 + Math.random() * 22,
      v: 0.15 + Math.random() * 0.35, p: Math.random() * 6.28, i: icons[(Math.random() * icons.length) | 0]
    }));
  }
  function rgb() { return getComputedStyle(document.documentElement).getPropertyValue('--wave').trim() || '15,118,110'; }
  function frame() {
    ctx.clearRect(0, 0, w, h);
    const col = rgb();
    for (let k = 0; k < 3; k++) {              // three flowing waves = the river
      ctx.beginPath(); ctx.moveTo(0, h);
      const base = h * (0.72 + k * 0.09), amp = 22 + k * 10, len = 0.004 - k * 0.0007;
      for (let x = 0; x <= w; x += 8) ctx.lineTo(x, base + Math.sin(x * len + t * (0.8 + k * 0.3) + k) * amp);
      ctx.lineTo(w, h); ctx.closePath();
      ctx.fillStyle = `rgba(${col},${0.07 + k * 0.04})`; ctx.fill();
    }
    ctx.globalAlpha = 0.28;                    // plates drifting across, bobbing on the waves
    plates.forEach(p => {
      p.x += p.v; if (p.x > w + 40) { p.x = -40; p.y = Math.random() * h; }
      const y = p.y + Math.sin(t * 1.2 + p.p) * 10;
      ctx.font = p.s + 'px serif'; ctx.fillText(p.i, p.x, y);
    });
    ctx.globalAlpha = 1;
    t += 0.016;
    if (!still) requestAnimationFrame(frame);
  }
  size(); addEventListener('resize', size); frame();
})();

/* cascading location menus: division > district > upazila > thana > post office */
(function () {
  const root = document.getElementById('loc'); if (!root) return;
  const api = root.dataset.api;
  const levels = ['division', 'district', 'upazila', 'thana', 'post_office'];
  const names = { district: 'district', upazila: 'upazila', thana: 'thana', post_office: 'post office' };
  const el = {}; levels.forEach(l => el[l] = document.getElementById('id_' + l));

  function clearFrom(i) {
    for (let j = i; j < levels.length; j++) {
      const s = el[levels[j]];
      s.innerHTML = `<option value="">Select ${names[levels[j]]}</option>`; s.disabled = true;
    }
  }
  async function load(i, parent) {
    clearFrom(i);
    if (i >= levels.length || !parent) return;
    const s = el[levels[i]];
    try {
      const r = await fetch(`${api}?level=${levels[i]}&parent=${parent}`);
      const data = await r.json();
      data.results.forEach(o => s.add(new Option(o.name, o.id)));
      s.disabled = false;
      const pre = s.dataset.selected; s.dataset.selected = '';
      if (pre) { s.value = pre; if (s.value) await load(i + 1, s.value); }
    } catch (e) { console.error('Location load failed', e); }
  }
  levels.slice(0, -1).forEach((l, i) => el[l].addEventListener('change', () => load(i + 1, el[l].value)));

  const div = el.division, pre = div.dataset.selected; div.dataset.selected = '';
  if (pre) { div.value = pre; if (div.value) load(1, div.value); }
})();


/* availability countdowns: <span class="countdown" data-end="ISO time"> */
(function () {
  const els = [...document.querySelectorAll('.countdown[data-end]')];
  if (!els.length) return;
  const meta = document.querySelector('meta[name="server-now"]');
  const offset = meta ? new Date(meta.content).getTime() - Date.now() : 0;   // follow the server clock
  const pad = n => String(n).padStart(2, '0');
  function fmt(ms) {
    const s = Math.floor(ms / 1000), d = Math.floor(s / 86400);
    return (d ? d + 'd ' : '') + pad(Math.floor(s % 86400 / 3600)) + ':' + pad(Math.floor(s % 3600 / 60)) + ':' + pad(s % 60);
  }
  document.addEventListener('countdown:end', e => {
    const card = e.target.closest('.card'); if (card) card.classList.add('expired');
  });
  function tick() {
    const now = Date.now() + offset;
    els.forEach(el => {
      if (el.classList.contains('ended')) return;
      const left = new Date(el.dataset.end).getTime() - now;
      if (isNaN(left)) return;
      if (left <= 0) {
        el.textContent = 'Time over'; el.classList.add('ended'); el.classList.remove('urgent');
        el.dispatchEvent(new CustomEvent('countdown:end', { bubbles: true }));
        return;
      }
      el.textContent = 'Ends in ' + fmt(left);
      el.classList.toggle('urgent', left < 3600000);
    });
  }
  tick(); setInterval(tick, 1000);
})();
