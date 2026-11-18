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
    addEventListener(ev, fn) {
      this.listeners[ev] = this.listeners[ev] || [];
      this.listeners[ev].push(fn);
    },
    appendChild(child) { this.children.push(child); },
    querySelector() { return null; },
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
    'btn-sound-toggle', 'retro-toast', 'screen-container', 'hasil', 'hero'
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

console.log('ALL FRONTEND JS TESTS PASSED');
