import { branding } from './config/branding.js';
import { esc, icon } from './ui.js';
import * as screens from './screens.js';

const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const header = document.querySelector('#header');
const content = document.querySelector('#content');
const bottomNav = document.querySelector('#bottomNav');
const toast = document.querySelector('#toast');
// This is used only to personalize the interface. Server-side Telegram initData validation stays in the backend.
const user = tg?.initDataUnsafe?.user || null;
const state = { view: 'home' };

const navItems = [
  ['home', 'Home', 'home'], ['partners', 'Partners', 'users'], ['agents', 'Agents', 'briefcase'], ['support', 'Support', 'message'], ['profile', 'Profile', 'user'],
];

function notify(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function avatar() {
  const initial = (user?.first_name || user?.username || branding.shortName).slice(0, 1).toUpperCase();
  return user?.photo_url ? `<img class="avatar" src="${esc(user.photo_url)}" alt="Profile">` : `<span class="avatar">${initial}</span>`;
}

function renderHeader() {
  header.innerHTML = `<button class="brand" data-nav="home" aria-label="Home"><span class="brand-mark">${branding.shortName}</span><span class="brand-copy">${branding.name}<small>NETWORK</small></span></button><div class="header-actions"><button class="circle-button" data-nav="support" aria-label="Support">${icon('bell')}<i class="notice"></i></button><button class="circle-button" data-nav="profile" aria-label="Profile">${avatar()}</button></div>`;
}

function renderNav() {
  bottomNav.innerHTML = navItems.map(([view, label, image]) => `<button class="nav-item ${state.view === view ? 'active' : ''}" data-nav="${view}">${icon(image)}<span>${label}</span></button>`).join('');
}

function render() {
  const view = state.view;
  const renderers = {
    home: () => screens.home({ user }), partners: screens.partners, agents: screens.agents, banners: screens.banners,
    contact: () => screens.lookup({ block: false }), blacklist: () => screens.lookup({ block: true }), faq: screens.faq,
    support: screens.support, ticket: screens.ticket, profile: () => screens.profile({ user }),
    'agent-application': () => screens.application('agent'), 'partner-application': () => screens.application('partner'),
  };
  renderHeader();
  content.innerHTML = (renderers[view] || renderers.home)();
  renderNav();
  if (view === 'home') tg?.BackButton?.hide(); else tg?.BackButton?.show();
}

function go(view) {
  state.view = view;
  tg?.HapticFeedback?.impactOccurred('light');
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]');
  if (nav) return go(nav.dataset.nav);
  if (event.target.closest('.faq-question')) return event.target.closest('.faq-item').classList.toggle('open');
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (!action) return;
  if (action === 'copy') {
    try { await navigator.clipboard.writeText('Partners'); notify('Promotional text copied'); } catch { notify('Copy is not available in this Telegram client'); }
  } else if (action === 'material') notify('This preview will open when materials are published by an administrator.');
  else if (action === 'support' || action === 'manager') {
    if (branding.supportUsername) tg?.openTelegramLink?.(`https://t.me/${branding.supportUsername.replace('@', '')}`);
    else notify('Support contact will be configured by an administrator.');
  }
});

document.addEventListener('input', (event) => {
  if (event.target.id !== 'faqSearch') return;
  const query = event.target.value.trim().toLowerCase();
  document.querySelectorAll('[data-faq]').forEach((item) => {
    item.hidden = Boolean(query && !item.dataset.faq.includes(query));
  });
});

document.addEventListener('submit', (event) => {
  const formType = event.target.dataset.form;
  if (!formType) return;
  event.preventDefault();
  const button = event.target.querySelector('[type="submit"]');
  button.disabled = true;
  button.textContent = 'Sending…';
  setTimeout(() => {
    button.disabled = false;
    if (formType === 'lookup') {
      const result = document.querySelector('#lookupResult');
      result.className = 'result-card show';
      result.innerHTML = `<h3>Check is ready</h3><p>Server-side contact checks will show the final availability result once data is added.</p>`;
    } else {
      notify(formType === 'ticket' ? 'Request saved. A manager will reply in Telegram.' : 'Application saved. We will contact you in Telegram.');
      go('profile');
    }
  }, 450);
});

tg?.BackButton?.onClick(() => go('home'));
render();
