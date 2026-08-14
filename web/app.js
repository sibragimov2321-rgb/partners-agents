const tg = window.Telegram?.WebApp;
tg?.ready(); tg?.expand();

const $ = (selector) => document.querySelector(selector);
const content = $('#content');
const header = $('#header');
const bottomNav = $('#bottomNav');
const toast = $('#toast');
const telegramUser = tg?.initDataUnsafe?.user || null; // UI display only. Server-side verification remains unchanged.
const state = { view: 'home', filter: 'All', faq: 'partner', search: '' };

const icon = (name) => ({
  home: '<svg viewBox="0 0 24 24"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path d="M9 21v-6h6v6"/></svg>',
  agents: '<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/></svg>',
  partners: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3.5 20v-1.5A4.5 4.5 0 0 1 8 14h2a4.5 4.5 0 0 1 4.5 4.5V20M16 5.5a3 3 0 0 1 0 5.7M18 14a4.5 4.5 0 0 1 2.5 4V20"/></svg>',
  banners: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-4.5-4.5L7 20"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="m20 20-4.2-4.2"/></svg>',
  shield: '<svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6Z"/><path d="m9 12 2 2 4-4"/></svg>',
  faq: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.2 1.8c-.9.8-1.8 1.3-1.8 2.7M12 16.8h.01"/></svg>',
  support: '<svg viewBox="0 0 24 24"><path d="M20 14a4 4 0 0 1-4 4H9l-5 3v-7a4 4 0 0 1-1-2.7V8a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4Z"/><path d="M8 10h8M8 13h5"/></svg>',
  profile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
  stats: '<svg viewBox="0 0 24 24"><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg>',
  link: '<svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.2-1.2"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/></svg>',
  telegram: '<svg viewBox="0 0 24 24"><path d="m21 4-3.1 15.2c-.2 1.1-.8 1.4-1.6.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1L17.6 5.7c.4-.4-.1-.6-.6-.3l-11.5 7.2-5-1.6c-1.1-.3-1.1-1.1.2-1.6L20.1 2c.9-.3 1.7.2.9 2Z"/></svg>',
  ticket: '<svg viewBox="0 0 24 24"><path d="M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4Z"/><path d="M13 5v14"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"/></svg>',
  warning: '<svg viewBox="0 0 24 24"><path d="M12 3 2.5 20h19Z"/><path d="M12 9v4M12 17h.01"/></svg>',
  lock: '<svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
}[name] || '');

function esc(value) { const item = document.createElement('span'); item.textContent = value || ''; return item.innerHTML; }
function username() { return telegramUser?.first_name || telegramUser?.username || 'Гость'; }
function avatar(className = 'avatar') { return telegramUser?.photo_url ? `<img class="${className}" src="${esc(telegramUser.photo_url)}" alt="Профиль">` : `<span class="${className}">${esc(username().slice(0, 1).toUpperCase())}</span>`; }
function notice(text) { toast.textContent = text; toast.classList.add('show'); clearTimeout(notice.timer); notice.timer = setTimeout(() => toast.classList.remove('show'), 2200); }
function haptic() { tg?.HapticFeedback?.impactOccurred('light'); }
function screenHead(title, subtitle) { return `<div class="screen-head"><button class="back-button" type="button" data-nav="home" aria-label="Назад">${icon('back')}</button><div><h2>${title}</h2><p class="subheading">${subtitle}</p></div></div>`; }
function empty(title, text, name = 'stats') { return `<div class="empty-state">${icon(name)}<h3>${title}</h3><p>${text}</p></div>`; }
function panel(title, tag, body, actions = '') { return `<article class="event-card"><div class="event-title"><b>${title}</b>${tag ? `<span>${tag}</span>` : ''}</div>${body}${actions ? `<div class="card-actions" style="padding:0 10px 10px;margin-top:0">${actions}</div>` : ''}</article>`; }
function statsCells(entries) { return `<div class="event-body">${entries.map(([label, value]) => `<div class="event-cell"><small>${label}</small><strong class="${value === 'Нет данных' ? 'empty' : ''}">${value}</strong></div>`).join('')}</div>`; }

