/* ═══════════════════════════════════════════════════════
   Product Gallery — Gen-Z Editorial UI
   Light theme, serif headings, image carousels, 
   mosaic collections, AI brain card
   ═══════════════════════════════════════════════════════ */

const API = 'http://localhost:8000/v1';
const BASE = 'http://localhost:8000';

// Safe lucide fallback: CDN runs before this script; guard against CDN failure
var lucide = window.lucide || { createIcons: function() {} };

// ── State ──────────────────────────────────────────────
const state = {
  token: localStorage.getItem('pg_token'),
  user: null,
  products: [],
  collections: [],
  categories: [],
  view: 'home',
  galleryFilter: 'All',
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// Card background colors for products without images
const CARD_BG_CLASSES = ['card-bg-1','card-bg-2','card-bg-3','card-bg-4','card-bg-5','card-bg-6','card-bg-7','card-bg-8'];
function getCardBg(id) {
  let hash = 0;
  for (let i = 0; i < (id || '').length; i++) hash = ((hash << 5) - hash) + id.charCodeAt(i);
  return CARD_BG_CLASSES[Math.abs(hash) % CARD_BG_CLASSES.length];
}

// Source labels
const SOURCE_LABELS = {
  web: 'WEB', manual: 'MANUAL', extension: 'EXTENSION',
  instagram: 'INSTAGRAM', twitter: 'TWITTER', reddit: 'REDDIT',
  pinterest: 'PINTEREST', youtube: 'YOUTUBE',
};

// ── Boot ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  bindGlobalEvents();
  if (state.token) {
    await fetchProfile();
    try {
      const pData = await api('/products?page_size=50');
      state.products = pData.items || [];
      const cData = await api('/collections');
      state.collections = cData.items || [];
    } catch {}
  }
  renderSidebarUser();
  navigate('home');
  renderLandingPage();
  lucide.createIcons();

  // Keyboard shortcut: Escape to close modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      $$('.modal-backdrop:not(.hidden)').forEach(m => m.classList.add('hidden'));
    }
  });
});

// ── Global Events ──────────────────────────────────────
function bindGlobalEvents() {
  // Nav links
  $$('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      navigate(link.dataset.view);
    });
  });

  // Mobile menu
  const mobileBtn = $('#btn-mobile-menu');
  if (mobileBtn) {
    mobileBtn.addEventListener('click', () => {
      $('#sidebar').classList.toggle('mobile-open');
    });
  }

  // FAB
  $('#fab-add').addEventListener('click', async () => {
    if (!state.token) {
      openModal('modal-auth');
    } else {
      // Pre-load collections and categories so the picker is up to date
      await refreshCollectionsForPicker();
      await refreshCategoriesForPicker();
      openModal('modal-product');
    }
  });

  // Modal close buttons
  $$('.modal-close-btn').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.close));
  });

  // Close modals on backdrop click
  $$('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal(backdrop.id);
    });
  });

  // Auth tabs
  $$('#auth-tabs .tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('#auth-tabs .tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const isLogin = tab.dataset.tab === 'login';
      $('#form-login').classList.toggle('hidden', !isLogin);
      $('#form-register').classList.toggle('hidden', isLogin);
      $('.modal-header h2').textContent = isLogin ? 'Welcome back' : 'Create an account';
      $('.modal-desc').textContent = isLogin
        ? 'Sign in to your Product Gallery account'
        : 'Start saving products from anywhere';
    });
  });

  // Form submissions
  $('#form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    await doLogin($('#login-email').value, $('#login-password').value);
  });

  $('#form-register').addEventListener('submit', async (e) => {
    e.preventDefault();
    await doRegister($('#reg-email').value, $('#reg-password').value, $('#reg-name').value || undefined);
  });

  $('#form-product').addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveProduct();
  });

  $('#form-collection').addEventListener('submit', async (e) => {
    e.preventDefault();
    await createCollection();
  });

  // Live metadata extraction on pasting a Product URL
  const prodUrlInput = $('#prod-url');
  if (prodUrlInput) {
    prodUrlInput.addEventListener('change', async (e) => {
      let urlVal = e.target.value.trim();
      if (urlVal) {
        if (!/^https?:\/\//i.test(urlVal)) {
          urlVal = 'https://' + urlVal;
          e.target.value = urlVal;
        }
        await handleUrlExtraction(urlVal);
      }
    });
  }

  // Live preview for custom image URL
  const prodImgUrlInput = $('#prod-image-url');
  if (prodImgUrlInput) {
    prodImgUrlInput.addEventListener('change', (e) => {
      const imgUrlVal = e.target.value.trim();
      if (imgUrlVal && /^https?:\/\//.test(imgUrlVal)) {
        const previewContainer = $('#prod-preview-container');
        const previewImg = $('#prod-preview-img');
        previewImg.src = imgUrlVal;
        previewContainer.classList.remove('hidden');
        previewImg.classList.remove('hidden');
      }
    });
  }

  // Live preview for local uploaded photo file
  const prodImgFileInput = $('#prod-image-file');
  if (prodImgFileInput) {
    prodImgFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const previewContainer = $('#prod-preview-container');
        const previewImg = $('#prod-preview-img');
        previewImg.src = URL.createObjectURL(file);
        previewContainer.classList.remove('hidden');
        previewImg.classList.remove('hidden');
      }
    });
  }

  // Full-screen Auth Page Tabs
  $$('#auth-page-tabs .tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('#auth-page-tabs .tab').forEach(t => {
        t.classList.remove('active');
        t.style.borderBottom = '2px solid transparent';
        t.style.color = 'var(--text-tertiary)';
        t.style.fontWeight = '500';
      });
      tab.classList.add('active');
      tab.style.borderBottom = '2px solid var(--text-primary)';
      tab.style.color = 'var(--text-primary)';
      tab.style.fontWeight = '600';
      
      const isLogin = tab.dataset.tab === 'login';
      $('#form-login-page').classList.toggle('hidden', !isLogin);
      $('#form-register-page').classList.toggle('hidden', isLogin);
      $('#auth-title').textContent = isLogin ? 'Welcome Back' : 'Create Account';
      $('#auth-desc').textContent = isLogin 
        ? 'Sign in to your Product Gallery account' 
        : 'Start saving products from anywhere';
    });
  });

  // Full-screen Auth Page Submissions
  $('#form-login-page').addEventListener('submit', async (e) => {
    e.preventDefault();
    await doLogin($('#login-page-email').value, $('#login-page-password').value);
  });

  $('#form-register-page').addEventListener('submit', async (e) => {
    e.preventDefault();
    await doRegister($('#reg-page-email').value, $('#reg-page-password').value, $('#reg-page-name').value || undefined);
  });

  // Back button on Auth Page
  const authBackBtn = $('#btn-auth-back');
  if (authBackBtn) {
    authBackBtn.addEventListener('click', () => {
      const authPage = $('#auth-page');
      const landingPage = $('#landing-page');
      if (authPage && landingPage) {
        authPage.style.opacity = '0';
        authPage.style.transform = 'scale(0.97)';
        setTimeout(() => {
          authPage.classList.add('hidden');
          landingPage.classList.remove('hidden');
          landingPage.style.opacity = '1';
          landingPage.style.transform = 'scale(1)';
        }, 300);
      }
    });
  }
}

