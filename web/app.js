const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const $ = (selector) => document.querySelector(selector);
const content = $('#content');
const header = $('#header');
const bottomNav = $('#bottomNav');
const toast = $('#toast');
const telegramUser = tg?.initDataUnsafe?.user || null; // Display only. Backend must validate initData before authorization.
const state = { view: 'home', faqAudience: 'partner', faqSearch: '', bannerFilter: 'All' };

const icons = {
  home: '<svg viewBox="0 0 24 24"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path d="M9 21v-6h6v6"/></svg>',
  agents: '<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/></svg>',
  partners: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3.5 20v-1.5A4.5 4.5 0 0 1 8 14h2a4.5 4.5 0 0 1 4.5 4.5V20M16 5.5a3 3 0 0 1 0 5.7M18 14a4.5 4.5 0 0 1 2.5 4V20"/></svg>',
  banners: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-4.5-4.5L7 20"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="m20 20-4.2-4.2"/></svg>',
  shield: '<svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6Z"/><path d="m9 12 2 2 4-4"/></svg>',
  faq: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.2 1.8c-.9.8-1.8 1.3-1.8 2.7M12 16.8h.01"/></svg>',
  support: '<svg viewBox="0 0 24 24"><path d="M20 14a4 4 0 0 1-4 4H9l-5 3v-7a4 4 0 0 1-1-2.7V8a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4Z"/><path d="M8 10h8M8 13h5"/></svg>',
  profile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
  chart: '<svg viewBox="0 0 24 24"><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg>',
  link: '<svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.2-1.2"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/></svg>',
  telegram: '<svg viewBox="0 0 24 24"><path d="m21 4-3.1 15.2c-.2 1.1-.8 1.4-1.6.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1L17.6 5.7c.4-.4-.1-.6-.6-.3l-11.5 7.2-5-1.6c-1.1-.3-1.1-1.1.2-1.6L20.1 2c.9-.3 1.7.2.9 2Z"/></svg>',
  mail: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
  ticket: '<svg viewBox="0 0 24 24"><path d="M4 5h16v5a2 2 0 0 0 0 4v5H4v-5a2 2 0 0 0 0-4Z"/><path d="M13 5v14"/></svg>',
  bell: '<svg viewBox="0 0 24 24"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"/></svg>',
  warning: '<svg viewBox="0 0 24 24"><path d="M12 3 2.5 20h19Z"/><path d="M12 9v4M12 17h.01"/></svg>',
  lock: '<svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
};

const menuItems = [
  ['agents', 'Агенты', 'Заявка и агентский кабинет'],
  ['partners', 'Партнёры', 'Партнёрская программа и трафик'],
  ['banners', 'Получить баннер', 'Рекламные материалы и тексты'],
  ['check', 'Проверить контакт', 'Проверка @username или email'],
  ['blocked', 'Заблокированный контакт', 'Проверка по блок-листу'],
  ['faq', 'Вопросы и ответы', 'Правила и частые вопросы'],
  ['support', 'Поддержка', 'Связаться с командой'],
  ['profile', 'Личный кабинет', 'Ваш профиль и статус'],
];

const navItems = [
  ['home', 'Главная', 'home'], ['agents', 'Агенты', 'agents'], ['stats', 'Статистика', 'chart'], ['support', 'Поддержка', 'support'], ['profile', 'Профиль', 'profile'],
];

function icon(name) { return icons[name] || icons.home; }
function haptic(type = 'light') { tg?.HapticFeedback?.impactOccurred(type); }
function notification(message) { toast.textContent = message; toast.classList.add('show'); window.clearTimeout(notification.timer); notification.timer = window.setTimeout(() => toast.classList.remove('show'), 2600); }
function firstLetter(value) { return (value || 'P').trim().charAt(0).toUpperCase(); }
function userName() { return telegramUser?.first_name || telegramUser?.username || 'Гость'; }
function avatarHtml(className = 'avatar') { return telegramUser?.photo_url ? `<img class="${className}" src="${escapeHtml(telegramUser.photo_url)}" alt="Аватар">` : `<span class="${className}">${firstLetter(userName())}</span>`; }
function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value || ''; return div.innerHTML; }

function applyTelegramTheme() {
  const p = tg?.themeParams || {};
  if (p.bg_color) document.documentElement.style.setProperty('--tg-bg', p.bg_color);
  if (p.text_color) document.documentElement.style.setProperty('--tg-text', p.text_color);
}

