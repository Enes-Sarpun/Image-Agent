/* ═══════════════════════════════════════════════════════════
   Image Agent — script.js
   Vanilla JS, no framework, no bundler
═══════════════════════════════════════════════════════════ */

'use strict';

/* ── State ── */
let currentFile    = null;
let isAnalyzing    = false;
let cacheEnabled   = true;
const API_BASE     = '';
const MAX_SIZE_MB  = 20;
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

/* ── Source label map ── */
const SOURCE_LABELS = {
  watermark:             'Watermark Tespiti',
  llm:                   'LLM Analizi',
  'llm+forensic':        'LLM + Forensic',
  'multi_pass+forensic': 'Multi-Pass + Forensic',
  'llm_search+forensic': 'LLM + Web Search',
  cache:                 'Önbellekten',
};

/* ════════════════════════════════════════════════════════════
   INIT
════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initHamburger();
  initDropzone();
  initCheckbox();
  initReveal();
  initParallax();
  initNeuralCanvas();
  initMistCanvas();
  initTypewriter();
  initPipelineObserver();
});

/* ════════════════════════════════════════════════════════════
   NAV — scroll border
════════════════════════════════════════════════════════════ */
function initNav() {
  const nav = document.getElementById('nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 8);
  }, { passive: true });

  /* ── Glider: dynamic position via getBoundingClientRect ── */
  const glider  = document.getElementById('navGlider');
  const segment = document.getElementById('navSegment');
  if (!glider || !segment) return;

  const segLinks = Array.from(segment.querySelectorAll('.nav-link'));

  function setActive(link) {
    segLinks.forEach(l => {
      l.classList.toggle('active', l === link);
      l.setAttribute('aria-current', l === link ? 'page' : 'false');
    });
    // Position glider using live bounding rects (works at any viewport size)
    const segRect  = segment.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();
    glider.style.transform = `translateX(${linkRect.left - segRect.left}px)`;
    glider.style.width     = `${linkRect.width}px`;
  }

  // Click on segment links
  segLinks.forEach(link => {
    link.addEventListener('click', () => setActive(link));
  });

  // Scroll-spy: track which section is most visible
  const sections = segLinks
    .map(l => l.getAttribute('href'))
    .filter(h => h && h.startsWith('#'))
    .map(h => document.querySelector(h))
    .filter(Boolean);

  if (sections.length) {
    const spy = new IntersectionObserver((entries) => {
      const visible = entries.filter(e => e.isIntersecting);
      if (!visible.length) return;
      const best = visible.reduce((a, b) =>
        a.intersectionRatio >= b.intersectionRatio ? a : b
      );
      const href  = '#' + best.target.id;
      const match = segLinks.find(l => l.getAttribute('href') === href);
      if (match) setActive(match);
    }, { threshold: [0.2, 0.5] });
    sections.forEach(s => spy.observe(s));
  }

  // Initial render (wait one frame so layout is settled)
  requestAnimationFrame(() => {
    if (segLinks[0]) setActive(segLinks[0]);
  });

  // Recalculate glider position on window resize
  window.addEventListener('resize', () => {
    const active = segment.querySelector('.nav-link.active') || segLinks[0];
    if (active) requestAnimationFrame(() => setActive(active));
  }, { passive: true });
}

/* ════════════════════════════════════════════════════════════
   HAMBURGER — mobile nav toggle
════════════════════════════════════════════════════════════ */
function initHamburger() {
  const btn   = document.getElementById('navHamburger');
  const nav   = document.getElementById('nav');
  const links = document.getElementById('navLinks');
  if (!btn || !links) return;

  function openMenu() {
    nav.classList.add('menu-open');
    links.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    btn.setAttribute('aria-label', 'Menüyü kapat');
    document.body.style.overflow = 'hidden'; // prevent background scroll
  }

  function closeMenu() {
    nav.classList.remove('menu-open');
    links.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Menüyü aç');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', () => {
    nav.classList.contains('menu-open') ? closeMenu() : openMenu();
  });

  /* Close on link click or Escape */
  links.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', closeMenu);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('menu-open')) closeMenu();
  });
}