// ── Navigation ─────────────────────────────────────────
function navigate(view, extra) {
  state.view = view;
  $$('.nav-link').forEach(l => l.classList.toggle('active', l.dataset.view === view));
  $('#sidebar').classList.remove('mobile-open');

  switch (view) {
    case 'home': renderHome(); break;
    case 'gallery': renderGallery(); break;
    case 'collections': renderCollections(); break;
    case 'collection': renderCollectionDetail(extra); break;
    case 'wishlist': renderGallery(true); break;
    case 'discover': renderDiscover(); break;
    case 'pricedrops': renderPriceDropsPage(); break;
    case 'health': renderHealth(); break;
    case 'settings': renderSettings(); break;
    default: renderHome();
  }
}

// ── Auth ───────────────────────────────────────────────
async function doLogin(email, password) {
  try {
    const res = await api('/auth/login', 'POST', { email, password });
    state.token = res.access_token;
    localStorage.setItem('pg_token', res.access_token);
    await fetchProfile();
    renderSidebarUser();
    closeModal('modal-auth');
    
    // Pre-fetch collections & products
    try {
      const pData = await api('/products?page_size=50');
      state.products = pData.items || [];
      const cData = await api('/collections');
      state.collections = cData.items || [];
    } catch {}

    const authPage = $('#auth-page');
    if (authPage) {
      authPage.style.opacity = '0';
      authPage.style.transform = 'scale(1.05)';
      setTimeout(() => authPage.classList.add('hidden'), 500);
    }
    sessionStorage.setItem('pg_entered', 'true');
    navigate('home');
    toast('Welcome back! ✨', 'success');
  } catch (e) {
    toast(e.message || 'Invalid credentials', 'error');
  }
}

async function doRegister(email, password, display_name) {
  try {
    const res = await api('/auth/register', 'POST', { email, password, display_name });
    state.token = res.access_token;
    localStorage.setItem('pg_token', res.access_token);
    await fetchProfile();
    renderSidebarUser();
    closeModal('modal-auth');
    
    // Pre-fetch collections & products
    try {
      const pData = await api('/products?page_size=50');
      state.products = pData.items || [];
      const cData = await api('/collections');
      state.collections = cData.items || [];
    } catch {}

    const authPage = $('#auth-page');
    if (authPage) {
      authPage.style.opacity = '0';
      authPage.style.transform = 'scale(1.05)';
      setTimeout(() => authPage.classList.add('hidden'), 500);
    }
    sessionStorage.setItem('pg_entered', 'true');
    navigate('home');
    toast('Account created! 🎉', 'success');
  } catch (e) {
    toast(e.message || 'Registration failed', 'error');
  }
}

async function fetchProfile() {
  try {
    state.user = await api('/auth/me');
  } catch {
    state.token = null;
    state.user = null;
    localStorage.removeItem('pg_token');
  }
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem('pg_token');
  sessionStorage.removeItem('pg_entered');
  renderSidebarUser();
  toast('Signed out', 'info');
  renderLandingPage();
}

function renderSidebarUser() {
  const el = $('#sidebar-user');
  if (state.user) {
    const name = state.user.display_name || state.user.email.split('@')[0];
    const initial = name.charAt(0).toUpperCase();
    el.innerHTML = `
      <div class="avatar avatar-purple">${esc(initial)}</div>
      <div class="sidebar-user-info">
        <div class="sidebar-user-name">${esc(name)}</div>
        <div class="sidebar-user-role">Your universe</div>
      </div>
      <div class="sidebar-user-actions">
        <button title="Sign out" onclick="logout()"><i data-lucide="log-out"></i></button>
      </div>
    `;
  } else {
    el.innerHTML = `
      <div class="avatar"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div>
      <div class="sidebar-user-info">
        <div class="sidebar-user-name">Guest</div>
        <div class="sidebar-user-role">Not signed in</div>
      </div>
      <div class="sidebar-user-actions">
        <button title="Sign in" onclick="openModal('modal-auth')"><i data-lucide="log-in"></i></button>
      </div>
    `;
  }
  lucide.createIcons();
}

// ═══ VIEWS ═════════════════════════════════════════════

