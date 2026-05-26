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
  initDropzone();
  initCheckbox();
  initReveal();
  initParallax();
  initMistCanvas();
  initTypewriter();
});

/* ════════════════════════════════════════════════════════════
   NAV — scroll border
════════════════════════════════════════════════════════════ */
function initNav() {
  const nav = document.getElementById('nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 80);
  }, { passive: true });
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
  showSkeleton();

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
function showSkeleton() {
  document.getElementById('emptyState').style.display    = 'none';
  document.getElementById('verdictCard').classList.remove('visible');
  document.getElementById('verdictCard').style.display  = 'none';
  document.getElementById('skeletonCard').classList.add('visible');
}

function renderEmpty() {
  document.getElementById('skeletonCard').classList.remove('visible');
  document.getElementById('verdictCard').classList.remove('visible');
  document.getElementById('verdictCard').style.display = 'none';
  document.getElementById('emptyState').style.display  = '';
  document.getElementById('forensicAccordion').classList.remove('visible');
}

function renderVerdict(data) {
  document.getElementById('skeletonCard').classList.remove('visible');
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
   MIST CANVAS — global mouse-interactive violet fog
   Fixed canvas behind the entire page, always running.
════════════════════════════════════════════════════════════ */
function initMistCanvas() {
  const canvas = document.getElementById('mistCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  /* Size canvas to viewport */
  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize, { passive: true });

  /* Track mouse / touch in viewport coords (0–1 normalised) */
  const target = { x: 0.5, y: 0.4 };

  window.addEventListener('mousemove', (e) => {
    target.x = e.clientX / window.innerWidth;
    target.y = e.clientY / window.innerHeight;
  }, { passive: true });

  window.addEventListener('touchmove', (e) => {
    target.x = e.touches[0].clientX / window.innerWidth;
    target.y = e.touches[0].clientY / window.innerHeight;
  }, { passive: true });

  /* Orb definitions (normalised 0-1 coords) */
  const orbs = [
    /* Primary — follows mouse with soft lerp */
    { ox: 0.5,  oy: 0.4,  r: 0.65, a: 0.22, speed: 0.055, drift: null },
    /* Secondary — slow autonomous drift */
    { ox: 0.2,  oy: 0.3,  r: 0.45, a: 0.12, speed: 0,     drift: { vx:  0.00010, vy:  0.00007 } },
    { ox: 0.75, oy: 0.6,  r: 0.42, a: 0.11, speed: 0,     drift: { vx: -0.00009, vy:  0.00010 } },
    { ox: 0.5,  oy: 0.9,  r: 0.35, a: 0.08, speed: 0,     drift: { vx:  0.00007, vy: -0.00009 } },
    { ox: 0.85, oy: 0.15, r: 0.30, a: 0.07, speed: 0,     drift: { vx: -0.00006, vy:  0.00008 } },
  ];

  /* Violet RGB values matching --accent #8B5CF6 */
  const R = 139, G = 92, B = 246;

  function drawOrb(orb) {
    const w  = canvas.width;
    const h  = canvas.height;
    const cx = orb.ox * w;
    const cy = orb.oy * h;
    const radius = orb.r * Math.max(w, h);

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    grad.addColorStop(0,    `rgba(${R},${G},${B},${orb.a})`);
    grad.addColorStop(0.4,  `rgba(${R},${G},${B},${(orb.a * 0.35).toFixed(3)})`);
    grad.addColorStop(1,    `rgba(${R},${G},${B},0)`);

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function frame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    orbs.forEach(orb => {
      if (orb.speed > 0) {
        /* Smooth follow */
        orb.ox += (target.x - orb.ox) * orb.speed;
        orb.oy += (target.y - orb.oy) * orb.speed;
      } else if (orb.drift) {
        /* Autonomous drift — wrap at extended bounds */
        orb.ox += orb.drift.vx;
        orb.oy += orb.drift.vy;
        if (orb.ox >  1.25) orb.ox = -0.25;
        if (orb.ox < -0.25) orb.ox =  1.25;
        if (orb.oy >  1.25) orb.oy = -0.25;
        if (orb.oy < -0.25) orb.oy =  1.25;
      }
      drawOrb(orb);
    });

    requestAnimationFrame(frame);
  }

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