/* ════════════════════════════════════════════════════════════
   DROPZONE
════════════════════════════════════════════════════════════ */
function initDropzone() {
  const dropzone   = document.getElementById('dropzone');
  const fileInput  = document.getElementById('fileInput');
  const clearBtn   = document.getElementById('previewClear');
  const analyzeBtn = document.getElementById('analyzeBtn');

  /* Click on dropzone → open file dialog (but not if clicking clear btn) */
  dropzone.addEventListener('click', (e) => {
    if (e.target === clearBtn || clearBtn.contains(e.target)) return;
    if (dropzone.classList.contains('has-preview')) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) handleFileSelect(fileInput.files[0]);
  });

  /* Drag & drop */
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', (e) => {
    if (!dropzone.contains(e.relatedTarget)) dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileSelect(file);
  });

  /* Clear preview */
  clearBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFile();
  });

  /* Analyze button */
  analyzeBtn.addEventListener('click', analyzeImage);
}

/* ════════════════════════════════════════════════════════════
   FILE HANDLING
════════════════════════════════════════════════════════════ */
function handleFileSelect(file) {
  /* Validation */
  if (!ALLOWED_TYPES.includes(file.type)) {
    showToast('Desteklenmeyen dosya türü. JPG, PNG, WEBP veya GIF yükleyin.', 'error');
    return;
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    showToast(`Dosya çok büyük. Maksimum ${MAX_SIZE_MB}MB.`, 'error');
    return;
  }

  currentFile = file;

  /* Show preview */
  const dropzone  = document.getElementById('dropzone');
  const previewImg = document.getElementById('previewImg');
  const previewMeta = document.getElementById('previewMeta');

  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewMeta.textContent = `${file.name} · ${formatBytes(file.size)}`;

  dropzone.classList.add('has-preview');
  document.getElementById('analyzeBtn').disabled = false;
}

function clearFile() {
  currentFile = null;

  const dropzone   = document.getElementById('dropzone');
  const previewImg = document.getElementById('previewImg');
  const fileInput  = document.getElementById('fileInput');

  if (previewImg.src) URL.revokeObjectURL(previewImg.src);
  previewImg.src = '';
  fileInput.value = '';
  dropzone.classList.remove('has-preview');
  document.getElementById('analyzeBtn').disabled = true;
  renderEmpty();
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ════════════════════════════════════════════════════════════
   CHECKBOX
════════════════════════════════════════════════════════════ */
function initCheckbox() {
  const label = document.getElementById('cacheLabel');
  const box   = document.getElementById('cacheBox');

  label.addEventListener('click', () => {
    cacheEnabled = !cacheEnabled;
    box.classList.toggle('checked', cacheEnabled);
  });
}

/* ════════════════════════════════════════════════════════════
   ANALYZE
════════════════════════════════════════════════════════════ */
async function analyzeImage() {
  if (!currentFile || isAnalyzing) return;
  isAnalyzing = true;
  setButtonLoading(true);
  showLoading();

  const formData = new FormData();
  formData.append('image', currentFile);
  formData.append('use_cache', cacheEnabled ? 'true' : 'false');

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      } catch {}
      throw new Error(msg);
    }

    const data = await res.json();
    renderVerdict(data);

  } catch (err) {
    showToast(err.message || 'Analiz sırasında bir hata oluştu.', 'error');
    renderEmpty();
  } finally {
    isAnalyzing = false;
    setButtonLoading(false);
  }
}

function setButtonLoading(loading) {
  const btn = document.getElementById('analyzeBtn');
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
  btn.querySelector('.btn-text').textContent = loading ? 'Analiz ediliyor...' : 'Analiz Et';
}

/* ════════════════════════════════════════════════════════════
   RENDER STATES
════════════════════════════════════════════════════════════ */
function showLoading() {
  document.getElementById('emptyState').style.display   = 'none';
  document.getElementById('verdictCard').classList.remove('visible');
  document.getElementById('verdictCard').style.display  = 'none';
  document.getElementById('resultLoader').classList.add('visible');
}