// ── Home ───────────────────────────────────────────────
async function renderHome() {
  const c = $('#content');

  if (!state.token) {
    c.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon-wrap"><i data-lucide="shopping-bag"></i></div>
        <h3 class="empty-title">Welcome to Product Gallery</h3>
        <p class="empty-desc">Your personal product memory. Sign in to start saving products from anywhere on the internet.</p>
        <button class="btn btn-primary" onclick="openModal('modal-auth')"><i data-lucide="log-in"></i> Get Started</button>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  showShimmer(c);

  try {
    const [products, collections, categories] = await Promise.all([
      api('/products?page_size=50').catch(() => ({ items: [], total: 0 })),
      api('/collections').catch(() => ({ items: [], total: 0 })),
      api('/categories').catch(() => ({ categories: [] })),
    ]);

    state.products = products.items || [];
    state.collections = collections.items || [];
    state.categories = (categories.categories || categories || []);
    const recent = state.products.slice(0, 10);
    const userName = state.user ? (state.user.display_name || state.user.email.split('@')[0]) : 'there';

    // Find products with price drops (simulated from price_original vs price_current)
    const priceDrops = state.products.filter(p => p.price_original && p.price_current && p.price_original > p.price_current).slice(0, 6);

    // Find most saved category for AI card
    const brandCounts = {};
    state.products.forEach(p => {
      if (p.brand) brandCounts[p.brand] = (brandCounts[p.brand] || 0) + 1;
    });
    const topBrand = Object.entries(brandCounts).sort((a,b) => b[1] - a[1])[0];

    c.innerHTML = `
      <div class="content-inner">
        <!-- Recently Saved Section -->
        <div class="carousel-container">
          <div class="section-header">
            <div>
              <div class="section-label">FRESH FROM THE INTERNET</div>
              <div class="section-title">Recently Saved<span class="dot">.</span></div>
            </div>
            <a class="see-all" onclick="navigate('gallery')">See all →</a>
          </div>
          ${recent.length > 0 ? `
            <div class="carousel" id="carousel-recent">
              ${recent.map(p => recentProductCard(p)).join('')}
            </div>
          ` : `
            <div style="color:var(--text-tertiary);font-size:0.9rem;padding:20px 0;">
              No products saved yet. Tap the <strong style="color:var(--coral)">+</strong> button to save your first one!
            </div>
          `}
        </div>

        <!-- Collections + AI Brain -->
        <div class="home-two-col">
          <div>
            <div class="section-header">
              <div>
                <div class="section-label">LITTLE UNIVERSES</div>
                <div class="section-title">Your Collections<span class="dot">.</span></div>
              </div>
              <a class="see-all" onclick="navigate('collections')">See all →</a>
            </div>
            ${state.collections.length > 0 ? `
              <div class="collections-grid" style="margin-bottom:0;">
                ${state.collections.slice(0, 3).map(col => collectionMosaicCard(col)).join('')}
              </div>
            ` : `
              <div style="color:var(--text-tertiary);font-size:0.9rem;padding:20px 0;">
                Create your first collection to organize your finds!
              </div>
            `}
          </div>

          <!-- AI Card -->
          <div>
            <div class="section-label" style="margin-bottom:12px;">AI</div>
            <div class="ai-card">
              <div class="ai-card-sparkle">✨</div>
              ${topBrand ? `
                <div class="ai-card-text">
                  You've saved <strong>${topBrand[1]}</strong> <strong>${esc(topBrand[0])}</strong> products recently. Want to compare them?
                </div>
                <button class="ai-card-cta" onclick="navigate('gallery')">Compare <i data-lucide="arrow-right"></i></button>
              ` : `
                <div class="ai-card-text">
                  Save a few more products and I'll start spotting patterns & deals for you<span class="dot">.</span>
                </div>
                <button class="ai-card-cta" onclick="openModal('modal-product')">Save product <i data-lucide="arrow-right"></i></button>
              `}
            </div>
          </div>
        </div>

        <!-- Price Drops -->
        ${priceDrops.length > 0 ? `
          <div class="price-drop-section">
            <div class="section-header">
              <div>
                <div class="section-label">↘ PRICE DROPS ON SAVED PRODUCTS</div>
                <div class="section-title">Things that got cheaper<span class="dot">.</span></div>
              </div>
            </div>
            <div class="price-drop-grid">
              ${priceDrops.map(p => priceDropCard(p)).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;

    bindProductCardEvents();
    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('alert-circle', 'Something went wrong', e.message);
    lucide.createIcons();
  }
}

// ── Recent Product Card (Carousel) ─────────────────────
function recentProductCard(p) {
  const price = p.price_current ? `₹${p.price_current.toLocaleString('en-IN')}` : '';
  const oldPrice = (p.price_original && p.price_original > (p.price_current || 0))
    ? `₹${p.price_original.toLocaleString('en-IN')}` : '';
  const discount = (p.price_original && p.price_current && p.price_original > p.price_current)
    ? `₹${(p.price_original - p.price_current).toLocaleString('en-IN')} off` : '';
  const source = SOURCE_LABELS[(p.source || 'manual').toLowerCase()] || 'SAVED';
  const bgClass = getCardBg(p.id);
  const imageUrl = getProductImage(p);

  return `
    <div class="carousel-item">
      <div class="product-card-img" data-id="${p.id}" onclick="showDetail('${p.id}')">
        <div class="card-image ${!imageUrl ? bgClass : ''}">
          ${imageUrl ? `<img src="${imageUrl}" alt="${esc(p.title)}" loading="lazy" />` : `
            <div class="placeholder-icon"><i data-lucide="package"></i></div>
          `}
          ${discount ? `<div class="discount-badge"><i data-lucide="trending-down"></i> ${discount}</div>` : ''}
          <button class="heart-btn ${p.is_favorite ? 'active' : ''}" data-id="${p.id}" onclick="event.stopPropagation(); toggleFavorite('${p.id}')">
            <i data-lucide="heart"></i>
          </button>
        </div>
        <div class="card-info">
          <div class="card-info-row">
            <span class="card-product-name">${esc(p.title || 'Untitled')}</span>
            <span class="card-source">${source}</span>
          </div>
          <div class="card-price-row">
            ${price ? `<span class="card-price">${price}</span>` : ''}
            ${oldPrice ? `<span class="card-price-old">${oldPrice}</span>` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderMosaic(col) {
  const colProducts = state.products.filter(p => 
    p.collections && p.collections.some(c => c.id === col.id)
  );

  let cellsHtml = '';
  for (let i = 0; i < 4; i++) {
    const p = colProducts[i];
    if (p) {
      const imgUrl = getProductImage(p);
      const bgClass = getCardBg(p.id);
      if (imgUrl) {
        cellsHtml += `<div class="mosaic-cell"><img src="${imgUrl}" alt="${esc(p.title)}" loading="lazy" /></div>`;
      } else {
        cellsHtml += `<div class="mosaic-cell ${bgClass}" style="display:flex;align-items:center;justify-content:center;color:rgba(0,0,0,0.15);"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-package"><path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2 2 2 0 0 0-2 2v8a2 2 0 0 0 2 2z"/></svg></div>`;
      }
    } else {
      const bgClass = getCardBg(col.id + i);
      cellsHtml += `<div class="mosaic-cell ${bgClass}"><div class="cell-placeholder"></div></div>`;
    }
  }
  return cellsHtml;
}

// ── Collection Mosaic Card ─────────────────────────────
function collectionMosaicCard(col) {
  const emoji = col.emoji || '📁';
  return `
    <div class="collection-card" onclick="navigate('collection', '${col.id}')" style="cursor: pointer;">
      <div class="collection-mosaic">
        ${renderMosaic(col)}
      </div>
      <div class="collection-meta">
        <span class="collection-emoji">${emoji}</span>
        <span class="collection-name">${esc(col.name)}</span>
        <span class="collection-count">${col.product_count || 0}</span>
      </div>
    </div>
  `;
}

// ── Price Drop Card ────────────────────────────────────
function priceDropCard(p) {
  const current = `₹${p.price_current.toLocaleString('en-IN')}`;
  const original = `₹${p.price_original.toLocaleString('en-IN')}`;
  const diff = `₹${(p.price_original - p.price_current).toLocaleString('en-IN')} off`;
  const bgClass = getCardBg(p.id);
  const imageUrl = getProductImage(p);

  return `
    <div class="price-drop-card" onclick="showDetail('${p.id}')">
      <div class="price-drop-thumb ${!imageUrl ? bgClass : ''}">
        ${imageUrl ? `<img src="${imageUrl}" alt="${esc(p.title)}" />` : ''}
      </div>
      <div class="price-drop-info">
        <div class="price-drop-name">${esc(p.title || 'Untitled')}</div>
        <div class="price-drop-prices">
          <span class="price-drop-current">${current}</span>
          <span class="price-drop-old">${original}</span>
        </div>
        <div class="price-drop-discount"><i data-lucide="trending-down"></i> ${diff}</div>
      </div>
    </div>
  `;
}

// ── Gallery ────────────────────────────────────────────
async function renderGallery(favsOnly = false) {
  const c = $('#content');

  if (!state.token) {
    c.innerHTML = emptyHTML('image', 'Sign in to view your gallery', 'Create an account to start saving products from the web.', `<button class="btn btn-primary" onclick="openModal('modal-auth')"><i data-lucide="log-in"></i> Sign In</button>`);
    lucide.createIcons();
    return;
  }

  showShimmer(c);

  try {
    let url = '/products?page_size=50';
    if (favsOnly) url += '&is_favorite=true';
    const data = await api(url);
    state.products = data.items || [];

    // Get categories for filter pills
    if (state.categories.length === 0) {
      try {
        const catData = await api('/categories');
        state.categories = catData.categories || catData || [];
      } catch {}
    }

    const sectionLabel = favsOnly ? 'YOUR SAVED FAVORITES' : 'EVERY PRODUCT YOU LOVED';
    const sectionTitle = favsOnly ? 'Wishlist' : 'Your Gallery';
    const filterCategories = ['All', ...state.categories.slice(0, 7).map(c => c.name)];

    c.innerHTML = `
      <div class="content-inner">
        <div style="margin-bottom: 24px;">
          <div class="section-label">${sectionLabel}</div>
          <div class="section-title">${sectionTitle}<span class="dot">.</span></div>
        </div>

        <div class="gallery-toolbar">
          <div class="gallery-search">
            <i data-lucide="search"></i>
            <input type="text" id="gallery-search-input" placeholder="Search your gallery..." />
          </div>
          <select class="gallery-sort" id="gallery-sort">
            <option value="recent">Recently saved</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="name">Name A-Z</option>
          </select>
          <div class="gallery-view-toggle">
            <button class="gallery-view-btn active" data-view-mode="grid" title="Grid view"><i data-lucide="grid-3x3"></i></button>
            <button class="gallery-view-btn" data-view-mode="list" title="List view"><i data-lucide="list"></i></button>
          </div>
        </div>

        <div class="filter-pills" id="filter-pills">
          ${filterCategories.map(cat => `
            <button class="filter-pill ${cat === state.galleryFilter ? 'active' : ''}" data-filter="${cat}">${cat}</button>
          `).join('')}
        </div>

        ${state.products.length > 0 ? `
          <div class="gallery-grid" id="gallery-grid">
            ${state.products.map(p => galleryProductCard(p)).join('')}
          </div>
        ` : `
          <div class="empty-state" style="padding: 60px 20px;">
            <div class="empty-icon-wrap"><i data-lucide="${favsOnly ? 'heart' : 'image'}"></i></div>
            <h3 class="empty-title">${favsOnly ? 'No favorites yet' : 'No products saved'}</h3>
            <p class="empty-desc">${favsOnly ? 'Heart your favorite products and they\'ll appear here.' : 'Save your first product to get started.'}</p>
          </div>
        `}
      </div>
    `;

    // Bind events
    bindGalleryEvents();
    bindProductCardEvents();
    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('alert-circle', 'Error loading gallery', e.message);
    lucide.createIcons();
  }
}

function galleryProductCard(p) {
  const price = p.price_current ? `₹${p.price_current.toLocaleString('en-IN')}` : '';
  const oldPrice = (p.price_original && p.price_original > (p.price_current || 0))
    ? `₹${p.price_original.toLocaleString('en-IN')}` : '';
  const discount = (p.price_original && p.price_current && p.price_original > p.price_current)
    ? `₹${(p.price_original - p.price_current).toLocaleString('en-IN')} off` : '';
  const bgClass = getCardBg(p.id);
  const imageUrl = getProductImage(p);

  return `
    <div class="gallery-card" data-id="${p.id}" onclick="showDetail('${p.id}')">
      <div class="card-image ${!imageUrl ? bgClass : ''}">
        ${imageUrl ? `<img src="${imageUrl}" alt="${esc(p.title)}" loading="lazy" />` : `
          <div class="placeholder-icon"><i data-lucide="package"></i></div>
        `}
        ${discount ? `<div class="discount-badge"><i data-lucide="trending-down"></i> ${discount}</div>` : ''}
        <button class="heart-btn ${p.is_favorite ? 'active' : ''}" data-id="${p.id}" onclick="event.stopPropagation(); toggleFavorite('${p.id}')">
          <i data-lucide="heart"></i>
        </button>
      </div>
      <div class="card-info">
        <div class="card-product-name">${esc(p.title || 'Untitled')}</div>
        ${p.brand ? `<div style="font-size:0.75rem;color:var(--text-tertiary);margin-top:1px;">${esc(p.brand)}</div>` : ''}
        <div class="card-price-row">
          ${price ? `<span class="card-price">${price}</span>` : ''}
          ${oldPrice ? `<span class="card-price-old">${oldPrice}</span>` : ''}
        </div>
      </div>
    </div>
  `;
}

function bindGalleryEvents() {
  // Filter pills
  $$('#filter-pills .filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      state.galleryFilter = pill.dataset.filter;
      $$('#filter-pills .filter-pill').forEach(p => p.classList.toggle('active', p.dataset.filter === state.galleryFilter));
      filterGallery();
    });
  });

  // Search
  const searchInput = $('#gallery-search-input');
  if (searchInput) {
    let timer;
    searchInput.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => filterGallery(), 300);
    });
  }

  // Sort
  const sortSelect = $('#gallery-sort');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => sortGallery());
  }

  // View toggle
  $$('.gallery-view-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.gallery-view-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Could toggle list view here
    });
  });
}

function filterGallery() {
  const searchVal = ($('#gallery-search-input')?.value || '').toLowerCase().trim();
  const grid = $('#gallery-grid');
  if (!grid) return;

  const cards = grid.querySelectorAll('.gallery-card');
  cards.forEach(card => {
    const id = card.dataset.id;
    const p = state.products.find(x => x.id === id);
    if (!p) return;

    let show = true;
    // Text search filter
    if (searchVal) {
      const haystack = `${p.title || ''} ${p.brand || ''} ${p.store || ''}`.toLowerCase();
      show = haystack.includes(searchVal);
    }
    // Category filter
    if (show && state.galleryFilter && state.galleryFilter !== 'All') {
      show = (p.category_name === state.galleryFilter);
    }
    card.style.display = show ? '' : 'none';
  });
}

function sortGallery() {
  const sortVal = $('#gallery-sort')?.value || 'recent';
  const grid = $('#gallery-grid');
  if (!grid) return;

  let sorted = [...state.products];
  switch (sortVal) {
    case 'price-asc': sorted.sort((a, b) => (a.price_current || 0) - (b.price_current || 0)); break;
    case 'price-desc': sorted.sort((a, b) => (b.price_current || 0) - (a.price_current || 0)); break;
    case 'name': sorted.sort((a, b) => (a.title || '').localeCompare(b.title || '')); break;
    default: break; // Already sorted by recent
  }

  grid.innerHTML = sorted.map(p => galleryProductCard(p)).join('');
  bindProductCardEvents();
  lucide.createIcons();
}

// ── Collections Page ───────────────────────────────────
async function renderCollections() {
  const c = $('#content');

  if (!state.token) {
    c.innerHTML = emptyHTML('layers', 'Sign in to view collections', 'Create an account to organize your products.', `<button class="btn btn-primary" onclick="openModal('modal-auth')"><i data-lucide="log-in"></i> Sign In</button>`);
    lucide.createIcons();
    return;
  }

  showShimmer(c);

  try {
    const data = await api('/collections');
    state.collections = data.items || [];

    c.innerHTML = `
      <div class="content-inner">
        <div class="collections-page-header">
          <div class="left">
            <h1>Collections<span class="dot" style="color:var(--purple)">.</span></h1>
            <p>Organize your product universe.</p>
          </div>
          <button class="btn btn-primary" onclick="openModal('modal-collection')">
            <i data-lucide="plus"></i> New Collection
          </button>
        </div>

        ${state.collections.length > 0 ? `
          <div class="collections-page-grid">
            ${state.collections.map(col => collectionFullCard(col)).join('')}
          </div>
        ` : `
          <div class="empty-state" style="padding: 60px 20px;">
            <div class="empty-icon-wrap"><i data-lucide="layers"></i></div>
            <h3 class="empty-title">No collections yet</h3>
            <p class="empty-desc">Create your first collection to start organizing your saved products.</p>
            <button class="btn btn-primary" onclick="openModal('modal-collection')"><i data-lucide="plus"></i> Create Collection</button>
          </div>
        `}
      </div>
    `;

    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('alert-circle', 'Error loading collections', e.message);
    lucide.createIcons();
  }
}

function collectionFullCard(col) {
  const emoji = col.emoji || '📁';
  const count = col.product_count || 0;

  return `
    <div class="collection-card-full" onclick="navigate('collection', '${col.id}')" style="cursor: pointer;">
      <div class="mosaic">
        ${renderMosaic(col)}
      </div>
      <div class="meta">
        <span class="emoji">${emoji}</span>
        <span class="name">${esc(col.name)}</span>
        <span class="count">${count}</span>
      </div>
      <div class="sub-meta">${count} product${count !== 1 ? 's' : ''}</div>
    </div>
  `;
}

async function renderCollectionDetail(collectionId) {
  const c = $('#content');
  showShimmer(c);

  try {
    const col = await api('/collections/' + collectionId);
    state.products = col.products || [];

    // Get categories for filter pills
    if (state.categories.length === 0) {
      try {
        const catData = await api('/categories');
        state.categories = catData.categories || catData || [];
      } catch {}
    }

    const emoji = col.emoji || '📁';
    const filterCategories = ['All', ...state.categories.slice(0, 7).map(c => c.name)];

    // Reset filter
    state.galleryFilter = 'All';

    c.innerHTML = `
      <div class="content-inner">
        <div style="margin-bottom: 24px; display: flex; align-items: center; gap: 16px;">
          <span style="font-size: 2.8rem; line-height: 1;">${emoji}</span>
          <div>
            <div class="section-label">COLLECTION</div>
            <div class="section-title" style="margin-top: 4px; font-size: 2.2rem; font-family: 'DM Serif Display', serif;">${esc(col.name)}<span class="dot" style="color:var(--purple)">.</span></div>
            ${col.description ? `<p style="color: var(--text-tertiary); font-size: 0.9rem; margin-top: 4px;">${esc(col.description)}</p>` : ''}
          </div>
        </div>

        <div class="gallery-toolbar">
          <div class="gallery-search">
            <i data-lucide="search"></i>
            <input type="text" id="gallery-search-input" placeholder="Search this collection..." />
          </div>
          <select class="gallery-sort" id="gallery-sort">
            <option value="recent">Recently saved</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="name">Name A-Z</option>
          </select>
          <div class="gallery-view-toggle">
            <button class="gallery-view-btn active" data-view-mode="grid" title="Grid view"><i data-lucide="grid-3x3"></i></button>
            <button class="gallery-view-btn" data-view-mode="list" title="List view"><i data-lucide="list"></i></button>
          </div>
        </div>

        <div class="filter-pills" id="filter-pills">
          ${filterCategories.map(cat => `
            <button class="filter-pill ${cat === state.galleryFilter ? 'active' : ''}" data-filter="${cat}">${cat}</button>
          `).join('')}
        </div>

        ${state.products.length > 0 ? `
          <div class="gallery-grid" id="gallery-grid">
            ${state.products.map(p => galleryProductCard(p)).join('')}
          </div>
        ` : `
          <div class="empty-state" style="padding: 60px 20px;">
            <div class="empty-icon-wrap"><i data-lucide="package"></i></div>
            <h3 class="empty-title">No products here yet</h3>
            <p class="empty-desc">Save a product and select this collection to see it here.</p>
          </div>
        `}
      </div>
    `;

    bindGalleryEvents();
    bindProductCardEvents();
    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('alert-circle', 'Error loading collection', e.message);
    lucide.createIcons();
  }
}

// ── Create Collection ──────────────────────────────────
async function createCollection() {
  const name = $('#coll-name').value.trim();
  const emoji = $('#coll-emoji').value.trim() || undefined;
  const description = $('#coll-desc').value.trim() || undefined;

  if (!name) { toast('Please enter a name', 'error'); return; }

  try {
    await api('/collections', 'POST', { name, emoji, description });
    closeModal('modal-collection');
    $('#form-collection').reset();
    toast('Collection created! 📁', 'success');
    if (state.view === 'collections') renderCollections();
    else if (state.view === 'home') renderHome();
  } catch (e) {
    toast(e.message || 'Failed to create collection', 'error');
  }
}

// ── Discover Page ──────────────────────────────────────
function renderDiscover() {
  const c = $('#content');
  c.innerHTML = `
    <div class="content-inner">
      <div style="margin-bottom: 24px;">
        <div class="section-label">EXPLORE & DISCOVER</div>
        <div class="section-title">Discover<span class="dot">.</span></div>
      </div>
      <div class="empty-state" style="padding: 60px 20px;">
        <div class="empty-icon-wrap"><i data-lucide="sparkles"></i></div>
        <h3 class="empty-title">Coming soon</h3>
        <p class="empty-desc">AI-powered product recommendations and trends will appear here in a future update.</p>
      </div>
    </div>
  `;
  lucide.createIcons();
}

// ── Price Drops Page ───────────────────────────────────
async function renderPriceDropsPage() {
  const c = $('#content');

  if (!state.token) {
    c.innerHTML = emptyHTML('trending-down', 'Sign in to track price drops', 'We\'ll notify you when your saved products get cheaper.', `<button class="btn btn-primary" onclick="openModal('modal-auth')"><i data-lucide="log-in"></i> Sign In</button>`);
    lucide.createIcons();
    return;
  }

  showShimmer(c);

  try {
    if (state.products.length === 0) {
      const data = await api('/products?page_size=50');
      state.products = data.items || [];
    }

    const priceDrops = state.products.filter(p => p.price_original && p.price_current && p.price_original > p.price_current);

    c.innerHTML = `
      <div class="content-inner">
        <div style="margin-bottom: 24px;">
          <div class="section-label">↘ PRICE DROPS ON SAVED PRODUCTS</div>
          <div class="section-title">Things that got cheaper<span class="dot">.</span></div>
        </div>

        ${priceDrops.length > 0 ? `
          <div class="price-drop-grid">
            ${priceDrops.map(p => priceDropCard(p)).join('')}
          </div>
        ` : `
          <div class="empty-state" style="padding: 60px 20px;">
            <div class="empty-icon-wrap"><i data-lucide="trending-down"></i></div>
            <h3 class="empty-title">No price drops yet</h3>
            <p class="empty-desc">When your saved products drop in price, they'll show up here. Keep saving products!</p>
          </div>
        `}
      </div>
    `;
    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('alert-circle', 'Error', e.message);
    lucide.createIcons();
  }
}

// ── Product Detail ─────────────────────────────────────
window.showDetail = async function(id) {
  const p = state.products.find(x => x.id === id);
  if (!p) return;

  // Make sure categories are loaded
  if (state.categories.length === 0) {
    try {
      const catData = await api('/categories');
      state.categories = catData.categories || catData || [];
    } catch {}
  }

  const price = p.price_current ? `₹${p.price_current.toLocaleString('en-IN')}` : '—';

  $('#detail-body').innerHTML = `
    <div class="detail-top">
      <div>
        <div class="detail-title">${esc(p.title || 'Untitled')}</div>
        ${p.brand ? `<div class="detail-brand">${esc(p.brand)}</div>` : ''}
      </div>
      <div class="detail-price">${price}</div>
    </div>
    <div class="detail-grid">
      <div class="detail-cell"><span class="detail-cell-label">Status</span><span class="detail-cell-value">${p.status}</span></div>
      <div class="detail-cell"><span class="detail-cell-label">Source</span><span class="detail-cell-value">${p.source || 'manual'}</span></div>
      <div class="detail-cell"><span class="detail-cell-label">Store</span><span class="detail-cell-value">${p.store || '—'}</span></div>
      <div class="detail-cell"><span class="detail-cell-label">Priority</span><span class="detail-cell-value">${'★'.repeat(p.priority)}${'☆'.repeat(5 - p.priority)}</span></div>
      <div class="detail-cell"><span class="detail-cell-label">Currency</span><span class="detail-cell-value">${p.currency}</span></div>
      <div class="detail-cell"><span class="detail-cell-label">Saved</span><span class="detail-cell-value">${new Date(p.saved_at).toLocaleDateString()}</span></div>
      
      <div class="detail-cell" style="grid-column: span 2; display: flex; align-items: center; gap: 8px; margin-top: 10px;">
        <span class="detail-cell-label" style="margin-bottom: 0; min-width: 60px;">Category</span>
        <select id="detail-category-select" style="font-size: 0.85rem; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-body); cursor: pointer; flex-1: 1;">
          <option value="">None (uncategorized)</option>
          ${state.categories.map(c => `
            <option value="${c.id}" ${c.id === p.category_id ? 'selected' : ''}>${esc(c.name)}</option>
          `).join('')}
        </select>
      </div>
    </div>
    ${p.notes ? `<div class="detail-notes-box">${esc(p.notes)}</div>` : ''}
    ${p.source_url ? `<p style="margin-bottom:20px"><a href="${p.source_url}" target="_blank" style="color:var(--purple);word-break:break-all;font-size:0.85rem">${esc(p.source_url)}</a></p>` : ''}
    <div class="detail-actions">
      <button class="btn ${p.is_favorite ? 'btn-secondary' : 'btn-primary'}" onclick="toggleFavAndRefresh('${p.id}')"><i data-lucide="${p.is_favorite ? 'heart-off' : 'heart'}"></i> ${p.is_favorite ? 'Unfavorite' : 'Favorite'}</button>
      <button class="btn btn-danger" onclick="deleteAndClose('${p.id}')"><i data-lucide="trash-2"></i> Delete</button>
    </div>
  `;
  openModal('modal-detail');
  lucide.createIcons();

  // Bind change listener for Category
  const selectEl = $('#detail-category-select');
  if (selectEl) {
    selectEl.addEventListener('change', async (e) => {
      const newCatId = e.target.value || null;
      try {
        const updated = await api(`/products/${p.id}`, 'PUT', { category_id: newCatId });
        // Update product in state
        const idx = state.products.findIndex(x => x.id === p.id);
        if (idx !== -1) {
          state.products[idx] = updated;
        }
        toast('Category updated! 🏷️', 'success');
        // Refresh current detail view
        showDetail(p.id);
        // Refresh the underlying page view
        if (state.view === 'gallery' || state.view === 'wishlist') renderGallery(state.view === 'wishlist');
        else if (state.view === 'home') renderHome();
      } catch (err) {
        toast('Failed to update category', 'error');
      }
    });
  }
};

window.toggleFavAndRefresh = async function(id) {
  await toggleFavorite(id);
  showDetail(id);
};

window.deleteAndClose = async function(id) {
  await deleteProduct(id);
  closeModal('modal-detail');
};

// ── Actions ────────────────────────────────────────────
window.toggleFavorite = async function(id) {
  try {
    const updated = await api(`/products/${id}/favorite`, 'POST');
    const idx = state.products.findIndex(p => p.id === id);
    if (idx !== -1) state.products[idx] = updated;
    // Update heart button visually
    const heartBtns = document.querySelectorAll(`.heart-btn[data-id="${id}"]`);
    heartBtns.forEach(btn => {
      btn.classList.toggle('active', updated.is_favorite);
    });
    toast(updated.is_favorite ? 'Added to favorites ❤️' : 'Removed from favorites', 'success');
  } catch (e) {
    toast('Failed to toggle favorite', 'error');
  }
};

async function deleteProduct(id) {
  try {
    await api(`/products/${id}`, 'DELETE');
    state.products = state.products.filter(p => p.id !== id);
    if (state.view === 'gallery' || state.view === 'wishlist') renderGallery(state.view === 'wishlist');
    else if (state.view === 'home') renderHome();
    toast('Product deleted', 'info');
  } catch (e) {
    toast('Failed to delete', 'error');
  }
}

async function saveProduct() {
  const name = $('#prod-name').value.trim();
  const url = $('#prod-url').value.trim();
  const imageUrl = $('#prod-image-url').value.trim() || undefined;
  const brand = $('#prod-brand').value.trim() || undefined;
  const price = $('#prod-price').value ? parseFloat($('#prod-price').value) : undefined;
  const source = $('#prod-source').value;
  const priority = parseInt($('#prod-priority').value);
  const notes = $('#prod-notes').value.trim() || undefined;
  const collectionId = $('#prod-collection')?.value || '';
  const categoryId = $('#prod-category')?.value || '';
  const fileInput = $('#prod-image-file');

  if (!name && !url) {
    toast('Please enter a Product Name or Product URL', 'error');
    return;
  }

  const body = { source: url ? 'web' : source, priority };
  if (name) body.title = name;
  if (url) body.source_url = url;
  if (brand) body.brand = brand;
  if (price) body.price_current = price;
  if (notes) body.notes = notes;
  if (imageUrl) body.image_url = imageUrl;
  if (collectionId) body.collection_ids = [collectionId];
  if (categoryId) body.category_id = categoryId;

  try {
    const saved = await api('/products', 'POST', body);

    // If there is an uploaded image file, upload it
    if (fileInput && fileInput.files && fileInput.files[0]) {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);

      const uploadRes = await fetch(`${API}/products/${saved.id}/images`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${state.token}`
        },
        body: formData
      });
      if (!uploadRes.ok) {
        const errData = await uploadRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to upload photo file');
      }
    }

    closeModal('modal-product');
    $('#form-product').reset();
    const previewContainer = $('#prod-preview-container');
    if (previewContainer) previewContainer.classList.add('hidden');
    const previewImg = $('#prod-preview-img');
    if (previewImg) previewImg.src = '';
    toast('Product saved! ✨', 'success');
    // Refresh collections state so home page shows updated counts
    if (state.token) {
      const cData = await api('/collections').catch(() => ({ items: [] }));
      state.collections = cData.items || [];
    }
    navigate(state.view);
  } catch (e) {
    toast(e.message || 'Failed to save', 'error');
  }
}