function renderHeader() {
  header.innerHTML = `<button class="brand" type="button" data-nav="home" aria-label="Главная"><span class="brand-mark">P</span><span class="brand-copy">PARTNERS<small>PORTAL</small></span></button><div class="header-right"><span class="header-balance"><i></i>${telegramUser ? 'ONLINE' : 'GUEST'}</span><button class="header-profile" type="button" data-nav="profile" aria-label="Профиль">${avatar()}<i class="notice"></i></button></div>`;
  header.insertAdjacentHTML('afterend', `<nav class="section-menu" aria-label="Разделы">${[['home','Главная'],['partners','Партнёры'],['agents','Агенты'],['banners','Баннеры'],['faq','FAQ'],['support','Поддержка']].map(([view,label]) => `<button class="section-link ${state.view === view ? 'active' : ''}" data-nav="${view}" type="button">${label}</button>`).join('')}</nav>`);
}
function renderBottomNav() {
  const nav = [['home','Главная','home'],['partners','Партнёры','partners'],['agents','Агенты','agents'],['support','Поддержка','support'],['profile','Профиль','profile']];
  bottomNav.innerHTML = nav.map(([view,label,name]) => `<button class="nav-item ${state.view === view ? 'active' : ''}" type="button" data-nav="${view}">${icon(name)}<span>${label}</span></button>`).join('');
}