function renderEmpty() {
  document.getElementById('resultLoader').classList.remove('visible');
  document.getElementById('verdictCard').classList.remove('visible');
  document.getElementById('verdictCard').style.display = 'none';
  document.getElementById('emptyState').style.display  = '';
  document.getElementById('forensicAccordion').classList.remove('visible');
}

function renderVerdict(data) {
  document.getElementById('resultLoader').classList.remove('visible');
  document.getElementById('emptyState').style.display = 'none';

  const { verdict, confidence, reasoning, key_indicators, source, elapsed_ms } = data;

  /* Determine class */
  let cls, labelText, iconId;
  if (verdict === 'ai') {
    cls = 'verdict-ai';
    labelText = 'AI Üretimi';
    iconId = 'icon-alert';
  } else if (verdict === 'real') {
    cls = 'verdict-real';
    labelText = 'Gerçek Fotoğraf';
    iconId = 'icon-camera';
  } else {
    cls = 'verdict-uncertain';
    labelText = 'Belirsiz';
    iconId = 'icon-help';
  }

  /* Source label */
  const sourceLabel = SOURCE_LABELS[source] || source;
  const elapsed = elapsed_ms != null ? `${(elapsed_ms / 1000).toFixed(1)}s` : '';

  /* Set card class */
  const card = document.getElementById('verdictCard');
  card.className = `verdict-card ${cls}`;

  /* Verdict label */
  document.getElementById('verdictLabel').innerHTML =
    `<svg width="28" height="28" style="vertical-align:-6px;margin-right:10px;"><use href="#${iconId}"/></svg>${labelText}`;

  /* Confidence (will be animated via countUp) */
  const confEl = document.getElementById('verdictConfidence');
  confEl.textContent = '%0';

  /* Progress bar — reset before animating */
  const bar = document.getElementById('verdictBar');
  bar.style.transition = 'none';
  bar.style.width = '0%';

  /* Meta */
  const metaEl = document.getElementById('verdictMeta');
  let metaHTML = `<svg width="13" height="13" style="flex-shrink:0"><use href="#icon-clock"/></svg> ${elapsed}`;
  if (sourceLabel) metaHTML += `<span class="verdict-meta-sep">·</span>${sourceLabel}`;
  metaEl.innerHTML = metaHTML;

  /* Reasoning */
  document.getElementById('verdictReasoning').textContent = reasoning || '';

  /* Indicators */
  const indContainer = document.getElementById('verdictIndicators');
  if (key_indicators && key_indicators.length) {
    let html = '<div class="verdict-indicators-label">Anahtar İpuçları</div>';
    key_indicators.forEach((ind, i) => {
      html += `<div class="verdict-indicator" style="animation-delay:${400 + i * 60}ms">${ind}</div>`;
    });
    indContainer.innerHTML = html;
  } else {
    indContainer.innerHTML = '';
  }

  /* Show card */
  card.style.display = 'block';
  requestAnimationFrame(() => {
    card.classList.add('visible');

    /* Animate indicators */
    card.querySelectorAll('.verdict-indicator').forEach(el => {
      el.style.animation = `fadeUp var(--dur-slow) var(--ease-out-expo) ${el.style.animationDelay} forwards`;
    });

    /* After card enters, animate confidence + bar */
    setTimeout(() => {
      countUp(confEl, confidence, 800);
      setTimeout(() => {
        bar.style.transition = 'width 800ms var(--ease-out-expo)';
        bar.style.width = `${confidence}%`;
      }, 160);
    }, 80);
  });

  /* Show forensic accordion */
  document.getElementById('forensicAccordion').classList.add('visible');
  initAccordion();
}