async function handleUrlExtraction(url) {
  if (!url || !/^https?:\/\//.test(url)) return;

  const previewContainer = $('#prod-preview-container');
  const previewImg = $('#prod-preview-img');

  if (!previewContainer || !previewImg) return;

  previewContainer.classList.remove('hidden');
  previewImg.src = '';
  previewImg.classList.add('hidden');

  // Show loading message
  let loadingText = $('#prod-preview-loading');
  if (!loadingText) {
    loadingText = document.createElement('div');
    loadingText.id = 'prod-preview-loading';
    loadingText.style.fontSize = '0.8rem';
    loadingText.style.color = 'var(--text-secondary)';
    loadingText.style.marginTop = '5px';
    previewContainer.appendChild(loadingText);
  }
  loadingText.textContent = 'Extracting product photo and details... 🔍';

  try {
    const data = await api('/products/extract', 'POST', { url });

    // Auto-populate fields if empty
    if (data.title && !$('#prod-name').value.trim()) {
      $('#prod-name').value = data.title;
    }
    if (data.brand && !$('#prod-brand').value.trim()) {
      $('#prod-brand').value = data.brand;
    }
    if (data.price && !$('#prod-price').value) {
      $('#prod-price').value = data.price;
    }

    // Set source dropdown to web
    if ($('#prod-source')) {
      $('#prod-source').value = 'web';
    }

    // Live preview extracted photo
    if (data.image_urls && data.image_urls.length > 0) {
      previewImg.src = data.image_urls[0];
      $('#prod-image-url').value = data.image_urls[0];
      previewImg.classList.remove('hidden');
    } else {
      previewContainer.classList.add('hidden');
    }
  } catch (e) {
    console.error('Extraction failed:', e);
    toast('Could not extract image from URL automatically.', 'info');
  } finally {
    const loading = $('#prod-preview-loading');
    if (loading) loading.remove();
  }
}

// Populate the collection dropdown inside the Save Product modal
async function refreshCollectionsForPicker() {
  const sel = $('#prod-collection');
  if (!sel) return;
  if (!state.token) {
    sel.innerHTML = '<option value="">— sign in first —</option>';
    return;
  }
  try {
    const data = await api('/collections');
    state.collections = data.items || [];
  } catch { /* keep cached */ }

  if (state.collections.length === 0) {
    sel.innerHTML = '<option value="">No collections yet — create one first</option>';
  } else {
    sel.innerHTML = '<option value="">None (unsorted)</option>' +
      state.collections.map(c =>
        `<option value="${c.id}">${c.emoji ? c.emoji + ' ' : ''}${esc(c.name)}</option>`
      ).join('');
  }
}

// Populate the category dropdown inside the Save Product modal
async function refreshCategoriesForPicker() {
  const sel = $('#prod-category');
  if (!sel) return;
  if (!state.token) {
    sel.innerHTML = '<option value="">— sign in first —</option>';
    return;
  }
  if (state.categories.length === 0) {
    try {
      const catData = await api('/categories');
      state.categories = catData.categories || catData || [];
    } catch {}
  }

  sel.innerHTML = '<option value="">None (uncategorized)</option>' +
    state.categories.map(c =>
      `<option value="${c.id}">${esc(c.name)}</option>`
    ).join('');
}

// ── Health ──────────────────────────────────────────────
async function renderHealth() {
  const c = $('#content');
  showShimmer(c);

  try {
    const [health, ready] = await Promise.all([
      fetch(`${BASE}/health`).then(r => r.json()).catch(() => ({ status: 'unreachable' })),
      fetch(`${BASE}/ready`).then(r => r.json()).catch(() => ({ status: 'unknown', checks: {} })),
    ]);

    const checks = ready.checks || {};
    const isUp = health.status === 'healthy' || health.status === 'ok';

    c.innerHTML = `
      <div class="content-inner">
        <div class="page-header"><div><h1>System Health</h1><p class="page-header-sub">Infrastructure status</p></div></div>
        <div class="health-grid">
          <div class="health-card">
            <div class="health-status">
              <div class="status-dot ${isUp ? 'online' : 'offline'}"></div>
              <span class="health-name">API Server</span>
            </div>
            <div class="health-detail">Status: ${health.status || 'unknown'}</div>
            <div class="health-detail">Version: ${health.version || 'N/A'}</div>
          </div>
          <div class="health-card">
            <div class="health-status">
              <div class="status-dot ${checks.database === 'ok' ? 'online' : 'offline'}"></div>
              <span class="health-name">PostgreSQL</span>
            </div>
            <div class="health-detail">Status: ${checks.database || 'checking...'}</div>
          </div>
          <div class="health-card">
            <div class="health-status">
              <div class="status-dot online"></div>
              <span class="health-name">Redis</span>
            </div>
            <div class="health-detail">Host: localhost:6379</div>
          </div>
          <div class="health-card">
            <div class="health-status">
              <div class="status-dot online"></div>
              <span class="health-name">MinIO (S3)</span>
            </div>
            <div class="health-detail">Console: <a href="http://localhost:9001" target="_blank" style="color:var(--purple)">localhost:9001</a></div>
          </div>
        </div>
      </div>
    `;
    lucide.createIcons();
  } catch (e) {
    c.innerHTML = emptyHTML('server-off', 'Backend unreachable', 'Make sure Docker is running.');
    lucide.createIcons();
  }
}

// ── Settings ───────────────────────────────────────────
function renderSettings() {
  const c = $('#content');
  c.innerHTML = `
    <div class="content-inner">
      <div class="page-header"><div><h1>Settings</h1><p class="page-header-sub">App configuration</p></div></div>
      <div class="settings-card">
        <h3>About</h3>
        <div class="health-detail">Product Gallery v0.1.0</div>
        <div class="health-detail">Backend: FastAPI + PostgreSQL + Redis</div>
        <div class="health-detail">Frontend: Vanilla JS + Lucide Icons</div>
        <div class="health-detail" style="margin-top:12px">Phase 1: Core CRUD — Complete ✅</div>
        <div class="health-detail">Phase 2: AI Extraction — Planned</div>
        <div class="health-detail">Phase 3: Price Tracking — Planned</div>
        <div class="health-detail">Phase 4: AI Copilot — Planned</div>
      </div>
    </div>
  `;
  lucide.createIcons();
}

// ── API Helper ─────────────────────────────────────────
async function api(path, method = 'GET', body) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, opts);
  if (res.status === 204) return null;

  if (res.status === 401 && path !== '/auth/login' && path !== '/auth/register') {
    state.token = null;
    state.user = null;
    localStorage.removeItem('pg_token');
    renderSidebarUser();
    navigate('home');
    showAuthPage();
    toast('Session expired. Please sign in again.', 'error');
    throw new Error('Session expired');
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
  return data;
}