function homeView() {
  const quick = [['partners','Партнёры'],['agents','Агенты'],['banners','Баннеры'],['check','Проверка']];
  return `<div class="view"><section class="promo"><span class="promo-tag">Partners programme</span><h1>Управляйте программой в Telegram</h1><p>Заявки, проверка контактов, материалы и помощь команды.</p><button class="button primary" type="button" data-nav="partners">Открыть ${icon('arrow')}</button></section><div class="quick-grid">${quick.map(([view,label]) => `<button class="quick-button" type="button" data-nav="${view}">${icon(view === 'check' ? 'search' : view)}<span>${label}</span></button>`).join('')}</div><div class="section-head"><h2>Рабочая панель</h2><button class="link-button" type="button" data-nav="stats">Статистика</button></div><div class="dashboard-list">${panel('Партнёрская программа','Профиль',statsCells([['Affiliate ID','Нет данных'],['Статус','Ожидает заявки']]),'<button class="button blue" type="button" data-nav="partners">Партнёры</button>')}${panel('Агентская программа','Профиль',statsCells([['Agent ID','Нет данных'],['Статус','Ожидает заявки']]),'<button class="button primary" type="button" data-nav="agents">Стать агентом</button>')}</div><div class="section-head"><h2>Последняя активность</h2><small>Обновления</small></div>${empty('Активности пока нет','Новые заявки, обращения и события появятся здесь.', 'stats')}</div>`;
}
function programView(kind) {
  const agent = kind === 'agents'; const title = agent ? 'Агенты' : 'Партнёры';
  const rows = agent ? [['Agent ID','Нет данных'],['GEO','Нет данных'],['Игроки','Нет данных'],['Доход','Нет данных']] : [['Affiliate ID','Нет данных'],['Трафик','Нет данных'],['Конверсии','Нет данных'],['Доход','Нет данных']];
  return `<div class="view">${screenHead(title, agent ? 'Агентская программа' : 'Партнёрская программа')}${panel(agent ? 'Стать агентом' : 'Стать партнёром','Новая заявка',`<div class="card" style="border:0;border-radius:0;background:#151e2b"><p>${agent ? 'Подайте заявку на подключение и получите доступ к агентскому кабинету после проверки.' : 'Расскажите о GEO и источнике трафика для рассмотрения заявки.'}</p></div>`,`<button class="button ${agent ? 'primary' : 'blue'}" type="button" data-nav="${agent ? 'agent-form' : 'partner-form'}">Заполнить заявку ${icon('arrow')}</button>`)}${panel(agent ? 'Агентский кабинет' : 'Кабинет партнёра','Нет данных',statsCells(rows),`<button class="button" type="button" data-nav="profile">Открыть профиль</button>`)}</div>`;
}
function formView(kind) {
  const agent = kind === 'agent';
  return `<div class="view">${screenHead(agent ? 'Заявка агента' : 'Заявка партнёра','Заполните данные для рассмотрения')}<div class="form-panel"><form class="form" id="applicationForm"><input type="hidden" value="${kind}"><div class="field"><label>Имя</label><input required value="${esc(telegramUser?.first_name || '')}" placeholder="Ваше имя"></div><div class="field"><label>Email</label><input required type="email" placeholder="name@example.com"></div><div class="field"><label>${agent ? 'Страна, город и опыт' : 'GEO и источник трафика'}</label><textarea required placeholder="Кратко расскажите о себе"></textarea></div>${agent ? '' : '<div class="field"><label>Сайт / канал / соцсеть</label><input placeholder="Ссылка, если есть"></div>'}<label class="consent"><input type="checkbox" required><span>Согласен с условиями обработки заявки.</span></label><button class="button primary" type="submit">Отправить заявку ${icon('arrow')}</button></form></div><div class="callout">${icon('lock')}<span><strong>Защищённая форма</strong><br>Сохранение в базе будет работать после подключения API заявок.</span></div></div>`;
}
function statsView() { const metrics = [['Игроки','Нет данных'],['Депозиты','Нет данных'],['Выводы','Нет данных'],['Доход','Нет данных'],['Конверсии','Нет данных'],['Период','Сегодня']]; return `<div class="view">${screenHead('Статистика','Результаты программы')}<div class="filter-row"><button class="filter-chip active">Сегодня</button><button class="filter-chip">7 дней</button><button class="filter-chip">30 дней</button><button class="filter-chip">Всё время</button></div>${panel('Ключевые показатели','Без данных',statsCells(metrics))}${empty('Нет подключённой статистики','Фактические данные появятся здесь после подключения серверного источника.', 'stats')}</div>`; }
function bannersView() {
  const filters = ['All','Telegram','Instagram','Facebook','Stories','Posts']; const list = [['Стартовый баннер','Telegram','1200 × 628'],['Вертикальная история','Stories','1080 × 1920'],['Партнёрская публикация','Posts','1080 × 1080']]; const visible = state.filter === 'All' ? list : list.filter(([,platform]) => platform === state.filter);
  return `<div class="view">${screenHead('Баннеры','Рекламные материалы')}<div class="filter-row">${filters.map(item => `<button class="filter-chip ${state.filter === item ? 'active' : ''}" type="button" data-filter="${item}">${item}</button>`).join('')}</div>${visible.length ? `<div class="banner-row">${visible.map(([title,platform,size]) => `<article class="banner-card"><div class="banner-preview">PARTNERS<br>CAMPAIGN</div><div class="banner-content"><h3>${title}</h3><p>Временный preview — заменяется материалом из админки.</p><div class="card-meta"><span class="chip blue">${platform}</span><span class="chip">GLOBAL</span><span class="chip">${size}</span></div><div class="card-actions"><button class="button" data-toast="Предпросмотр станет доступен после загрузки файла">Открыть</button><button class="button primary" data-copy="Partners Portal — рекламный текст">${icon('copy')}</button></div></div></article>`).join('')}</div>` : empty('Материалов нет','В этой категории пока нет баннеров.', 'banners')}</div>`;
}
function lookupView(blocked = false) { const title = blocked ? 'Заблокированный контакт' : 'Проверить контакт'; return `<div class="view">${screenHead(title, blocked ? 'Проверка по блок-листу' : 'Проверка @username или email')}<div class="form-panel"><form class="form" id="lookupForm" data-kind="${blocked ? 'blocked' : 'contact'}"><div class="field"><label>Контакт</label><div class="field-wrap"><span class="input-icon">${icon(blocked ? 'shield' : 'search')}</span><input id="lookup" required placeholder="@username, email или ID"></div></div><button class="button blue" type="submit">Проверить ${icon('search')}</button></form><div id="lookupResult" class="result-card"></div></div><div class="callout">${icon('lock')}<span><strong>Конфиденциальная проверка</strong><br>Детали других пользователей доступны только администратору.</span></div></div>`; }
const faq = { partner: [['Какие виды трафика разрешены?','Условия по источникам трафика определяются программой. За точной информацией обратитесь в поддержку.'],['Как часто обновляется статистика?','Показатели появятся автоматически после подключения источника статистики.'],['Когда происходят выплаты?','График выплат доступен одобренным участникам в личном кабинете.']], agent: [['Как стать агентом?','Откройте форму в разделе «Агенты», заполните данные и дождитесь решения команды.'],['Как получить материалы?','Перейдите в раздел «Баннеры». Актуальные материалы добавляются администратором.'],['Как связаться с менеджером?','Откройте «Поддержку» и создайте обращение.']] };
function faqView() { const rows = faq[state.faq].filter(([question]) => question.toLowerCase().includes(state.search.toLowerCase())); return `<div class="view">${screenHead('FAQ','Вопросы и ответы')}<div class="tabs"><button class="tab ${state.faq === 'partner' ? 'active' : ''}" data-faq="partner">Для партнёров</button><button class="tab ${state.faq === 'agent' ? 'active' : ''}" data-faq="agent">Для агентов</button></div><div class="field-wrap"><span class="input-icon">${icon('search')}</span><input id="faqSearch" value="${esc(state.search)}" placeholder="Поиск по вопросам"></div><div class="accordion">${rows.length ? rows.map(([q,a]) => `<article class="faq-item"><button class="faq-question" type="button"><span>${q}</span><i class="chevron">›</i></button><div class="faq-answer">${a}</div></article>`).join('') : empty('Ничего не найдено','Измените поисковый запрос.', 'search')}</div></div>`; }
function supportView() { const item = (name, text, iconName, nav, toastText) => `<button class="support-card" type="button" ${nav ? `data-nav="${nav}"` : `data-toast="${toastText}"`}><span class="support-icon">${icon(iconName)}</span><span class="support-copy"><strong>${name}</strong><small>${text}</small></span><span class="chevron">›</span></button>`; return `<div class="view">${screenHead('Поддержка','Связь с командой')}<div class="support-grid">${item('Telegram support','Быстрая связь с командой','telegram',null,'Support username ещё не настроен')}${item('Написать менеджеру','Помощь по заявке и доступам','support',null,'Менеджер будет назначен после заявки')}${item('Вопросы и ответы','Ответы на частые вопросы','faq','faq')}${item('Создать обращение','Описать вопрос для команды','ticket','ticket')}</div><div class="callout">${icon('support')}<span><strong>Статус обращений</strong><br>После подключения API обращения будут отображаться в приложении.</span></div></div>`; }
function ticketView() { return `<div class="view">${screenHead('Новое обращение','Поддержка')}<div class="form-panel"><form class="form" id="ticketForm"><div class="field"><label>Тема</label><input required placeholder="Например: вопрос по регистрации"></div><div class="field"><label>Категория</label><select><option>Общий вопрос</option><option>Заявка</option><option>Материалы</option><option>Техническая проблема</option></select></div><div class="field"><label>Сообщение</label><textarea required placeholder="Опишите вопрос"></textarea></div><button class="button primary" type="submit">Создать обращение ${icon('arrow')}</button></form></div></div>`; }
function profileView() { const login = telegramUser?.username ? `@${telegramUser.username}` : 'Username не указан'; return `<div class="view">${screenHead('Личный кабинет','Профиль пользователя')}<article class="card"><div class="profile-top">${avatar()}<div><h3>${esc(username())}</h3><p>${esc(login)}<br>Telegram ID: ${esc(String(telegramUser?.id || 'доступен в Telegram'))}</p></div></div><div class="card-meta"><span class="chip yellow">Гость</span><span class="chip">Ожидает регистрации</span></div></article>${panel('Доступ к программе','Нет данных',statsCells([['Agent / Affiliate ID','Нет данных'],['GEO','Нет данных'],['Промокод','Нет данных'],['Персональная ссылка','Нет данных']]),'<button class="button blue" data-nav="partners">Подать заявку</button>')}</div>`; }