/* ════════════════════════════════════════════════════════════
   COUNT-UP
════════════════════════════════════════════════════════════ */
function countUp(el, target, duration) {
  const start     = performance.now();
  const startVal  = 0;

  function easeOutExpo(t) {
    return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
  }

  function frame(now) {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const value    = startVal + (target - startVal) * easeOutExpo(progress);
    el.textContent = `%${value.toFixed(1)}`;
    if (progress < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

/* ════════════════════════════════════════════════════════════
   ACCORDION
════════════════════════════════════════════════════════════ */
function initAccordion() {
  const accordion = document.getElementById('forensicAccordion');
  const summary   = document.getElementById('accordionSummary');

  /* Remove any old listener by cloning */
  const newSummary = summary.cloneNode(true);
  summary.parentNode.replaceChild(newSummary, summary);

  newSummary.addEventListener('click', () => {
    accordion.classList.toggle('open');
  });
}

/* ════════════════════════════════════════════════════════════
   TOAST
════════════════════════════════════════════════════════════ */
function showToast(message, type = 'error') {
  const container = document.getElementById('toastContainer');

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconId = type === 'error' ? 'icon-alert' : 'icon-check';
  toast.innerHTML = `
    <svg width="14" height="14" style="flex-shrink:0"><use href="#${iconId}"/></svg>
    <span>${message}</span>
    <button style="margin-left:auto;background:none;border:none;cursor:pointer;color:var(--text-muted);padding:2px;" onclick="dismissToast(this.parentElement)">
      <svg width="12" height="12"><use href="#icon-x"/></svg>
    </button>
  `;

  container.appendChild(toast);

  /* Auto dismiss */
  setTimeout(() => dismissToast(toast), 4000);
}

function dismissToast(toast) {
  if (!toast || !toast.parentElement) return;
  toast.classList.add('hiding');
  toast.addEventListener('animationend', () => toast.remove(), { once: true });
}

/* ════════════════════════════════════════════════════════════
   SCROLL REVEAL
════════════════════════════════════════════════════════════ */
function initReveal() {
  const observer = new IntersectionObserver(
    (entries) => entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        observer.unobserve(e.target);
      }
    }),
    { threshold: 0.1 }
  );
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

/* ════════════════════════════════════════════════════════════
   PIPELINE STEP OBSERVER — highlights step as it scrolls into view
════════════════════════════════════════════════════════════ */
function initPipelineObserver() {
  const steps = document.querySelectorAll('.step');
  if (!steps.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      e.target.classList.toggle('active', e.isIntersecting);
    });
  }, { threshold: 0.5 });

  steps.forEach(step => observer.observe(step));
}

/* ════════════════════════════════════════════════════════════
   HERO PARALLAX
════════════════════════════════════════════════════════════ */
function initParallax() {
  const heroInner = document.getElementById('heroInner');
  if (!heroInner) return;

  window.addEventListener('scroll', () => {
    const y  = window.scrollY;
    const vh = window.innerHeight;
    if (y > vh) return;
    const p = y / vh;
    heroInner.style.transform = `translateY(${y * 0.3}px)`;
    heroInner.style.opacity   = `${1 - p * 1.5}`;
  }, { passive: true });
}