// ── Image Helper ───────────────────────────────────────
function getProductImage(p) {
  // Check for image_url, thumbnail_url, or images array
  if (p.image_url) return p.image_url;
  if (p.thumbnail_url) return p.thumbnail_url;
  if (p.images && p.images.length > 0) return p.images[0].url || p.images[0];
  return null;
}

// ── UI Helpers ─────────────────────────────────────────
window.showAuthPage = function() {
  const authPage = $('#auth-page');
  if (authPage) {
    const landingPage = $('#landing-page');
    if (landingPage) landingPage.classList.add('hidden');
    
    authPage.classList.remove('hidden');
    authPage.style.opacity = '1';
    authPage.style.transform = 'scale(1)';
    lucide.createIcons();
  }
};
window.openModal = function(id) {
  if (id === 'modal-auth') {
    showAuthPage();
    return;
  }
  document.getElementById(id).classList.remove('hidden');
  lucide.createIcons();
};
function closeModal(id) {
  if (id === 'modal-auth') {
    const authPage = $('#auth-page');
    if (authPage) authPage.classList.add('hidden');
    return;
  }
  document.getElementById(id).classList.add('hidden');
}
window.logout = logout;

function showShimmer(el) {
  el.innerHTML = `<div class="content-inner"><div class="shimmer-grid">${Array(8).fill('<div class="shimmer-block"></div>').join('')}</div></div>`;
}

