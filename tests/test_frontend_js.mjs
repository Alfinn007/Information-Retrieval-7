import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const appJsPath = path.resolve('web/app.js');
const appJsCode = fs.readFileSync(appJsPath, 'utf8');

function createElement(id = '') {
  return {
    id,
    value: '',
    textContent: '',
    innerHTML: '',
    style: { display: '' },
    children: [],
    classList: {
      _set: new Set(),
      add(...cls) { cls.forEach(c => this._set.add(c)); },
      remove(...cls) { cls.forEach(c => this._set.delete(c)); },
      toggle(c) {
        if (this._set.has(c)) { this._set.delete(c); return false; }
        this._set.add(c); return true;
      },
      contains(c) { return this._set.has(c); }
    },
    listeners: {},
    _selectors: {},
    addEventListener(ev, fn) {
      this.listeners[ev] = this.listeners[ev] || [];
      this.listeners[ev].push(fn);
    },
    appendChild(child) { this.children.push(child); },
    querySelector(sel) {
      if ([
        '.btn-toggle-detail', '.card-accordion', '.btn-copy-spec', '.toast-msg',
        '.btn-toggle-variants', '.variants-extra', '.variants-title'
      ].includes(sel)) {
        if (!this._selectors[sel]) {
          this._selectors[sel] = createElement(sel);
        }
        return this._selectors[sel];
      }
      return null;
    },
    getAttribute() { return ''; },
    focus() {},
    scrollIntoView() { this._scrolled = true; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 100, height: 100 }; },
  };
}

function setupHarness(fetchImpl) {
  const elements = new Map();
  const ids = [
    'search-form', 'search-input', 'link-lihat-hasil', 'cards-container',
    'loading-state', 'empty-state', 'error-state', 'error-state-message',
    'btn-retry-search', 'summary-query', 'container-constraints',
    'container-matched', 'expanded-query-text', 'price-note-text',
    'relaxed-banner', 'result-counter', 'sticker-brand', 'sticker-date',
    'mobile-floating-btn', 'btn-sort-rel',
    'btn-scroll-top', 'laptop-chassis', 'hero-stage',
    'btn-sound-toggle', 'retro-toast', 'screen-container', 'hasil', 'hero',
    'btn-cta-search', 'screen-doc-count', 'footer-dataset-meta'
  ];
  ids.forEach(id => elements.set(id, createElement(id)));

  let domReadyCb = null;
  const document = {
    getElementById(id) { return elements.get(id) || null; },
    querySelectorAll() { return []; },
    createElement(tag) { return createElement(tag); },
    addEventListener(ev, fn) { if (ev === 'DOMContentLoaded') domReadyCb = fn; },
  };

  const window = {
    matchMedia() { return { matches: false }; },
    addEventListener() {},
    scrollY: 0,
  };

  const context = {
    document,
    window,
    navigator: {},
    fetch: fetchImpl,
    AbortController,
    Intl,
    performance: { now: () => 0 },
    requestAnimationFrame: (cb) => cb(1000),
    setTimeout,
    clearTimeout,
    console,
    encodeURIComponent,
  };

  vm.runInNewContext(appJsCode, context);
  assert.ok(domReadyCb, 'DOMContentLoaded listener harus terdaftar');
  return { elements, start: () => domReadyCb() };
}

async function flushMicrotasks() {
  await new Promise(r => setTimeout(r, 15));
}

// 1. Initial load: sukses tanpa auto-scroll & label SKOR PERINGKAT
{
  const { elements, start } = setupHarness(async () => ({
    ok: true,
    status: 200,
    async json() {
      return {
        query: 'laptop gaming murah',
        expanded_query: 'gaming',
        constraints: 'RAM >= 8GB',
        constraints_detail: [{ key: 'ram_min', label: 'RAM >= 8GB (asumsi sistem: gaming)', source: 'system_assumption', kind: 'hard' }],
        matched_phrases: ['gaming'],
        relaxed: false,
        count: 1,
        results: [{
          rank: 1, id: '10', brand: 'Acer', name: 'Nitro 5', category: 'Gaming',
          display: '15.6 inch', cpu: 'i5', ram: '8GB', storage: '512GB SSD',
          gpu: 'GTX 1050', os: 'Win 10', weight: '2.4kg', price_idr: 11000000, score: 0.6,
          match_reasons: ['RAM 8GB memenuhi >= 8GB'], variants: []
        }]
      };
    }
  }));
  start();
  await flushMicrotasks();
  assert.equal(elements.get('hasil')._scrolled, undefined, 'Initial load tidak boleh auto-scroll');
  assert.equal(elements.get('cards-container').children.length, 1);
  const cardHtml = elements.get('cards-container').children[0].innerHTML;
  assert.ok(cardHtml.includes('SKOR PERINGKAT:'));
  assert.ok(!cardHtml.includes('SKOR TF-IDF:'));
  assert.ok(!cardHtml.includes('Relevansi:'));
}

