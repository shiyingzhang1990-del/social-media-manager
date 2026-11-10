/**
 * Main application - routing, modal, toast, auth.
 */

// ── Auth ───────────────────────────────────────────────────────
const loginPage = document.getElementById('login-page');
const appEl = document.getElementById('app');
const loginBtn = document.getElementById('login-btn');
const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');

function showApp() {
  loginPage.style.display = 'none';
  appEl.style.display = 'flex';
}

function showLogin() {
  appEl.style.display = 'none';
  loginPage.style.display = 'flex';
  loginError.style.display = 'none';
}

async function doLogin() {
  const username = loginUsername.value.trim();
  const password = loginPassword.value.trim();
  if (!username || !password) {
    loginError.textContent = '请输入用户名和密码';
    loginError.style.display = 'block';
    return;
  }
  loginBtn.disabled = true;
  loginBtn.textContent = '登录中...';
  try {
    const result = await API.login(username, password);
    if (result.success) {
      API.setToken(result.token);
      showApp();
      navigate('dashboard');
      loginPassword.value = '';
    }
  } catch (e) {
    loginError.textContent = e.message || '登录失败';
    loginError.style.display = 'block';
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = '登 录';
  }
}

async function doLogout() {
  try { await API.logout(); } catch (e) { /* ignore */ }
  API.clearToken();
  showLogin();
}

loginBtn.addEventListener('click', doLogin);
loginPassword.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') doLogin();
});
loginUsername.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') loginPassword.focus();
});
logoutBtn.addEventListener('click', (e) => {
  e.preventDefault();
  doLogout();
});

// ── Route View ──────────────────────────────────────────────────
const views = {
  dashboard: DashboardView,
  accounts: AccountsView,
  content: ContentView,
  publish: PublishView,
  calendar: CalendarView,
  analytics: AnalyticsView,
  schedules: SchedulesView,
  logs: LogsView,
};

function navigate(viewName) {
  if (!API.isLoggedIn()) {
    showLogin();
    return;
  }
  const view = views[viewName];
  if (!view) return;

  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === viewName);
  });

  view.render();
}

// ── Sidebar Navigation ─────────────────────────────────────────
document.addEventListener('click', (e) => {
  const navItem = e.target.closest('.nav-item');
  if (navItem && navItem.dataset.view) {
    e.preventDefault();
    navigate(navItem.dataset.view);
  }
});

// ── Modal ───────────────────────────────────────────────────────
function showModal(title, bodyHtml, confirmText, confirmCallback) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;

  const overlay = document.getElementById('modal-overlay');
  const modal = document.getElementById('modal-content');

  // Remove existing footer
  const oldFooter = modal.querySelector('.modal-footer');
  if (oldFooter) oldFooter.remove();

  if (confirmText && confirmCallback) {
    const footer = document.createElement('div');
    footer.className = 'modal-footer';
    footer.innerHTML = `
      <button class="btn btn-outline" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" id="modal-confirm">${confirmText}</button>
    `;
    modal.appendChild(footer);
    document.getElementById('modal-confirm').onclick = confirmCallback;
  }

  overlay.style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

document.getElementById('modal-close').onclick = closeModal;
document.getElementById('modal-overlay').onclick = (e) => {
  if (e.target === e.currentTarget) closeModal();
};

// ── Toast ───────────────────────────────────────────────────────
function toast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  document.body.appendChild(el);

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

// ── Init ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  if (API.isLoggedIn()) {
    try {
      const result = await API.getMe();
      if (result.success) {
        showApp();
        navigate('dashboard');
        return;
      }
    } catch (e) {
      API.clearToken();
    }
  }
  showLogin();
});
