import { branding } from './config/branding.js';
import { esc, icon } from './ui.js';
import * as screens from './screens.js';

const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
const supportsBackButton = Boolean(tg?.isVersionAtLeast?.('6.1'));
const supportsHaptics = Boolean(tg?.isVersionAtLeast?.('6.1'));

const header = document.querySelector('#header');
const content = document.querySelector('#content');
const bottomNav = document.querySelector('#bottomNav');
const toast = document.querySelector('#toast');
const user = tg?.initDataUnsafe?.user || null; // presentation only; backend remains responsible for initData validation.
const state = { view: 'home' };
const navItems = [['home', 'Главная', 'home'], ['stats', 'Статистика', 'chart'], ['promotion', 'Продвижение', 'bolt'], ['support', 'Поддержка', 'message'], ['profile', 'Профиль', 'user']];

function message(text) { toast.textContent = text; toast.classList.add('show'); clearTimeout(message.timer); message.timer = setTimeout(() => toast.classList.remove('show'), 2300); }
function avatar() { const mark = (user?.first_name || user?.username || 'P').slice(0, 1).toUpperCase(); return user?.photo_url ? `<img class="avatar" src="${esc(user.photo_url)}" alt="Профиль">` : `<span class="avatar">${mark}</span>`; }

function renderHeader() { header.innerHTML = `<button class="portal-mark" data-nav="home" aria-label="Главная">PM</button><div class="portal-title"><b>${branding.name}</b><span>PORTAL</span></div><div class="header-tools"><button class="online-chip" data-nav="profile"><i></i>ONLINE</button><button class="header-avatar" data-nav="profile" aria-label="Профиль">${avatar()}</button></div>`; }
function renderNav() { bottomNav.innerHTML = navItems.map(([view, title, image]) => `<button class="nav-item ${state.view === view ? 'active' : ''}" data-nav="${view}">${icon(image)}<span>${title}</span></button>`).join(''); }
function renderModal() { document.querySelector('#modalLayer')?.remove(); document.body.insertAdjacentHTML('beforeend', `<div id="modalLayer" class="modal-layer"><div class="bottom-sheet"><button class="sheet-close" data-action="close-modal" aria-label="Закрыть">${icon('close')}</button><span class="sheet-kicker">ВАШ QR</span><h2>Приглашайте партнёров</h2><div class="qr-placeholder">${icon('qr')}</div><p>QR станет доступен после активации персональной ссылки.</p><div class="sheet-actions"><button class="app-btn primary" data-action="share">${icon('share')} Поделиться</button><button class="app-btn" data-action="close-modal">Закрыть</button></div></div></div>`); }
function render() { const routes = { home: () => screens.home({ user }), stats: screens.stats, promotion: screens.promotion, partners: screens.partners, agents: screens.agents, banners: screens.banners, contact: () => screens.lookup({ block: false }), blacklist: () => screens.lookup({ block: true }), support: screens.support, faq: screens.faq, ticket: screens.ticket, profile: () => screens.profile({ user }), 'agent-application': () => screens.application('agent'), 'partner-application': () => screens.application('partner') }; renderHeader(); content.innerHTML = (routes[state.view] || routes.home)(); renderNav(); if (supportsBackButton) { if (state.view === 'home') tg.BackButton.hide(); else tg.BackButton.show(); } }
function go(view) { state.view = view; if (supportsHaptics) tg.HapticFeedback.impactOccurred('light'); render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }

document.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]'); if (nav) return go(nav.dataset.nav);
  const faq = event.target.closest('.faq-question'); if (faq) return faq.parentElement.classList.toggle('open');
  const action = event.target.closest('[data-action]')?.dataset.action; if (!action) return;
  if (action === 'open-qr') return renderModal();
  if (action === 'close-modal') return document.querySelector('#modalLayer')?.remove();
  if (action === 'copy') { try { await navigator.clipboard.writeText(''); message('Ссылка станет доступна после одобрения профиля'); } catch { message('Копирование недоступно в этом клиенте Telegram'); } return; }
  if (action === 'share') { if (supportsHaptics) tg.HapticFeedback.impactOccurred('medium'); message('Ссылка станет доступна после одобрения профиля'); return; }
  if (action === 'material') return message('Материал будет доступен после публикации администратором');
  if (action === 'support') return message('Контакт поддержки будет добавлен администратором');
});
document.addEventListener('input', (event) => { if (event.target.id !== 'faqSearch') return; const query = event.target.value.trim().toLowerCase(); document.querySelectorAll('[data-faq]').forEach((row) => { row.hidden = Boolean(query && !row.dataset.faq.includes(query)); }); });
document.addEventListener('submit', (event) => { const type = event.target.dataset.form; if (!type) return; event.preventDefault(); const button = event.target.querySelector('[type="submit"]'); button.disabled = true; button.textContent = 'Отправляем…'; setTimeout(() => { button.disabled = false; if (type === 'lookup') { const result = document.querySelector('#lookupResult'); result.className = 'result-card show'; result.innerHTML = '<b>Проверка подготовлена</b><p>Результат появится после подключения серверного поиска.</p>'; } else { message(type === 'ticket' ? 'Обращение подготовлено' : 'Заявка подготовлена'); go('profile'); } }, 350); });
if (supportsBackButton) tg.BackButton.onClick(() => go('home'));
render();