function renderHeader() {
  header.innerHTML = `<button class="brand" type="button" data-nav="home" aria-label="Главная"><span class="brand-mark">P</span><span class="brand-copy">PARTNERS<small>PORTAL</small></span></button><div class="header-right"><span class="online">в сети</span><button class="header-profile" type="button" data-nav="profile" aria-label="Профиль">${avatarHtml()}<i class="notice"></i></button></div>`;
}
function renderBottomNav() {
  bottomNav.innerHTML = navItems.map(([view, label, iconName]) => `<button class="nav-item ${state.view === view ? 'active' : ''}" type="button" data-nav="${view}">${icon(iconName)}<span>${label}</span></button>`).join('');
}
function screenHeader(title, subtitle) { return `<div class="screen-head"><button class="back-button" type="button" data-nav="home" aria-label="Назад">${icon('back')}</button><div><h2>${title}</h2>${subtitle ? `<p class="subheading">${subtitle}</p>` : ''}</div></div>`; }
function emptyState(title, text, iconName = 'chart') { return `<div class="empty-state"><span class="round-icon">${icon(iconName)}</span><h3>${title}</h3><p>${text}</p></div>`; }
function card(title, text, iconName, action, primary = false) { return `<article class="card"><div class="card-row"><span class="round-icon">${icon(iconName)}</span><span class="chip">доступно в портале</span></div><h3 style="margin-top:14px">${title}</h3><p class="muted">${text}</p>${action ? `<div class="card-actions"><button class="button ${primary ? 'primary' : 'ghost'}" type="button" data-nav="${action}">Открыть ${icon('arrow')}</button></div>` : ''}</article>`; }

function homeView() {
  return `<div class="view"><section class="hero"><div class="hero-top"><p class="eyebrow">Partners Portal</p><span class="status-chip">${telegramUser ? 'Telegram подключён' : 'Гостевой доступ'}</span></div><h1>Партнёрская программа в одном приложении</h1><p>Заявки, материалы, проверка контактов и поддержка — безопасно внутри Telegram.</p><div class="hero-actions"><button class="button primary" type="button" data-nav="agents">Начать работу ${icon('arrow')}</button><button class="button ghost" type="button" data-nav="profile">Мой профиль</button></div></section><div class="section-head"><h2>Разделы</h2><button class="link-button" type="button" data-nav="stats">Статистика</button></div><div class="menu-grid">${menuItems.map(([key, title, subtitle]) => `<button class="menu-card" type="button" data-nav="${key}"><span class="menu-icon">${icon(key === 'check' ? 'search' : key === 'blocked' ? 'shield' : key)}</span><span class="menu-copy"><strong>${title}</strong><small>${subtitle}</small></span><span class="chevron">›</span></button>`).join('')}</div></div>`;
}