/* ════════════════════════════════════════════════════════════
   NEURAL CANVAS  v3
   ─────────────────────────────────────────────────────────
   Architecture
   ┌─ Spatial grid  O(n) neighbour search instead of O(n²)
   ├─ Spring-damper physics  (home → scatter → snap)
   ├─ Scroll velocity  → dynamic connectDist + hue shift
   ├─ Hero IntersectionObserver → opacity fade + rAF pause
   ├─ Scroll parallax translateY for depth
   ├─ visibilitychange + reduced-motion guards
   └─ Adaptive node count (mobile: 120, desktop: 220)
════════════════════════════════════════════════════════════ */
function initNeuralCanvas() {
  const canvas = document.getElementById('neuralCanvas');
  if (!canvas) return;

  /* ── reduced-motion: skip animation entirely ── */
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const ctx = canvas.getContext('2d', { alpha: true });

  /* ── viewport ── */
  let W = 0, H = 0;
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    buildGrid();
  }

  /* ── scroll state ── */
  let rawScroll  = 0;
  let scrollVel  = 0;
  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    rawScroll = window.scrollY;
    /* Parallax depth: canvas lags ~15% behind scroll */
    canvas.style.transform = `translateY(${rawScroll * -0.15}px)`;
  }, { passive: true });

  /* ── mouse ── */
  const mouse = { x: -9999, y: -9999, active: false };
  window.addEventListener('mousemove', e => {
    mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true;
  }, { passive: true });
  window.addEventListener('mouseleave', () => { mouse.active = false; });

  /* ════════════════ CONSTANTS ════════════════ */
  const N              = 220;     // max node pool
  let   activeN        = window.innerWidth < 720 ? 120 : N;
  const BASE_DIST      = 185;
  const MAX_DIST_BONUS = 80;
  const SCATTER_R      = 140;
  const SPRING_K       = 0.022;
  const DAMPING        = 0.88;
  const REPULSE_STR    = 26;
  const DRIFT_SPD      = 0.45;

  /* ════════════════ PALETTE ════════════════ */
  const PAL = [
    [15,  20,  50 ],
    [22,  18,  80 ],
    [55,  20,  130],
    [90,  35,  200],
    [109, 40,  217],
    [139, 92,  246],
    [167, 139, 250],
    [200, 170, 255],
  ];

  /* ════════════════ NODE POOL ════════════════ */
  const hx    = new Float32Array(N);
  const hy    = new Float32Array(N);
  const px    = new Float32Array(N);
  const py    = new Float32Array(N);
  const vx    = new Float32Array(N);
  const vy    = new Float32Array(N);
  const ddx   = new Float32Array(N);
  const ddy   = new Float32Array(N);
  const rad   = new Float32Array(N);
  const alpha = new Float32Array(N);
  const phase = new Float32Array(N);
  const colR  = new Uint8Array(N);
  const colG  = new Uint8Array(N);
  const colB  = new Uint8Array(N);

  function initNodes() {
    for (let i = 0; i < N; i++) {
      const c = PAL[Math.floor(Math.random() * PAL.length)];
      hx[i]    = Math.random() * W;
      hy[i]    = (i / N) * H + Math.random() * (H / N);
      px[i]    = hx[i];
      py[i]    = hy[i];
      vx[i]    = 0; vy[i] = 0;
      ddx[i]   = (Math.random() - 0.5) * DRIFT_SPD;
      ddy[i]   = (Math.random() - 0.5) * DRIFT_SPD * 0.6;
      rad[i]   = 1.8 + Math.random() * 3.0;
      alpha[i] = 0.55 + Math.random() * 0.45;
      phase[i] = Math.random() * Math.PI * 2;
      colR[i]  = c[0]; colG[i] = c[1]; colB[i] = c[2];
    }
  }

  /* ════════════════ SPATIAL GRID ════════════════ */
  let CELL = 0, COLS = 0, ROWS_G = 0;
  let grid;

  function buildGrid() {
    CELL   = BASE_DIST + MAX_DIST_BONUS;
    COLS   = Math.ceil(W / CELL) + 1;
    ROWS_G = Math.ceil(H / CELL) + 1;
    grid   = Array.from({ length: COLS * ROWS_G }, () => []);
  }

  function clearGrid() {
    if (!grid) return;
    for (let i = 0; i < grid.length; i++) grid[i].length = 0;
  }

  function insertGrid(i) {
    const cx = (px[i] / CELL) | 0;
    const cy = (py[i] / CELL) | 0;
    if (cx < 0 || cx >= COLS || cy < 0 || cy >= ROWS_G) return;
    grid[cy * COLS + cx].push(i);
  }

  /* ════════════════ DRAW HELPERS ════════════════ */
  function drawNode(i, pulse) {
    const x  = px[i], y = py[i];
    const pr = Math.max(0.5, rad[i] * (1 + pulse * 0.35));
    const a  = alpha[i] * (0.75 + pulse * 0.25);
    const R  = colR[i], G = colG[i], B = colB[i];
    const glowR = pr * 5;

    const g = ctx.createRadialGradient(x, y, 0, x, y, glowR);
    g.addColorStop(0,    `rgba(${R},${G},${B},${(a * 0.80).toFixed(3)})`);
    g.addColorStop(0.30, `rgba(${R},${G},${B},${(a * 0.25).toFixed(3)})`);
    g.addColorStop(1,    `rgba(${R},${G},${B},0)`);
    ctx.beginPath();
    ctx.arc(x, y, glowR, 0, 6.2832);
    ctx.fillStyle = g;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(x, y, pr, 0, 6.2832);
    ctx.fillStyle = `rgba(${R},${G},${B},${a.toFixed(3)})`;
    ctx.fill();
  }

  function drawEdge(i, j, dist, connectDist, hueShift) {
    const prox  = 1 - dist / connectDist;
    const ea    = prox * prox * (0.32 + hueShift * 0.22);
    const blend = prox * 0.45 + hueShift * 0.25;
    const iT    = 1 - blend;
    const eR = ((colR[i] + colR[j]) * 0.5 * iT + 139 * blend) | 0;
    const eG = ((colG[i] + colG[j]) * 0.5 * iT + 92  * blend) | 0;
    const eB = ((colB[i] + colB[j]) * 0.5 * iT + 246 * blend) | 0;

    ctx.beginPath();
    ctx.moveTo(px[i], py[i]);
    ctx.lineTo(px[j], py[j]);
    ctx.strokeStyle = `rgba(${eR},${eG},${eB},${ea.toFixed(3)})`;
    ctx.lineWidth   = prox * 1.4;
    ctx.stroke();
  }

  /* ════════════════ HERO VISIBILITY ════════════════ */
  let heroRatio = 1;  // 0–1 intersection ratio

  /* Smooth CSS opacity transition */
  canvas.style.transition = 'opacity 0.6s ease';

  const heroEl = document.getElementById('hero');
  if (heroEl) {
    const thresholds = Array.from({ length: 11 }, (_, i) => i / 10);
    new IntersectionObserver((entries) => {
      const e = entries[0];
      heroRatio = e.intersectionRatio;
      /* Fade to ~15% opacity when hero is off-screen */
      canvas.style.opacity = String(Math.max(0.15, heroRatio));
      if (e.isIntersecting && rafId === null)  startLoop();
      else if (!e.isIntersecting)              stopLoop();
    }, { threshold: thresholds }).observe(heroEl);
  }

  /* ════════════════ rAF CONTROL ════════════════ */
  let rafId = null;
  let t     = 0;

  function startLoop() {
    if (rafId !== null) return;
    rafId = requestAnimationFrame(tick);
  }

  function stopLoop() {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
  }

  function tick() {
    rafId = requestAnimationFrame(tick);
    t += 0.007;

    const rawVel = rawScroll - lastScroll;
    scrollVel    = scrollVel * 0.85 + rawVel * 0.15;
    lastScroll   = rawScroll;

    const speedFactor = Math.min(Math.abs(scrollVel) / 12, 1);
    /* Connections thin out as hero scrolls away */
    const connectDist = BASE_DIST * (0.45 + heroRatio * 0.55) + speedFactor * MAX_DIST_BONUS * heroRatio;
    const hueShift    = speedFactor;

    clearGrid();
    for (let i = 0; i < activeN; i++) {
      hx[i] += ddx[i];
      hy[i] += ddy[i];
      if (hx[i] < -80) { hx[i] = W + 80; hy[i] = Math.random() * H; }
      else if (hx[i] > W + 80) { hx[i] = -80; hy[i] = Math.random() * H; }
      if (hy[i] < -80) { hy[i] = H + 80; hx[i] = Math.random() * W; }
      else if (hy[i] > H + 80) { hy[i] = -80; hx[i] = Math.random() * W; }

      vx[i] += (hx[i] - px[i]) * SPRING_K;
      vy[i] += (hy[i] - py[i]) * SPRING_K;

      if (mouse.active) {
        const dx = px[i] - mouse.x;
        const dy = py[i] - mouse.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < SCATTER_R * SCATTER_R && d2 > 0.01) {
          const d     = Math.sqrt(d2);
          const force = (1 - d / SCATTER_R);
          const f     = force * force * REPULSE_STR;
          vx[i] += (dx / d) * f;
          vy[i] += (dy / d) * f;
        }
      }

      vx[i] *= DAMPING;
      vy[i] *= DAMPING;
      px[i] += vx[i];
      py[i] += vy[i];

      if (py[i] > -60 && py[i] < H + 60) insertGrid(i);
    }

    ctx.clearRect(0, 0, W, H);

    const distSq = connectDist * connectDist;
    for (let i = 0; i < activeN; i++) {
      if (py[i] < -60 || py[i] > H + 60) continue;
      const cx = (px[i] / CELL) | 0;
      const cy = (py[i] / CELL) | 0;

      for (let ny2 = cy - 1; ny2 <= cy + 1; ny2++) {
        if (ny2 < 0 || ny2 >= ROWS_G) continue;
        for (let nx2 = cx - 1; nx2 <= cx + 1; nx2++) {
          if (nx2 < 0 || nx2 >= COLS) continue;
          const cell = grid[ny2 * COLS + nx2];
          for (let k = 0; k < cell.length; k++) {
            const j = cell[k];
            if (j <= i) continue;
            const dx = px[i] - px[j];
            const dy = py[i] - py[j];
            const d2 = dx * dx + dy * dy;
            if (d2 < distSq) drawEdge(i, j, Math.sqrt(d2), connectDist, hueShift);
          }
        }
      }
    }

    for (let i = 0; i < activeN; i++) {
      if (py[i] < -60 || py[i] > H + 60) continue;
      const pulse = Math.sin(t * 1.6 + phase[i]) * 0.5 + 0.5;
      drawNode(i, pulse);
    }
  }

  /* ── visibilitychange: pause when tab is hidden ── */
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopLoop();
    } else if (heroRatio > 0) {
      startLoop();
    }
  });

  /* ── init & start ── */
  resize();
  initNodes();
  window.addEventListener('resize', () => {
    activeN = window.innerWidth < 720 ? 120 : N;
    resize();
    initNodes();
  }, { passive: true });
  startLoop();
}