// 2. Nol hasil -> empty-state
{
  const { elements, start } = setupHarness(async () => ({
    ok: true,
    status: 200,
    async json() {
      return { query: 'gaming maksimal 5 juta', expanded_query: 'gaming', constraints: 'harga <= Rp5.000.000', matched_phrases: ['gaming'], relaxed: false, count: 0, results: [] };
    }
  }));
  start();
  await flushMicrotasks();
  assert.equal(elements.get('empty-state').style.display, 'flex');
  assert.equal(elements.get('error-state').style.display, 'none');
  assert.equal(elements.get('cards-container').children.length, 0);
}

// 3. Kegagalan API -> error-state + tombol Coba lagi (tanpa mock data)
{
  let attempt = 0;
  const { elements, start } = setupHarness(async () => {
    attempt += 1;
    if (attempt === 1) throw new Error('Network down');
    return {
      ok: true,
      status: 200,
      async json() {
        return { query: 'laptop gaming murah', expanded_query: 'gaming', constraints: '-', matched_phrases: [], relaxed: false, count: 1, results: [{ rank: 1, id: '99', brand: 'Lenovo', name: 'IdeaPad', category: 'Notebook', display: '14 inch', cpu: 'i5', ram: '8GB', storage: '256GB SSD', gpu: 'Intel', os: 'Win 10', weight: '1.5kg', price_idr: 8000000, score: 0.5 }] };
      }
    };
  });
  start();
  await flushMicrotasks();
  assert.equal(elements.get('error-state').style.display, 'flex');
  assert.equal(elements.get('cards-container').children.length, 0, 'Error tidak boleh menampilkan mock data');

  // Klik tombol Coba lagi
  elements.get('btn-retry-search').listeners.click[0]();
  await flushMicrotasks();
  assert.equal(elements.get('error-state').style.display, 'none');
  assert.equal(elements.get('cards-container').children.length, 1);
}

// 4. Out-of-order responses: Query A lambat, Query B cepat -> hasil akhir harus milik B, tanpa error dari A
{
  let resolveA;
  let call = 0;
  const { elements, start } = setupHarness((url, opts) => {
    call += 1;
    if (call === 1) {
      return new Promise((resolve, reject) => {
        resolveA = resolve;
        opts.signal.addEventListener('abort', () => {
          const err = new Error('Aborted');
          err.name = 'AbortError';
          reject(err);
        });
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      async json() {
        return {
          query: 'thinkpad', expanded_query: 'thinkpad', constraints: 'seri thinkpad',
          matched_phrases: [], relaxed: false, count: 1,
          results: [{ rank: 1, id: '200', brand: 'Lenovo', name: 'ThinkPad T470', category: 'Notebook', display: '14 inch', cpu: 'i5', ram: '16GB', storage: '512GB SSD', gpu: 'Intel', os: 'Win 10', weight: '1.6kg', price_idr: 15000000, score: 0.9 }]
        };
      }
    });
  });

  start();
  // Segera kirim query B sebelum A selesai
  elements.get('search-input').value = 'thinkpad';
  elements.get('search-form').listeners.submit[0]({ preventDefault() {} });
  await flushMicrotasks();

  assert.equal(elements.get('summary-query').textContent, 'thinkpad');
  assert.equal(elements.get('error-state').style.display, 'none');
  assert.equal(elements.get('cards-container').children.length, 1);
  assert.ok(elements.get('cards-container').children[0].innerHTML.includes('ThinkPad T470'));
}

// 5. total_candidates & catalog_size sinkronisasi + tombol CTA + toggle varian accordion
{
  const requestedUrls = [];
  const { elements, start } = setupHarness(async (url) => {
    requestedUrls.push(url);
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          query: 'laptop gaming murah',
          expanded_query: 'gaming',
          constraints: 'RAM >= 8GB',
          matched_phrases: ['gaming'],
          relaxed: false,
          count: 1,
          total_candidates: 142,
          catalog_size: 1275,
          results: [{
            rank: 1, id: '10', brand: 'Acer', name: 'Nitro 5', category: 'Gaming',
            display: '15.6 inch', cpu: 'i5', ram: '8GB', storage: '512GB SSD',
            gpu: 'GTX 1050', os: 'Win 10', weight: '2.4kg', price_idr: 11000000, score: 0.6,
            match_reasons: ['RAM 8GB memenuhi >= 8GB'],
            variants: [
              { cpu: 'i7', ram: '16GB', storage: '512GB SSD', gpu: 'GTX 1050', price_idr: 13000000 },
              { cpu: 'i7', ram: '16GB', storage: '1TB SSD', gpu: 'GTX 1060', price_idr: 15000000 }
            ]
          }]
        };
      }
    };
  });

  start();
  await flushMicrotasks();

  assert.equal(elements.get('result-counter').textContent, '000000000142');
  assert.equal(elements.get('screen-doc-count').textContent, '1.275 DOCS ONLINE');
  assert.equal(elements.get('footer-dataset-meta').textContent, 'DATASET: 1.275 LAPTOP');

  const card = elements.get('cards-container').children[0];
  const btnToggle = card.querySelector('.btn-toggle-detail');
  btnToggle.listeners.click[0]({ stopPropagation() {} });
  assert.equal(btnToggle.textContent, 'Tutup Detail ▲');
  btnToggle.listeners.click[0]({ stopPropagation() {} });
  assert.equal(btnToggle.textContent, 'Detail Lengkap ▼ (+2 varian)');

  elements.get('search-input').value = 'asus rog';
  elements.get('btn-cta-search').listeners.click[0]();
  await flushMicrotasks();
  assert.ok(requestedUrls.some(u => u.includes('q=asus%20rog')));
}