function agentsView() {
  return `<div class="view">${screenHeader('Агенты', 'Работа с агентской программой')}<div class="callout"><span class="round-icon">${icon('agents')}</span><div><strong>Ваш кабинет будет доступен после одобрения</strong><br><small>Данные агента появляются только после регистрации и проверки заявки.</small></div></div>${card('Стать агентом', 'Оставьте заявку на подключение. Команда рассмотрит её и свяжется с вами в Telegram.', 'agents', 'agent-form', true)}${card('Я уже агент', 'Проверьте состояние профиля, Agent ID и доступные материалы.', 'profile', 'profile')}</div>`;
}
function partnersView() {
  return `<div class="view">${screenHeader('Партнёры', 'Партнёрская программа и трафик')}<div class="callout"><span class="round-icon">${icon('partners')}</span><div><strong>Профиль партнёра создаётся после одобрения</strong><br><small>Affiliate ID, ссылки и статистика появятся в личном кабинете.</small></div></div>${card('Стать партнёром', 'Расскажите о GEO, источнике трафика и предполагаемом объёме.', 'partners', 'partner-form', true)}${card('Я уже партнёр', 'Перейдите в профиль, чтобы увидеть доступный статус аккаунта.', 'profile', 'profile')}</div>`;
}
function applicationForm(kind) {
  const agent = kind === 'agent';
  const title = agent ? 'Заявка агента' : 'Заявка партнёра';
  const extra = agent ? `<div class="field"><label>Страна и город</label><input required name="geo" placeholder="Например: Казахстан, Алматы"></div><div class="field"><label>Опыт работы</label><textarea name="experience" placeholder="Кратко расскажите об опыте"></textarea></div>` : `<div class="field"><label>GEO и источник трафика</label><input required name="geo" placeholder="Например: KZ — Telegram, Instagram"></div><div class="field"><label>Сайт / канал / соцсеть</label><input name="channel" placeholder="Ссылка, если есть"></div>`;
  return `<div class="view">${screenHeader(title, 'Заполните форму для рассмотрения')}<form id="applicationForm" class="form" data-kind="${kind}"><div class="field"><label>Ваше имя</label><input required name="name" value="${escapeHtml(telegramUser?.first_name || '')}" placeholder="Имя"></div><div class="field"><label>Email</label><input required type="email" name="email" placeholder="name@example.com"></div>${extra}<div class="field"><label>Комментарий</label><textarea name="comment" placeholder="Дополнительная информация"></textarea></div><label class="consent"><input required type="checkbox"><span>Я согласен с условиями обработки заявки.</span></label><button class="button primary" type="submit">Отправить заявку ${icon('arrow')}</button></form><div class="callout"><span class="round-icon">${icon('lock')}</span><div><strong>Данные защищены</strong><br><small>Отправка сохраняется только после подключения API заявок на сервере.</small></div></div></div>`;
}
function statsView() {
  const metrics = [['Игроки', 'agents'], ['Депозиты', 'chart'], ['Выводы', 'arrow'], ['Доход', 'partners'], ['Конверсии', 'check']];
  return `<div class="view">${screenHeader('Статистика', 'Показатели программы')}<div class="tabs"><button class="tab active" type="button">Сегодня</button><button class="tab" type="button">7 дней</button><button class="tab" type="button">30 дней</button><button class="tab" type="button">Всё время</button></div><div class="stats-grid">${metrics.map(([label, iconName]) => `<div class="metric"><span class="round-icon">${icon(iconName)}</span><small>${label}</small><strong>Нет данных</strong></div>`).join('')}</div>${emptyState('Статистика пока недоступна', 'Когда сервер подключит реальные показатели, они появятся здесь автоматически.')}</div>`;
}
function bannersView() {
  const filters = ['All', 'Telegram', 'Instagram', 'Facebook', 'Stories', 'Posts'];
  const samples = [['Telegram — стартовый', 'Telegram', '1200 × 628'], ['Stories — вертикальный', 'Stories', '1080 × 1920'], ['Партнёрская публикация', 'Posts', '1080 × 1080']];
  const visible = state.bannerFilter === 'All' ? samples : samples.filter(([, platform]) => platform === state.bannerFilter);
  return `<div class="view">${screenHeader('Получить баннер', 'Рекламные материалы')}<div class="chips">${filters.map(filter => `<button class="filter-chip ${filter === state.bannerFilter ? 'active' : ''}" type="button" data-filter="${filter}">${filter}</button>`).join('')}</div>${visible.length ? `<div class="banner-grid">${visible.map(([title, platform, size]) => `<article class="banner-card"><div class="banner-preview"><b>PARTNERS<br>CAMPAIGN</b></div><div class="banner-content"><h3>${title}</h3><p>Оригинальный временный макет. Материалы можно заменить через административную часть.</p><div class="banner-meta"><span class="chip">GLOBAL</span><span>${platform}</span><span>${size}</span></div><div class="card-actions"><button class="button ghost" type="button" data-toast="Предпросмотр будет доступен после загрузки материала">Открыть</button><button class="button primary" type="button" data-copy="Partners Portal — рекламный текст">${icon('copy')} Текст</button></div></div></article>`).join('')}</div>` : emptyState('Материалов нет', 'В выбранной категории пока нет доступных баннеров.', 'banners')}</div>`;
}
function checkView(blocked = false) {
  const title = blocked ? 'Заблокированный контакт' : 'Проверить контакт';
  const description = blocked ? 'Введите Telegram, email, Agent ID или Affiliate ID для проверки блок-листа.' : 'Введите @username или email. Личные данные других участников не раскрываются.';
  return `<div class="view">${screenHeader(title, description)}<div class="card"><form id="lookupForm" class="form" data-lookup="${blocked ? 'blocked' : 'contact'}"><div class="field"><label>Контакт</label><div class="field-wrap"><span class="input-icon">${icon(blocked ? 'shield' : 'search')}</span><input id="lookupValue" required placeholder="@username, email или ID"></div></div><button class="button primary" type="submit">Проверить ${icon('search')}</button></form><div id="lookupResult" class="result-card"></div></div><div class="callout"><span class="round-icon">${icon('lock')}</span><div><strong>Конфиденциальная проверка</strong><br><small>Расширенные сведения видны только пользователям с административной ролью.</small></div></div></div>`;
}
const faqData = {
  partner: [['Какие виды трафика разрешены?', 'Допустимые источники и ограничения публикуются администратором программы. Для точного ответа обратитесь в поддержку.'], ['Какие модели сотрудничества доступны?', 'Условия определяются после рассмотрения заявки и доступны в личном кабинете одобренного партнёра.'], ['Как часто обновляется статистика?', 'После подключения статистического API показатели будут обновляться автоматически.'], ['Когда происходят выплаты?', 'График и способы выплат отображаются только в одобренном профиле партнёра.']],
  agent: [['Как стать агентом?', 'Откройте раздел «Агенты», отправьте заявку и дождитесь решения команды.'], ['Как работает агентский кабинет?', 'После одобрения здесь появятся Agent ID, GEO, персональная ссылка и доступные материалы.'], ['Как получить рекламные материалы?', 'Используйте раздел «Получить баннер». Актуальные материалы загружаются администратором.'], ['Как связаться с менеджером?', 'Откройте раздел поддержки и создайте обращение или воспользуйтесь ссылкой на Telegram support.']],
};
function faqView() {
  const questions = faqData[state.faqAudience].filter(([question]) => question.toLowerCase().includes(state.faqSearch.toLowerCase()));
  return `<div class="view">${screenHeader('Вопросы и ответы', 'Найдите ответ за несколько секунд')}<div class="tabs"><button class="tab ${state.faqAudience === 'partner' ? 'active' : ''}" data-faq="partner" type="button">Для партнёров</button><button class="tab ${state.faqAudience === 'agent' ? 'active' : ''}" data-faq="agent" type="button">Для агентов</button></div><div class="field-wrap"><span class="input-icon">${icon('search')}</span><input id="faqSearch" value="${escapeHtml(state.faqSearch)}" placeholder="Поиск по вопросам"></div><div class="accordion">${questions.length ? questions.map(([question, answer]) => `<article class="faq-item"><button class="faq-question" type="button"><span>${question}</span><i class="chevron">›</i></button><div class="faq-answer">${answer}</div></article>`).join('') : emptyState('Ничего не найдено', 'Попробуйте изменить поисковый запрос.', 'search')}</div></div>`;
}
function supportView() {
  return `<div class="view">${screenHeader('Поддержка', 'Команда на связи')}<div class="callout"><span class="round-icon">${icon('support')}</span><div><strong>Нужна помощь?</strong><br><small>Выберите удобный способ связи или создайте обращение.</small></div></div><div class="support-grid"><button class="support-card" type="button" data-toast="Telegram support будет открыт после настройки SUPPORT_USERNAME"><span class="menu-icon">${icon('telegram')}</span><span class="menu-copy"><strong>Telegram support</strong><small>Быстрая связь с командой</small></span><span class="chevron">›</span></button><button class="support-card" type="button" data-toast="Менеджер станет доступен после назначения"><span class="menu-icon">${icon('support')}</span><span class="menu-copy"><strong>Написать менеджеру</strong><small>Персональная помощь по заявке</small></span><span class="chevron">›</span></button><button class="support-card" type="button" data-nav="faq"><span class="menu-icon">${icon('faq')}</span><span class="menu-copy"><strong>Открыть FAQ</strong><small>Ответы на частые вопросы</small></span><span class="chevron">›</span></button><button class="support-card" type="button" data-nav="ticket"><span class="menu-icon">${icon('ticket')}</span><span class="menu-copy"><strong>Создать обращение</strong><small>Опишите вопрос для команды</small></span><span class="chevron">›</span></button></div></div>`;
}
function ticketView() { return `<div class="view">${screenHeader('Новое обращение', 'Ответит назначенный менеджер')}<form id="ticketForm" class="form"><div class="field"><label>Тема</label><input required placeholder="Например: вопрос по регистрации"></div><div class="field"><label>Категория</label><select><option>Общий вопрос</option><option>Заявка</option><option>Материалы</option><option>Техническая проблема</option></select></div><div class="field"><label>Сообщение</label><textarea required placeholder="Опишите вопрос подробнее"></textarea></div><button class="button primary" type="submit">Отправить обращение ${icon('arrow')}</button></form><div class="callout"><span class="round-icon">${icon('lock')}</span><div><strong>Статус обращения</strong><br><small>После подключения серверного API заявки появятся в списке поддержки.</small></div></div></div>`; }
function profileView() { const username = telegramUser?.username ? `@${telegramUser.username}` : 'Username не указан'; const id = telegramUser?.id || 'будет доступен в Telegram'; return `<div class="view">${screenHeader('Личный кабинет', 'Профиль пользователя')}<article class="card profile-card">${avatarHtml()}<div><h3>${escapeHtml(userName())}</h3><p class="muted">${escapeHtml(username)}<br>Telegram ID: ${escapeHtml(String(id))}<br>Роль: гость · Статус: ожидает регистрации</p></div></article><div class="card"><div class="card-row"><h3>Ваш доступ</h3><span class="chip">безопасно</span></div><p class="muted">После одобрения заявки здесь появятся роль, Agent/Affiliate ID, GEO, персональная ссылка, промокод и доступная статистика.</p><div class="card-actions"><button class="button primary" type="button" data-nav="agents">Стать агентом</button><button class="button ghost" type="button" data-nav="partners">Стать партнёром</button></div></div></div>`; }