/* ════════════════════════════════════════════════════════════
   MIST CANVAS — global mouse-interactive violet fog
   Fixed aurora layer; always visible but calm opacity.
════════════════════════════════════════════════════════════ */
function initMistCanvas() {
  const canvas = document.getElementById('mistCanvas');
  if (!canvas) return;

  /* ── reduced-motion: skip animation ── */
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize, { passive: true });

  const target = { x: 0.5, y: 0.4 };
  window.addEventListener('mousemove', (e) => {
    target.x = e.clientX / window.innerWidth;
    target.y = e.clientY / window.innerHeight;
  }, { passive: true });
  window.addEventListener('touchmove', (e) => {
    target.x = e.touches[0].clientX / window.innerWidth;
    target.y = e.touches[0].clientY / window.innerHeight;
  }, { passive: true });

  /* Orb alphas reduced ~25% for calmer aurora feel */
  const orbs = [
    { ox: 0.5,  oy: 0.4,  r: 0.70, a: 0.20, speed: 0.055, drift: null },
    { ox: 0.2,  oy: 0.3,  r: 0.52, a: 0.12, speed: 0,     drift: { vx:  0.00010, vy:  0.00007 } },
    { ox: 0.75, oy: 0.6,  r: 0.48, a: 0.10, speed: 0,     drift: { vx: -0.00009, vy:  0.00010 } },
    { ox: 0.5,  oy: 0.9,  r: 0.40, a: 0.08, speed: 0,     drift: { vx:  0.00007, vy: -0.00009 } },
    { ox: 0.85, oy: 0.15, r: 0.35, a: 0.06, speed: 0,     drift: { vx: -0.00006, vy:  0.00008 } },
  ];

  const R = 139, G = 92, B = 246;

  function drawOrb(orb) {
    const w  = canvas.width;
    const h  = canvas.height;
    const cx = orb.ox * w;
    const cy = orb.oy * h;
    const radius = orb.r * Math.max(w, h);

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    grad.addColorStop(0,    `rgba(${R},${G},${B},${orb.a})`);
    grad.addColorStop(0.25, `rgba(${R},${G},${B},${(orb.a * 0.70).toFixed(3)})`);
    grad.addColorStop(0.55, `rgba(${R},${G},${B},${(orb.a * 0.30).toFixed(3)})`);
    grad.addColorStop(1,    `rgba(${R},${G},${B},0)`);

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  let mistRafId = null;

  function frame() {
    mistRafId = requestAnimationFrame(frame);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    orbs.forEach(orb => {
      if (orb.speed > 0) {
        orb.ox += (target.x - orb.ox) * orb.speed;
        orb.oy += (target.y - orb.oy) * orb.speed;
      } else if (orb.drift) {
        orb.ox += orb.drift.vx;
        orb.oy += orb.drift.vy;
        if (orb.ox >  1.25) orb.ox = -0.25;
        if (orb.ox < -0.25) orb.ox =  1.25;
        if (orb.oy >  1.25) orb.oy = -0.25;
        if (orb.oy < -0.25) orb.oy =  1.25;
      }
      drawOrb(orb);
    });
  }

  /* ── visibilitychange: pause when tab hidden ── */
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (mistRafId !== null) { cancelAnimationFrame(mistRafId); mistRafId = null; }
    } else {
      if (mistRafId === null) { mistRafId = requestAnimationFrame(frame); }
    }
  });

  frame();
}

