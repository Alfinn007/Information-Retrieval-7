/**
 * LAPTOPEX - Client-Side App Logic (Interactive & Responsive)
 * Sistem Rekomendasi Laptop (IR-7: TF-IDF + Query Expansion + Constraints)
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  const linkLihatHasil = document.getElementById('link-lihat-hasil');
  const cardsContainer = document.getElementById('cards-container');
  const loadingState = document.getElementById('loading-state');
  const emptyState = document.getElementById('empty-state');
  const errorState = document.getElementById('error-state');
  const errorStateMessage = document.getElementById('error-state-message');
  const btnRetrySearch = document.getElementById('btn-retry-search');
  
  const summaryQuery = document.getElementById('summary-query');
  const containerConstraints = document.getElementById('container-constraints');
  const containerMatched = document.getElementById('container-matched');
  const expandedQueryText = document.getElementById('expanded-query-text');
  const priceNoteText = document.getElementById('price-note-text');
  const relaxedBanner = document.getElementById('relaxed-banner');
  const resultCounter = document.getElementById('result-counter');
  
  const stickerBrand = document.getElementById('sticker-brand');
  const stickerDate = document.getElementById('sticker-date');

  // Mobile Floating Search Button
  const mobileFloatingBtn = document.getElementById('mobile-floating-btn');

  // Deck Sort Buttons
  const btnSortRel = document.getElementById('btn-sort-rel');
  const btnSortPriceAsc = document.getElementById('btn-sort-price-asc');
  const btnSortPriceDesc = document.getElementById('btn-sort-price-desc');
  const btnScrollTop = document.getElementById('btn-scroll-top');
  
  // Quick Query Chips
  const queryChips = document.querySelectorAll('.query-chip');

  // 3D Laptop Chassis & Stage
  const laptopChassis = document.getElementById('laptop-chassis');
  const heroStage = document.getElementById('hero-stage');

  // Audio Toggle Button & Toast
  const btnSoundToggle = document.getElementById('btn-sound-toggle');
  const retroToast = document.getElementById('retro-toast');

  // State
  let currentResults = [];
  let currentSort = 'relevance';
  let soundEnabled = true;
  let activeController = null;
  let latestRequestId = 0;
  let lastSubmittedQuery = '';

  // Format Tanggal Hari Ini untuk Stiker Kaset
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  if (stickerDate) {
    stickerDate.textContent = `${yyyy}.${mm}.${dd}`;
  }

  // Currency Formatter Rupiah
  const rupiahFormatter = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0
  });

  // =========================================================================
  // 1. RETRO WEB AUDIO API (SYNTHESIZED SOUND FX - TANPA FILE AUDIO EKSTERNAL)
  // =========================================================================
  let audioCtx = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  // Efek klik mekanik kaset
  function playClickSound() {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioCtx) return;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(140, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(30, audioCtx.currentTime + 0.05);

      gain.gain.setValueAtTime(0.22, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.05);

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.06);
    } catch (e) {
      // Audio fallback jika diblokir autoplay
    }
  }

  // Efek tape rewinding (saat mulai search)
  function playTapeRewindSound() {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioCtx) return;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(280, audioCtx.currentTime);
      osc.frequency.linearRampToValueAtTime(820, audioCtx.currentTime + 0.25);

      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.28);

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {}
  }

  // Efek sukses hasil dimuat (beep retro)
  function playSuccessBeep() {
    if (!soundEnabled) return;
    try {
      initAudio();
      if (!audioCtx) return;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.08); // A5

      gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.18);

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.2);
    } catch (e) {}
  }

  // Sound Toggle Listener
  if (btnSoundToggle) {
    btnSoundToggle.addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      if (soundEnabled) {
        btnSoundToggle.classList.remove('muted');
        btnSoundToggle.innerHTML = '<span class="sound-icon">🔊</span><span class="sound-text">AUDIO: ON</span>';
        playClickSound();
      } else {
        btnSoundToggle.classList.add('muted');
        btnSoundToggle.innerHTML = '<span class="sound-icon">🔇</span><span class="sound-text">AUDIO: OFF</span>';
      }
    });
  }


  // =========================================================================
  // 2. PARALLAX & TOUCH 3D TILT INTERAKTIF (DESKTOP MOUSE & MOBILE TOUCH)
  // =========================================================================
  function triggerHaptic(duration = 25) {
    if (navigator && navigator.vibrate) {
      try { navigator.vibrate(duration); } catch (e) {}
    }
  }

  // Interaktivitas Tap Layar Terminal Laptop
  const screenContainer = document.getElementById('screen-container');
  if (screenContainer && searchInput) {
    screenContainer.addEventListener('click', (e) => {
      if (e.target !== searchInput) {
        searchInput.focus();
        triggerHaptic(15);
        playClickSound();
        screenContainer.style.boxShadow = 'inset 0 0 24px rgba(134, 209, 42, 0.5), 0 0 10px rgba(134, 209, 42, 0.4)';
        setTimeout(() => {
          screenContainer.style.boxShadow = '';
        }, 800);
      }
    });
  }

  if (laptopChassis) {
    // A. Desktop Mousemove Tilt (layar lebar > 680px)
    if (window.matchMedia('(min-width: 681px)').matches && heroStage) {
      heroStage.addEventListener('mousemove', (e) => {
        const rect = heroStage.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        
        const tiltX = 11 - (y * 10);
        const tiltY = x * 12;
        laptopChassis.style.transform = `rotate(${tiltX}deg) rotateY(${tiltY}deg) translateY(${y * -5}px)`;
      });

      heroStage.addEventListener('mouseleave', () => {
        laptopChassis.style.transform = '';
      });
    }

    // B. Mobile Touch Drag Tilt (layar <= 680px)
    if (window.matchMedia('(max-width: 680px)').matches) {
      let touchStartX = 0;
      let touchStartY = 0;
      let isTouching = false;

      laptopChassis.addEventListener('touchstart', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
        isTouching = true;
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        laptopChassis.style.transition = 'none';
      }, { passive: true });

      laptopChassis.addEventListener('touchmove', (e) => {
        if (!isTouching) return;
        const currentX = e.touches[0].clientX;
        const currentY = e.touches[0].clientY;
        const deltaX = currentX - touchStartX;
        const deltaY = currentY - touchStartY;

        // Batasi sudut kemiringan agar pas di layar HP dan tidak pernah terpotong (max 5 deg)
        const rotY = Math.max(Math.min(deltaX * 0.08, 5), -5);
        const rotX = Math.max(Math.min(-deltaY * 0.08, 4), -4);

        laptopChassis.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.01)`;
      }, { passive: true });

      const resetTouchTilt = () => {
        if (!isTouching) return;
        isTouching = false;
        laptopChassis.style.transition = 'transform 0.4s cubic-bezier(0.18, 0.9, 0.3, 1)';
        laptopChassis.style.transform = 'none';
      };

      laptopChassis.addEventListener('touchend', resetTouchTilt);
      laptopChassis.addEventListener('touchcancel', resetTouchTilt);

      // Gyroscope halus tanpa memotong batas layar HP
      if (window.DeviceOrientationEvent) {
        window.addEventListener('deviceorientation', (e) => {
          if (!isTouching && e.gamma !== null) {
            const gamma = Math.max(Math.min(e.gamma, 15), -15);
            const subtleTilt = (gamma / 15) * 2.5; // Max 2.5 deg
            laptopChassis.style.transform = `rotate(${subtleTilt}deg)`;
          }
        }, { passive: true });
      }
    }
  }


  // =========================================================================
  // 3. TOAST NOTIFIKASI
  // =========================================================================
  function showToast(msg) {
    if (!retroToast) return;
    const msgEl = retroToast.querySelector('.toast-msg');
    if (msgEl) msgEl.textContent = msg;
    retroToast.classList.add('show');
    playClickSound();
    triggerHaptic(30);
    setTimeout(() => {
      retroToast.classList.remove('show');
    }, 2400);
  }


  // =========================================================================
  // 4. EKSEKUSI PENCARIAN (SEARCH LOGIC)
  // =========================================================================
  async function performSearch(query, options = {}) {
    const { scrollToResults = true } = options;
    const trimmed = (query || '').trim();
    if (!trimmed) {
      searchInput.focus();
      return;
    }

    if (activeController) {
      activeController.abort();
    }
    const controller = new AbortController();
    activeController = controller;
    const requestId = ++latestRequestId;
    lastSubmittedQuery = trimmed;

    playTapeRewindSound();

    // Tampilkan Loading State
    cardsContainer.innerHTML = '';
    emptyState.style.display = 'none';
    if (errorState) errorState.style.display = 'none';
    loadingState.style.display = 'flex';
    summaryQuery.textContent = trimmed;
    searchInput.value = trimmed;

    if (scrollToResults) {
      const resultsSection = document.getElementById('hasil');
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(trimmed)}&top=30`, {
        signal: controller.signal
      });

      if (requestId !== latestRequestId) return;

      let data = null;
      try {
        data = await response.json();
      } catch (parseErr) {
        throw new Error(`Respons server tidak valid (HTTP ${response.status}).`);
      }

      if (!response.ok) {
        const msg = (data && data.error) ? data.error : `HTTP Error: ${response.status}`;
        throw new Error(msg);
      }

      if (!data || !Array.isArray(data.results)) {
        throw new Error('Format data hasil pencarian tidak valid.');
      }

      if (requestId !== latestRequestId) return;
      handleSearchResults(data);
    } catch (err) {
      if (err && err.name === 'AbortError') return;
      if (requestId !== latestRequestId) return;
      handleSearchError(err && err.message ? err.message : 'Gagal terhubung ke server pencarian.');
    }
  }

  function handleSearchError(errorMessage) {
    loadingState.style.display = 'none';
    emptyState.style.display = 'none';
    if (relaxedBanner) relaxedBanner.style.display = 'none';
    cardsContainer.innerHTML = '';
    currentResults = [];
    animateCounter(0);

    if (stickerBrand) stickerBrand.textContent = 'LAPTOPEX';
    containerConstraints.innerHTML = '<span class="chip-black">-</span>';
    containerMatched.innerHTML = '<span class="chip-outline">-</span>';
    expandedQueryText.textContent = '-';

    if (errorStateMessage) errorStateMessage.textContent = errorMessage;
    if (errorState) errorState.style.display = 'flex';
  }

  function handleSearchResults(data) {
    loadingState.style.display = 'none';
    if (errorState) errorState.style.display = 'none';
    playSuccessBeep();

    currentResults = data.results || [];
    currentSort = 'relevance';
    updateActiveSortButton();

    // 1. Update Counter Odometer
    animateCounter(currentResults.length);

    // 2. Update Informasi Metadata & Chips
    renderMetadata(data);

    // 3. Update Stiker di Palmrest Laptop
    if (stickerBrand) {
      if (currentResults.length > 0) {
        stickerBrand.textContent = currentResults[0].brand.toUpperCase();
      } else {
        stickerBrand.textContent = 'LAPTOPEX';
      }
    }

    // 4. Render Kartu
    if (currentResults.length === 0) {
      emptyState.style.display = 'flex';
      cardsContainer.innerHTML = '';
    } else {
      emptyState.style.display = 'none';
      renderCards(currentResults);
    }
  }

  /**
   * Render Filter & Expansion Chips
   */
  function renderMetadata(data) {
    // Constraints terstruktur jika tersedia
    containerConstraints.innerHTML = '';
    const detailList = Array.isArray(data.constraints_detail) ? data.constraints_detail : null;
    if (detailList && detailList.length > 0) {
      detailList.forEach(item => {
        const chip = document.createElement('span');
        if (item.source === 'system_assumption') {
          chip.className = 'chip-assumption';
        } else if (item.kind === 'preference') {
          chip.className = 'chip-preference';
        } else {
          chip.className = 'chip-black';
        }
        chip.textContent = item.label;
        containerConstraints.appendChild(chip);
      });
    } else {
      const rawConstraints = data.constraints || 'Tidak ada filter khusus';
      const parts = rawConstraints.split(',').map(s => s.trim()).filter(Boolean);
      parts.forEach(part => {
        const chip = document.createElement('span');
        chip.className = 'chip-black';
        chip.textContent = part;
        containerConstraints.appendChild(chip);
      });
    }

    // Matched Expansion Phrases
    containerMatched.innerHTML = '';
    const matched = data.matched_phrases || [];
    if (matched.length > 0) {
      matched.forEach(phrase => {
        const chip = document.createElement('span');
        chip.className = 'chip-outline';
        chip.textContent = phrase;
        containerMatched.appendChild(chip);
      });
    } else {
      const chip = document.createElement('span');
      chip.className = 'chip-outline';
      chip.textContent = 'Tidak ada istilah kamus yang cocok';
      containerMatched.appendChild(chip);
    }

    // Expanded Query Text
    expandedQueryText.textContent = data.expanded_query || '-';

    if (priceNoteText && data.price_note) {
      priceNoteText.textContent = data.price_note;
    }

    // Relaxed Warning Banner
    if (relaxedBanner) {
      relaxedBanner.style.display = data.relaxed ? 'flex' : 'none';
    }
  }

  /**
   * Render Kartu Hasil Laptop (J-Card Style)
   */
  function renderCards(laptops) {
    cardsContainer.innerHTML = '';

    laptops.forEach((item, index) => {
      const card = document.createElement('article');
      card.className = 'laptop-card';
      card.style.animationDelay = `${Math.min(index * 35, 600)}ms`;

      // Kalkulasi bar VU meter equalizer (14 segmen)
      const maxSegments = 14;
      const scoreNormalized = Math.min(Math.max(item.score, 0), 1);
      const activeSegments = Math.round(scoreNormalized * maxSegments);

      let eqSegmentsHtml = '';
      for (let s = 0; s < maxSegments; s++) {
        const isActive = s < activeSegments ? 'active' : '';
        eqSegmentsHtml += `<span class="eq-seg ${isActive}"></span>`;
      }

      // Format Harga IDR
      const formattedPrice = rupiahFormatter.format(item.price_idr).replace(/\s/g, '');
      const reasons = Array.isArray(item.match_reasons) ? item.match_reasons : [];
      const reasonsHtml = reasons.length > 0
        ? `<div class="match-reasons-row">${reasons.map(r => `<span class="reason-pill">${escapeHtml(r)}</span>`).join('')}</div>`
        : '';

      const variants = Array.isArray(item.variants) ? item.variants : [];
      const variantsHtml = variants.length > 0
        ? `<div class="variants-section">
             <div class="variants-title">Varian konfigurasi lain (${variants.length}):</div>
             <div class="variants-list">
               ${variants.slice(0, 5).map(v => {
                 const vPrice = rupiahFormatter.format(v.price_idr).replace(/\s/g, '');
                 return `<div class="variant-item"><strong>${vPrice}</strong> · ${escapeHtml(v.cpu)} · ${escapeHtml(v.ram)} · ${escapeHtml(v.storage)} · ${escapeHtml(v.gpu)}</div>`;
               }).join('')}
             </div>
           </div>`
        : '';

      card.innerHTML = `
        <!-- Rank Raksasa -->
        <div class="card-rank-box">
          <span class="rank-prefix">RANK</span>
          <span class="rank-number">${item.rank || (index + 1)}</span>
        </div>

        <!-- Detail Tengah -->
        <div class="card-body">
          <div class="card-title-row">
            <span class="card-brand">${escapeHtml(item.brand)}</span>
            <h3 class="card-name">${escapeHtml(item.name)}</h3>
            <span class="card-category-badge">${escapeHtml(item.category || 'Notebook')}</span>
          </div>

          <div class="specs-grid">
            <div class="spec-item">
              <span class="spec-k">CPU:</span>
              <span class="spec-v" title="${escapeHtml(item.cpu)}">${escapeHtml(item.cpu)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-k">RAM:</span>
              <span class="spec-v">${escapeHtml(item.ram)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-k">STORAGE:</span>
              <span class="spec-v" title="${escapeHtml(item.storage)}">${escapeHtml(item.storage)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-k">GPU:</span>
              <span class="spec-v" title="${escapeHtml(item.gpu)}">${escapeHtml(item.gpu)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-k">LAYAR:</span>
              <span class="spec-v" title="${escapeHtml(item.display)}">${escapeHtml(item.display)}</span>
            </div>
            <div class="spec-item">
              <span class="spec-k">OS/BERAT:</span>
              <span class="spec-v">${escapeHtml(item.os)} · ${escapeHtml(item.weight)}</span>
            </div>
          </div>

          <div class="card-actions-row">
            <button type="button" class="btn-card-action btn-copy-spec" title="Salin Ringkasan Spesifikasi">
              📋 Salin Spek
            </button>
            <button type="button" class="btn-card-action btn-toggle-detail" title="Buka Detail">
              Detail Lengkap ▼${variants.length > 0 ? ` (+${variants.length} varian)` : ''}
            </button>
          </div>
          ${reasonsHtml}
        </div>

        <!-- Kolom Kanan: Harga & Meter -->
        <div class="card-right-box">
          <div class="price-tag">${formattedPrice}</div>
          <div class="meter-wrapper">
            <div class="meter-header">
              <span>SKOR PERINGKAT:</span>
              <span class="meter-score-text">${(item.score || 0).toFixed(4)}</span>
            </div>
            <div class="equalizer-bar" title="Skor peringkat: ${(item.score || 0).toFixed(4)}">
              ${eqSegmentsHtml}
            </div>
          </div>
        </div>

        <!-- Accordion Info Lengkap -->
        <div class="card-accordion">
          <div class="accordion-details-list">
            <div><strong>ID Database:</strong> ${escapeHtml(item.id || '-')}</div>
            <div><strong>Sistem Operasi:</strong> ${escapeHtml(item.os || '-')}</div>
            <div><strong>Bobot / Berat:</strong> ${escapeHtml(item.weight || '-')}</div>
            <div><strong>Resolusi Layar:</strong> ${escapeHtml(item.display || '-')}</div>
            <div><strong>Spesifikasi Prosesor:</strong> ${escapeHtml(item.cpu || '-')}</div>
            <div><strong>Kartu Grafis:</strong> ${escapeHtml(item.gpu || '-')}</div>
          </div>
          ${variantsHtml}
        </div>
      `;

      // Event Copy Spec
      const btnCopy = card.querySelector('.btn-copy-spec');
      if (btnCopy) {
        btnCopy.addEventListener('click', (e) => {
          e.stopPropagation();
          const specText = `[LAPTOPEX REKOMENDASI] ${item.brand} ${item.name} | CPU: ${item.cpu} | RAM: ${item.ram} | Storage: ${item.storage} | GPU: ${item.gpu} | Harga: ${formattedPrice}`;
          if (navigator.clipboard) {
            navigator.clipboard.writeText(specText).then(() => {
              showToast(`Spesifikasi ${item.name} tersalin!`);
            });
          } else {
            showToast(`Spesifikasi ${item.name} siap dibagikan!`);
          }
        });
      }

      // Event Accordion Toggle
      const btnToggle = card.querySelector('.btn-toggle-detail');
      const accordion = card.querySelector('.card-accordion');
      
      function toggleAccordion(e) {
        e.stopPropagation();
        playClickSound();
        triggerHaptic(15);
        const isOpen = accordion.classList.toggle('open');
        btnToggle.textContent = isOpen ? 'Tutup Detail ▲' : 'Detail Lengkap ▼';
      }

      if (btnToggle) btnToggle.addEventListener('click', toggleAccordion);
      card.addEventListener('click', toggleAccordion);

      cardsContainer.appendChild(card);
    });
  }

  /**
   * Sort Handler Sisi Client
   */
  function sortResults(type) {
    if (!currentResults || currentResults.length <= 1) return;
    playClickSound();
    currentSort = type;
    updateActiveSortButton();

    const sorted = [...currentResults];
    if (type === 'relevance') {
      sorted.sort((a, b) => (b.score || 0) - (a.score || 0));
    } else if (type === 'price-asc') {
      sorted.sort((a, b) => a.price_idr - b.price_idr);
    } else if (type === 'price-desc') {
      sorted.sort((a, b) => b.price_idr - a.price_idr);
    }

    sorted.forEach((item, idx) => {
      item.rank = idx + 1;
    });

    renderCards(sorted);
  }

  function updateActiveSortButton() {
    [btnSortRel, btnSortPriceAsc, btnSortPriceDesc].forEach(btn => {
      if (btn) btn.classList.remove('active');
    });

    if (currentSort === 'relevance' && btnSortRel) btnSortRel.classList.add('active');
    if (currentSort === 'price-asc' && btnSortPriceAsc) btnSortPriceAsc.classList.add('active');
    if (currentSort === 'price-desc' && btnSortPriceDesc) btnSortPriceDesc.classList.add('active');
  }

  /**
   * Animasi Angka Counter Odometer
   */
  function animateCounter(targetNumber) {
    if (!resultCounter) return;
    const duration = 500;
    const startTime = performance.now();
    const startNum = 0;

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const current = Math.floor(progress * (targetNumber - startNum) + startNum);
      resultCounter.textContent = String(current).padStart(12, '0');

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        resultCounter.textContent = String(targetNumber).padStart(12, '0');
      }
    }

    requestAnimationFrame(step);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Event Listeners
   */
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      performSearch(searchInput.value);
    });
  }

  // Floating Search Button (Mobile)
  if (mobileFloatingBtn) {
    mobileFloatingBtn.addEventListener('click', () => {
      playClickSound();
      const heroSection = document.getElementById('hero');
      if (heroSection) heroSection.scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => {
        searchInput.focus();
      }, 400);
    });

    // Munculkan hanya saat di-scroll ke bawah melewati hero
    window.addEventListener('scroll', () => {
      if (window.scrollY > 400) {
        mobileFloatingBtn.style.display = 'flex';
      } else {
        mobileFloatingBtn.style.display = 'none';
      }
    }, { passive: true });
  }

  // Quick Chips Click
  queryChips.forEach(chip => {
    chip.addEventListener('click', () => {
      playClickSound();
      triggerHaptic(20);
      const q = chip.getAttribute('data-query');
      searchInput.value = q;
      performSearch(q);
    });
  });

  // Sort Buttons Click
  if (btnSortRel) btnSortRel.addEventListener('click', () => sortResults('relevance'));
  if (btnSortPriceAsc) btnSortPriceAsc.addEventListener('click', () => sortResults('price-asc'));
  if (btnSortPriceDesc) btnSortPriceDesc.addEventListener('click', () => sortResults('price-desc'));

  // Scroll to Top
  if (btnScrollTop) {
    btnScrollTop.addEventListener('click', () => {
      playClickSound();
      const heroSection = document.getElementById('hero');
      if (heroSection) heroSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  if (linkLihatHasil) {
    linkLihatHasil.addEventListener('click', (e) => {
      e.preventDefault();
      playClickSound();
      const resultsSection = document.getElementById('hasil');
      if (resultsSection) resultsSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  if (btnRetrySearch) {
    btnRetrySearch.addEventListener('click', () => {
      playClickSound();
      if (lastSubmittedQuery) {
        performSearch(lastSubmittedQuery, { scrollToResults: true });
      }
    });
  }

  // Pencarian awal default tanpa menggeser layar menjauhi kolom pencarian
  performSearch('laptop gaming murah', { scrollToResults: false });
});