function render() {
  document.querySelector('.section-menu')?.remove(); renderHeader();
  const views = { home: homeView, agents: () => programView('agents'), partners: () => programView('partners'), 'agent-form': () => formView('agent'), 'partner-form': () => formView('partner'), stats: statsView, banners: bannersView, check: () => lookupView(), blocked: () => lookupView(true), faq: faqView, support: supportView, ticket: ticketView, profile: profileView };
  content.innerHTML = (views[state.view] || homeView)(); renderBottomNav();
  if (state.view === 'home') tg?.BackButton?.hide(); else tg?.BackButton?.show();
}
function navigate(view) { haptic(); state.view = view; render(); window.scrollTo({top:0,behavior:'smooth'}); }
document.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]'); if (nav) { navigate(nav.dataset.nav); return; }
  const filter = event.target.closest('[data-filter]'); if (filter) { state.filter = filter.dataset.filter; render(); return; }
  const tab = event.target.closest('[data-faq]'); if (tab) { state.faq = tab.dataset.faq; render(); return; }
  const faqButton = event.target.closest('.faq-question'); if (faqButton) { faqButton.closest('.faq-item').classList.toggle('open'); return; }
  const copy = event.target.closest('[data-copy]'); if (copy) { try { await navigator.clipboard.writeText(copy.dataset.copy); notice('Рекламный текст скопирован'); } catch { notice('Не удалось скопировать текст'); } return; }
  const toastButton = event.target.closest('[data-toast]'); if (toastButton) notice(toastButton.dataset.toast);
});
document.addEventListener('input', (event) => { if (event.target.id === 'faqSearch') { state.search = event.target.value; const pos = event.target.selectionStart; render(); $('#faqSearch')?.focus(); $('#faqSearch')?.setSelectionRange(pos,pos); } });
document.addEventListener('submit', (event) => {
  if (event.target.id === 'applicationForm' || event.target.id === 'ticketForm') { event.preventDefault(); const button = event.target.querySelector('button[type="submit"]'); button.disabled = true; button.textContent = 'Отправляем…'; setTimeout(() => { notice('Форма готова. Для сохранения подключите API на сервере.'); navigate('home'); }, 550); }
  if (event.target.id === 'lookupForm') { event.preventDefault(); const result = $('#lookupResult'); result.className = 'result-card show'; result.innerHTML = `<h3>Проверяем контакт…</h3><p>Запрос обрабатывается защищённо.</p>`; setTimeout(() => { result.className = 'result-card show error'; result.innerHTML = `<h3>Проверка пока недоступна</h3><p>Подключите API контактов или блок-листа на сервере для фактического результата.</p>`; }, 620); }
});
tg?.BackButton?.onClick(() => navigate('home'));
render();