/* ════════════════════════════════════════════════════════════
   TYPEWRITER — statement section
════════════════════════════════════════════════════════════ */
function initTypewriter() {
  const container = document.getElementById('statementText');
  const template  = document.getElementById('statementRaw');
  if (!container || !template) return;

  const raw     = template.content.textContent.trim();
  const typed   = container.querySelector('.statement-typed');
  const cursor  = container.querySelector('.typewriter-cursor');

  /* Split into segments: plain text or <strong>...</strong> */
  const STRONG_MARKER = '[[STRONG]]';
  const STRONG_END    = '[[/STRONG]]';
  const rawMarked = raw
    .replace('Image Agent, buna çok katmanlı bir yanıt sunuyor.', `${STRONG_MARKER}Image Agent, buna çok katmanlı bir yanıt sunuyor.${STRONG_END}`);

  /* Build flat char array with metadata */
  const chars = [];
  let inStrong = false;
  let i = 0;
  while (i < rawMarked.length) {
    if (rawMarked.startsWith(STRONG_MARKER, i)) {
      inStrong = true;
      i += STRONG_MARKER.length;
    } else if (rawMarked.startsWith(STRONG_END, i)) {
      inStrong = false;
      i += STRONG_END.length;
    } else if (rawMarked[i] === '\\' && rawMarked[i + 1] === 'n') {
      chars.push({ ch: '\n', strong: inStrong });
      i += 2;
    } else {
      chars.push({ ch: rawMarked[i], strong: inStrong });
      i++;
    }
  }

  /* Speed: ms per character */
  const CHAR_DELAY = 28;
  let charIndex = 0;
  let started   = false;

  function renderChars() {
    let html = '';
    let openStrong = false;
    for (let j = 0; j < charIndex; j++) {
      const { ch, strong } = chars[j];
      if (strong && !openStrong) { html += '<strong>'; openStrong = true; }
      if (!strong && openStrong) { html += '</strong>'; openStrong = false; }
      if (ch === '\n') { html += '<br>'; }
      else             { html += ch; }
    }
    if (openStrong) html += '</strong>';
    typed.innerHTML = html;
  }

  function typeNext() {
    if (charIndex >= chars.length) {
      /* Done — keep cursor blinking for a moment then hide */
      setTimeout(() => { if (cursor) cursor.style.display = 'none'; }, 2000);
      return;
    }
    charIndex++;
    renderChars();
    /* Slightly longer pause after sentence-ending punctuation */
    const ch = chars[charIndex - 1].ch;
    const delay = (ch === '.' || ch === '?' || ch === '!') ? CHAR_DELAY * 8 : CHAR_DELAY;
    setTimeout(typeNext, delay);
  }

  /* Start typing when section scrolls into view */
  const obs = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !started) {
      started = true;
      obs.disconnect();
      setTimeout(typeNext, 300);
    }
  }, { threshold: 0.3 });
  obs.observe(container);
}