function emptyHTML(icon, title, desc, extra = '') {
  return `<div class="content-inner"><div class="empty-state"><div class="empty-icon-wrap"><i data-lucide="${icon}"></i></div><h3 class="empty-title">${title}</h3><p class="empty-desc">${desc}</p>${extra}</div></div>`;
}

function bindProductCardEvents() {
  // Heart buttons are bound inline via onclick
}

function toast(msg, type = 'info') {
  const icons = { success: 'check-circle-2', error: 'x-circle', info: 'info' };
  const div = document.createElement('div');
  div.className = `toast ${type}`;
  div.innerHTML = `<i data-lucide="${icons[type] || 'info'}"></i> ${esc(msg)}`;
  $('#toast-container').appendChild(div);
  lucide.createIcons();
  setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 200); }, 3000);
}

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function avgPrice(products) {
  const priced = products.filter(p => p.price_current);
  if (!priced.length) return '—';
  const avg = priced.reduce((s, p) => s + p.price_current, 0) / priced.length;
  return '₹' + Math.round(avg).toLocaleString('en-IN');
}

// ── Landing Page ──────────────────────────────────────
window.renderLandingPage = function() {
  const page = $('#landing-page');
  if (!page) return;

  const greeting = $('#landing-greeting');
  const subtitle = $('#landing-subtitle');
  const enterBtn = $('#btn-enter-gallery');

  if (state.token && sessionStorage.getItem('pg_entered') === 'true') {
    page.classList.add('hidden');
    return;
  }

  if (state.token && state.user) {
    greeting.textContent = `Hello, ${state.user.name || 'Meghana'}.`;
    subtitle.textContent = "Your curated memory of style, taste, and items you love.";
    enterBtn.innerHTML = `<span>Enter Gallery</span> <i data-lucide="arrow-right"></i>`;
    
    enterBtn.onclick = () => {
      page.style.opacity = '0';
      page.style.transform = 'scale(1.05)';
      sessionStorage.setItem('pg_entered', 'true');
      setTimeout(() => page.classList.add('hidden'), 500);
    };
  } else {
    greeting.textContent = "Product Gallery.";
    subtitle.textContent = "Your curated memory of style, taste, and items you love.";
    enterBtn.innerHTML = `<span>Sign In to Enter</span> <i data-lucide="log-in"></i>`;
    
    enterBtn.onclick = () => {
      page.style.opacity = '0';
      page.style.transform = 'scale(0.97)';
      setTimeout(() => {
        page.classList.add('hidden');
        const authPage = $('#auth-page');
        if (authPage) {
          authPage.classList.remove('hidden');
          authPage.style.opacity = '1';
          authPage.style.transform = 'scale(1)';
        }
      }, 300);
    };
  }
  
  page.classList.remove('hidden');
  page.style.opacity = '1';
  page.style.transform = 'scale(1)';
  lucide.createIcons();
};