// 6. Kartu dengan >5 varian (contoh 9 varian MacBook Pro) bisa membuka semua varian tanpa men-tutup accordion
{
  const nineVariants = Array.from({ length: 9 }, (_, i) => ({
    id: String(100 + i),
    cpu: `Intel Core i7-${i}`,
    ram: '16GB',
    storage: '512GB SSD',
    gpu: 'Intel Iris',
    price_idr: 25000000 + (i * 500000),
  }));

  const { elements, start } = setupHarness(async () => ({
    ok: true,
    status: 200,
    async json() {
      return {
        query: 'laptop macbook',
        expanded_query: 'macbook',
        constraints: 'seri macbook',
        matched_phrases: ['macbook'],
        relaxed: false,
        count: 1,
        total_candidates: 3,
        catalog_size: 1275,
        results: [{
          rank: 1, id: '1', brand: 'Apple', name: 'MacBook Pro', category: 'Ultrabook',
          display: '15.4 inch', cpu: 'Intel Core i7', ram: '16GB', storage: '512GB SSD',
          gpu: 'Radeon Pro', os: 'macOS', weight: '1.83kg', price_idr: 30000000, score: 0.9,
          match_reasons: [],
          variants: nineVariants
        }]
      };
    }
  }));

  start();
  await flushMicrotasks();

  const card = elements.get('cards-container').children[0];
  assert.equal((card.innerHTML.match(/class="variant-item"/g) || []).length, 9);
  assert.ok(card.innerHTML.includes('menampilkan 5 dari 9'));
  assert.ok(card.innerHTML.includes('Tampilkan semua 9 varian (+4 lainnya)'));

  const btnToggleVariants = card.querySelector('.btn-toggle-variants');
  const extraVariantsEl = card.querySelector('.variants-extra');
  const variantsTitleEl = card.querySelector('.variants-title');

  let stopped = false;
  btnToggleVariants.listeners.click[0]({ stopPropagation() { stopped = true; } });
  assert.equal(stopped, true);
  assert.equal(extraVariantsEl.classList.contains('expanded'), true);
  assert.equal(btnToggleVariants.textContent, 'Tampilkan lebih sedikit (5)');
  assert.equal(variantsTitleEl.textContent, 'Varian konfigurasi lain (menampilkan semua 9):');

  btnToggleVariants.listeners.click[0]({ stopPropagation() {} });
  assert.equal(extraVariantsEl.classList.contains('expanded'), false);
  assert.equal(btnToggleVariants.textContent, 'Tampilkan semua 9 varian (+4 lainnya)');
  assert.equal(variantsTitleEl.textContent, 'Varian konfigurasi lain (menampilkan 5 dari 9):');
}

console.log('ALL FRONTEND JS TESTS PASSED');