function render() {
  renderHeader();
  const views = { home: homeView, agents: agentsView, partners: partnersView, 'agent-form': () => applicationForm('agent'), 'partner-form': () => applicationForm('partner'), stats: statsView, banners: bannersView, check: () => checkView(false), blocked: () => checkView(true), faq: faqView, support: supportView, ticket: ticketView, profile: profileView };
  content.innerHTML = (views[state.view] || homeView)();
  renderBottomNav();
  tg?.BackButton?.isVisible && state.view !== 'home' ? tg.BackButton.show() : tg?.BackButton?.hide();
}

function navigate(view) { haptic(); state.view = view; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
document.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]'); if (nav) { navigate(nav.dataset.nav); return; }
  const filter = event.target.closest('[data-filter]'); if (filter) { state.bannerFilter = filter.dataset.filter; render(); return; }
  const faqTab = event.target.closest('[data-faq]'); if (faqTab) { state.faqAudience = faqTab.dataset.faq; render(); return; }
  const faqQuestion = event.target.closest('.faq-question'); if (faqQuestion) { faqQuestion.closest('.faq-item').classList.toggle('open'); haptic('light'); return; }
  const copy = event.target.closest('[data-copy]'); if (copy) { try { await navigator.clipboard.writeText(copy.dataset.copy); notification('Рекламный текст скопирован'); } catch { notification('Не удалось скопировать текст'); } return; }
  const message = event.target.closest('[data-toast]'); if (message) notification(message.dataset.toast);
});
document.addEventListener('input', (event) => { if (event.target.id === 'faqSearch') { state.faqSearch = event.target.value; const caret = event.target.selectionStart; render(); $('#faqSearch')?.focus(); $('#faqSearch')?.setSelectionRange(caret, caret); } });
document.addEventListener('submit', (event) => {
  if (event.target.id === 'applicationForm') { event.preventDefault(); const button = event.target.querySelector('button[type="submit"]'); button.disabled = true; button.textContent = 'Отправляем…'; window.setTimeout(() => { notification('Форма готова. Подключите API заявок для сохранения в базе.'); navigate('home'); }, 650); }
  if (event.target.id === 'ticketForm') { event.preventDefault(); const button = event.target.querySelector('button[type="submit"]'); button.disabled = true; button.textContent = 'Отправляем…'; window.setTimeout(() => { notification('Форма готова. Подключите API обращений для сохранения.'); navigate('support'); }, 650); }
  if (event.target.id === 'lookupForm') { event.preventDefault(); const output = $('#lookupResult'); const blocked = event.target.dataset.lookup === 'blocked'; output.className = 'result-card show'; output.innerHTML = `<span class="round-icon">${icon('search')}</span><h3>Проверяем контакт…</h3><p class="muted">Запрос защищённо обрабатывается сервером.</p>`; window.setTimeout(() => { output.className = 'result-card show error'; output.innerHTML = `<span class="round-icon">${icon('warning')}</span><h3>Проверка пока недоступна</h3><p class="muted">Подключите API ${blocked ? 'блок-листа' : 'контактов'} на сервере, чтобы увидеть фактический результат.</p>`; }, 720); }
});
tg?.BackButton?.onClick(() => navigate('home'));
applyTelegramTheme();
render();
