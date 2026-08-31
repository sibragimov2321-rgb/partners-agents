import { esc, icon, pageHead } from './ui.js?v=20260821-7';

const e = value => esc(value ?? '');
const action = (label, attrs = '', kind = 'primary') => `<button class="app-btn ${kind}" ${attrs}>${label}</button>`;

const countryGroups = [
  ['Основные страны', [['Кыргызстан','🇰🇬'],['Узбекистан','🇺🇿'],['Казахстан','🇰🇿'],['Таджикистан','🇹🇯'],['Туркменистан','🇹🇲'],['Азербайджан','🇦🇿'],['Турция','🇹🇷'],['Россия','🇷🇺']]],
  ['Кавказ и СНГ', [['Армения','🇦🇲'],['Беларусь','🇧🇾'],['Грузия','🇬🇪'],['Молдова','🇲🇩'],['Украина','🇺🇦']]],
  ['Другие страны Азии', [['Афганистан','🇦🇫'],['Бангладеш','🇧🇩'],['Бахрейн','🇧🇭'],['Бруней','🇧🇳'],['Бутан','🇧🇹'],['Вьетнам','🇻🇳'],['Израиль','🇮🇱'],['Индия','🇮🇳'],['Индонезия','🇮🇩'],['Иордания','🇯🇴'],['Ирак','🇮🇶'],['Иран','🇮🇷'],['Йемен','🇾🇪'],['Камбоджа','🇰🇭'],['Катар','🇶🇦'],['Кипр','🇨🇾'],['Китай','🇨🇳'],['Кувейт','🇰🇼'],['Лаос','🇱🇦'],['Ливан','🇱🇧'],['Малайзия','🇲🇾'],['Мальдивы','🇲🇻'],['Монголия','🇲🇳'],['Мьянма','🇲🇲'],['Непал','🇳🇵'],['ОАЭ','🇦🇪'],['Оман','🇴🇲'],['Пакистан','🇵🇰'],['Палестина','🇵🇸'],['Саудовская Аравия','🇸🇦'],['Сингапур','🇸🇬'],['Сирия','🇸🇾'],['Таиланд','🇹🇭'],['Тимор-Лесте','🇹🇱'],['Филиппины','🇵🇭'],['Шри-Ланка','🇱🇰'],['Южная Корея','🇰🇷'],['Япония','🇯🇵']]],
];
const countryNames = new Set(countryGroups.flatMap(([, countries]) => countries.map(([name]) => name)));

const statusCopy = {
  draft: ['Черновик', 'Продолжите заполнение анкеты.'],
  submitted: ['Заявка отправлена', 'Заявка ожидает начала проверки менеджером.'],
  under_review: ['На проверке', 'Менеджер проверяет предоставленные данные.'],
  need_information: ['Нужна информация', 'Откройте заявку и учтите комментарий менеджера.'],
  pre_approved: ['Предварительно одобрено', 'Менеджер готовит следующий этап регистрации.'],
  waiting_deposit: ['Ожидается депозит', 'Внесите стартовый депозит согласно условиям вашего GEO.'],
  waiting_documents: ['Ожидаются документы', 'Загрузите документы только на этом защищённом этапе.'],
  final_review: ['Финальная проверка', 'Менеджер проверяет документы перед активацией.'],
  approved: ['Агент подтверждён', 'Рабочий профиль агента активирован.'],
  rejected: ['Заявка отклонена', 'Причина указана в комментарии менеджера.'],
};

function countryControl(value = '', geoSettings = []) {
  const known = countryNames.has(value);
  const selected = known ? value : value ? '__other__' : '';
  const settings = new Map(geoSettings.map(item => [item.country, item]));
  const groups = countryGroups.map(([label, countries]) => `<optgroup label="${label}">${countries.map(([name, flag]) => {
    const setting = settings.get(name);
    return `<option value="${name}" data-geo="${e(setting?.geo_code)}" data-deposit="${e(setting?.minimum_deposit)}" data-currency="${e(setting?.currency)}" ${selected === name ? 'selected' : ''}>${flag} ${name}</option>`;
  }).join('')}</optgroup>`).join('');
  return `<label class="field"><span>Страна *</span><select name="country" required><option value="">Выберите страну</option>${groups}<option value="__other__" ${selected === '__other__' ? 'selected' : ''}>🌍 Другая страна</option></select></label>
    <label class="field country-other" ${selected === '__other__' ? '' : 'hidden'}><span>Название страны *</span><input name="country_other" value="${selected === '__other__' ? e(value) : ''}" ${selected === '__other__' ? 'required' : ''} placeholder="Введите страну"></label>
    <div class="geo-condition" data-geo-condition hidden></div>`;
}

function infoScreen(hasApplication = false) {
  const registrationAction = hasApplication ? 'data-show-application' : 'data-start-registration';
  const programBenefits = [
    ['briefcase', 'Агентский аккаунт'], ['bolt', 'Личный промокод'],
    ['wallet', '8% с пополнений'], ['chart', '2% с выводов'],
    ['message', 'Telegram-боты'], ['users', 'Рабочие инструменты'],
    ['shield', 'Личный Agent ID'], ['user', 'Поддержка менеджера'],
    ['chart', 'Статистика работы'], ['check', 'Статус проверенного агента'],
  ];
  const steps = [
    ['Создайте аккаунт', 'Зарегистрируйтесь и заполните основные данные.'],
    ['Заполните заявку', 'Укажите контакты, страну, город и информацию о планируемой работе.'],
    ['Пройдите проверку', 'Менеджер проверит предоставленную информацию.'],
    ['Внесите стартовый депозит', 'После предварительного одобрения внесите сумму согласно условиям вашего GEO.'],
    ['Подтвердите личность', 'Предоставьте документы только на открытом менеджером этапе.'],
    ['Получите статус агента', 'Получите Agent ID, промокод и доступ к агентским инструментам.'],
  ];
  const prepare = ['Имя и фамилия','Страна','Город','Telegram','Номер телефона','Email','Место работы','Название кассы / точки','Информация об опыте','Документы — на этапе проверки'];
  return `<div class="view onboarding-view agent-intro-view">
    ${pageHead('Стать агентом', 'Возможности и регистрация')}
    <section class="agent-intro-hero sales-section"><div class="intro-orbit" aria-hidden="true"><i></i><b>PA</b></div><span>PARTNERS AGENT NETWORK</span><h1>Станьте <em>агентом</em></h1><p>Работайте с игроками, получайте доход с операций и развивайте собственную базу игроков вместе с Partners Agent.</p><div class="hero-actions">${action(hasApplication ? 'Моя заявка' : 'Стать агентом', registrationAction)}${action('Как это работает','data-scroll-to="agent-process"','secondary')}</div></section>

    <section class="sales-section rewards-section"><div class="section-title"><span>ВАШИ ВОЗМОЖНОСТИ</span><h2>Что вы получаете как агент</h2></div><p class="section-lead">После подтверждения агент получает инструменты для работы с игроками и возможность зарабатывать на их операциях.</p><div class="rate-grid"><article class="rate-card deposit-rate"><strong>8%</strong><span>С депозитов игроков</span><p>Получайте 8% за операции пополнения средств игроков, которые проходят через вас.</p></article><article class="rate-card withdraw-rate"><strong>2%</strong><span>С выводов игроков</span><p>Получайте 2% за операции вывода средств игроков, которые обслуживаются через вас.</p></article></div></section>

    <section class="promo-card sales-section"><i>${icon('bolt')}</i><div><span>ПЕРСОНАЛЬНЫЙ ИНСТРУМЕНТ</span><h2>Личный промокод</h2><p>После активации агент получает персональный промокод для привлечения и регистрации своих игроков.</p><div class="promo-demo"><code>YOURCODE</code><button type="button" disabled aria-label="Демонстрация копирования">${icon('copy')}</button></div><small>Демонстрационный код. Настоящий промокод появится после активации.</small></div></section>

    <section class="tools-card sales-section"><div class="tools-visual"><i>${icon('message')}</i><b>BOT</b><span></span></div><div class="section-title"><span>ИНСТРУМЕНТЫ ДЛЯ РАБОТЫ</span><h2>Боты для агентов</h2></div><p>Мы предоставляем готовые Telegram-боты и инструменты, которые помогают работать с игроками и упрощают ежедневную работу агента.</p><div class="tool-tags"><span>${icon('message')} Telegram Bot</span><span>${icon('users')} Работа с игроками</span><span>${icon('wallet')} Пополнение / вывод</span><span>${icon('shield')} Поддержка</span></div></section>

    <section class="teamcash-guide sales-section"><div class="guide-heading"><i>${icon('play')}</i><div><span>ВИДЕОГАЙД · 2:41</span><h2>Как работает приложение TeamCash</h2></div></div><p>Посмотрите инструкцию перед регистрацией. В видео показаны основные разделы приложения и рабочие операции агента.</p><div class="guide-player"><video controls playsinline preload="metadata" poster="/static/assets/guides/teamcash-agent-guide-poster.jpg" aria-label="Гайд по работе с приложением TeamCash"><source src="/static/assets/guides/teamcash-agent-guide.mp4" type="video/mp4">Ваше устройство не поддерживает просмотр видео.</video></div><div class="guide-topics"><span>${icon('wallet')} Баланс и лимиты</span><span>${icon('arrow')} Пополнение и вывод</span><span>${icon('users')} Работа с игроками</span></div><small>Видео открывается прямо внутри Telegram. Автоматическое воспроизведение отключено.</small></section>

    <section class="earnings-section sales-section"><div class="section-title"><span>ПОНЯТНЫЙ РАСЧЁТ</span><h2>Как вы зарабатываете</h2></div><div class="calculation-grid"><article><span>ПОПОЛНЕНИЕ</span><p>Игрок пополняет</p><b>$1 000</b><div><small>Доход агента</small><strong>8% = $80</strong></div></article><article><span>ВЫВОД</span><p>Игрок выводит</p><b>$1 000</b><div><small>Доход агента</small><strong>2% = $20</strong></div></article></div><p class="income-note">Чем больше операций проходит через агента, тем выше потенциальный доход. Расчёт приведён как пример и не является гарантией заработка.</p></section>

    <section class="program-section sales-section"><div class="section-title"><span>ПОЛНЫЙ НАБОР</span><h2>Агент получает</h2></div><div class="program-benefit-grid">${programBenefits.map(([glyph,title]) => `<article><i>${icon(glyph)}</i><span>${title}</span></article>`).join('')}</div></section>

    <section class="process-card sales-section" id="agent-process"><div class="section-title"><span>6 ШАГОВ</span><h2>Как стать агентом</h2></div><div class="process-timeline numbered">${steps.map(([title,text],index) => `<article><i>${String(index + 1).padStart(2,'0')}</i><div><h3>${title}</h3><p>${text}</p></div></article>`).join('')}</div><p class="geo-note">Размер стартового депозита определяется настройками выбранной страны / GEO и будет показан после предварительного одобрения.</p></section>

    <section class="prepare-card sales-section"><div class="section-title"><span>ПОДГОТОВЬТЕ ЗАРАНЕЕ</span><h2>Что понадобится для регистрации</h2></div><div class="prepare-grid">${prepare.map(item => `<span>${icon('check')} ${item}</span>`).join('')}</div><p class="privacy-note">Документы не нужно загружать сразу — этот этап откроется только после решения менеджера.</p></section>

    <section class="final-agent-cta sales-section"><span>ГОТОВЫ НАЧАТЬ?</span><h2>Готовы стать агентом?</h2><p>Подайте заявку и пройдите проверку, чтобы получить доступ к агентской программе Partners Agent.</p>${action(hasApplication ? 'Посмотреть мою заявку' : 'Начать регистрацию', registrationAction)}${action('Связаться с менеджером','data-nav="support"','secondary')}</section>
  </div>`;
}

function wizardProgress(step) {
  return `<div class="wizard-heading"><div><span>ШАГ ${step + 1} ИЗ 6</span><b>${Math.round(((step + 1) / 6) * 100)}%</b></div><div class="wizard-track"><i style="width:${((step + 1) / 6) * 100}%"></i></div></div>`;
}

function field(label, name, value, type = 'text', placeholder = '', required = true) {
  return `<label class="field"><span>${label}${required ? ' *' : ''}</span><input type="${type}" name="${name}" ${required ? 'required' : ''} value="${e(value)}" placeholder="${placeholder}"></label>`;
}

function wizard(application = {}, step = 0, geoSettings = [], telegram = {}) {
  const screen = Math.max(0, Math.min(4, Number(step) || 0));
  const data = application || {};
  let body = '';
  if (screen === 0) {
    body = `<form class="flow-card wizard-card" data-form="agent-draft" data-next="1"><div class="form-kicker">ОСНОВНАЯ ИНФОРМАЦИЯ</div><h2>Расскажите, кто вы и где будете работать</h2><div class="field-split">${field('Имя','first_name',data.first_name || telegram.first_name,'text','Ваше имя')}${field('Фамилия','last_name',data.last_name || telegram.last_name,'text','Ваша фамилия')}</div>${countryControl(data.country, geoSettings)}${field('Город','city',data.city,'text','Город')}<div class="flow-actions single">${action('Далее','type="submit"')}</div></form>`;
  } else if (screen === 1) {
    body = `<form class="flow-card wizard-card" data-form="agent-draft" data-next="2"><div class="form-kicker">КОНТАКТЫ</div><h2>Как с вами связаться</h2>${field('Номер телефона','phone',data.phone,'tel','+996 700 000 000')}${field('Telegram','telegram_username',data.telegram_username || telegram.username,'text','@username')}${field('E-mail','email',data.email,'email','name@example.com')}<p class="form-help">Используйте международный формат телефона и действующие контакты.</p><div class="flow-actions">${action('Назад','data-agent-step="0"','secondary')}${action('Далее','type="submit"')}</div></form>`;
  } else if (screen === 2) {
    const has = data.has_experience === true ? 'yes' : data.has_experience === false ? 'no' : '';
    body = `<form class="flow-card wizard-card" data-form="agent-draft" data-next="3"><div class="form-kicker">ОПЫТ</div><h2>Расскажите о себе</h2><fieldset class="choice-field"><legend>Есть ли опыт работы агентом / кассиром? *</legend><label><input type="radio" name="has_experience" value="true" ${has === 'yes' ? 'checked' : ''} required><span>Да</span></label><label><input type="radio" name="has_experience" value="false" ${has === 'no' ? 'checked' : ''} required><span>Нет</span></label></fieldset><label class="field experience-details" ${has === 'yes' ? '' : 'hidden'}><span>Предыдущий опыт *</span><textarea name="experience" ${has === 'yes' ? 'required' : ''} placeholder="Коротко расскажите о своей работе">${e(data.experience)}</textarea></label><label class="field"><span>Сколько игроков планируете обслуживать? *</span><select name="planned_players" required><option value="">Выберите вариант</option>${[['up_to_10','До 10'],['10_30','10–30'],['30_100','30–100'],['over_100','Более 100'],['unknown','Пока не знаю']].map(([value,label]) => `<option value="${value}" ${data.planned_players === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label><div class="flow-actions">${action('Назад','data-agent-step="1"','secondary')}${action('Далее','type="submit"')}</div></form>`;
  } else if (screen === 3) {
    body = `<form class="flow-card wizard-card" data-form="agent-draft" data-next="4"><div class="form-kicker">ИНФОРМАЦИЯ О РАБОТЕ</div><h2>Как будет организована работа</h2>${field('Название кассы / точки','cashdesk_name',data.cashdesk_name,'text','Необязательно',false)}${field('Город / регион / адрес работы','location',data.location,'text','Где вы планируете работать?')}<fieldset class="choice-field"><legend>Есть ли физическая точка? *</legend><label><input type="radio" name="physical_point" value="true" ${data.physical_point === true ? 'checked' : ''} required><span>Да</span></label><label><input type="radio" name="physical_point" value="false" ${data.physical_point === false ? 'checked' : ''} required><span>Нет</span></label></fieldset><label class="field"><span>Откуда узнали о программе? *</span><select name="source" required><option value="">Выберите вариант</option>${[['agent','От действующего агента'],['manager','От менеджера'],['telegram','Telegram'],['instagram','Instagram'],['ads','Реклама'],['friends','Знакомые'],['other','Другое']].map(([value,label]) => `<option value="${value}" ${data.source === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label class="field referral-agent" ${data.source === 'agent' ? '' : 'hidden'}><span>Telegram / ID агента *</span><input name="referral_agent" value="${e(data.referral_agent)}" ${data.source === 'agent' ? 'required' : ''} placeholder="@username или Agent ID"></label><label class="field source-other" ${data.source === 'other' ? '' : 'hidden'}><span>Укажите источник *</span><input name="source_other" value="${e(data.source_other)}" ${data.source === 'other' ? 'required' : ''} placeholder="Напишите источник"></label><div class="flow-actions">${action('Назад','data-agent-step="2"','secondary')}${action('Далее','type="submit"')}</div></form>`;
  } else {
    const experience = data.has_experience ? (data.experience || 'Есть опыт') : 'Без опыта';
    body = `<form class="review-form" data-form="agent-submit"><div class="review-grid"><article><header><span>ЛИЧНЫЕ ДАННЫЕ</span><button type="button" data-agent-step="0">Изменить</button></header><dl><dt>Имя</dt><dd>${e([data.first_name,data.last_name].filter(Boolean).join(' '))}</dd><dt>Страна</dt><dd>${e(data.country)}</dd><dt>Город</dt><dd>${e(data.city)}</dd></dl></article><article><header><span>КОНТАКТЫ</span><button type="button" data-agent-step="1">Изменить</button></header><dl><dt>Телефон</dt><dd>${e(data.phone)}</dd><dt>Telegram</dt><dd>@${e(data.telegram_username)}</dd><dt>E-mail</dt><dd>${e(data.email)}</dd></dl></article><article><header><span>ОПЫТ И РАБОТА</span><button type="button" data-agent-step="2">Изменить</button></header><dl><dt>Опыт</dt><dd>${e(experience)}</dd><dt>Игроки</dt><dd>${e(data.planned_players)}</dd><dt>Касса</dt><dd>${e(data.cashdesk_name || 'Не указана')}</dd><dt>Место</dt><dd>${e(data.location)}</dd><dt>Источник</dt><dd>${e(data.source === 'other' ? data.source_other : data.source)}</dd></dl></article></div><label class="truth-consent"><input type="checkbox" name="confirmed_truth" value="true" required><span>${icon('check')} Я подтверждаю, что предоставленная информация является достоверной.</span></label><div class="flow-actions">${action('Назад','data-agent-step="3"','secondary')}${action('Отправить заявку','type="submit"')}</div></form>`;
  }
  return `<div class="view onboarding-view wizard-view">${pageHead('Анкета агента', 'Данные сохраняются после каждого шага')}${wizardProgress(screen)}${notice(application)}${body}</div>`;
}

function notice(application) {
  if (!application?.manager_comment) return '';
  return `<section class="manager-note"><b>Комментарий менеджера</b><p>${e(application.manager_comment)}</p></section>`;
}

function success(application) {
  return `<div class="view onboarding-view">${pageHead('Стать агентом', 'Шаг 6 из 6')}${wizardProgress(5)}<section class="submission-success"><div class="success-ring">${icon('check')}</div><span>ЗАЯВКА ПРИНЯТА</span><h1>Заявка отправлена</h1><p>Ваши данные успешно переданы менеджеру. Статус можно отслеживать в разделе «Моя заявка».</p><div><small>НОМЕР ЗАЯВКИ</small><b>${e(application.application_number)}</b><em>На проверке</em></div></section><div class="flow-actions vertical">${action('Моя заявка','data-show-application')}${action('На главную','data-nav="home"','secondary')}</div></div>`;
}

function applicationTimeline(application) {
  const stageByStatus = {draft:0,submitted:1,under_review:2,need_information:2,pre_approved:2,waiting_deposit:3,waiting_documents:4,final_review:4,approved:5,rejected:2};
  const active = stageByStatus[application.status] ?? 0;
  const labels = ['Регистрация заполнена','Заявка отправлена','Проверка менеджером','Стартовый депозит','Проверка документов','Активация агента'];
  const completed = application.status === 'approved' ? labels.length : active;
  return `<div class="status-timeline">${labels.map((label,index) => `<article class="${index < completed ? 'done' : index === active ? 'active' : ''}"><i>${index < completed ? icon('check') : index + 1}</i><span>${label}</span></article>`).join('')}</div>`;
}

function myApplication(application) {
  const copy = statusCopy[application.status] || statusCopy.under_review;
  return `<div class="view onboarding-view application-view">${pageHead('Моя заявка', application.application_number)}${notice(application)}<section class="application-overview ${application.status}"><div><span>ЗАЯВКА ${e(application.application_number)}</span><h1>${copy[0]}</h1><p>${copy[1]}</p></div><b>${e(copy[0])}</b></section><section class="timeline-card"><div class="form-kicker">ПРОГРЕСС РЕГИСТРАЦИИ</div>${applicationTimeline(application)}</section><section class="application-facts"><article><span>GEO</span><b>${e(application.geo_code || '—')}</b></article><article><span>СТРАНА</span><b>${e(application.country || '—')}</b></article><article><span>МЕНЕДЖЕР</span><b>${application.assigned_manager_id ? `ID ${application.assigned_manager_id}` : 'Назначается'}</b></article><article><span>ОБНОВЛЕНО</span><b>${application.updated_at ? new Date(application.updated_at).toLocaleDateString('ru-RU') : '—'}</b></article></section>${application.status === 'need_information' ? action('Дополнить данные','data-resume-application') : ''}${action('Связаться с менеджером','data-nav="support"','secondary')}</div>`;
}

function deposit(application) {
  const setting = application.geo_setting;
  const amount = setting ? `${setting.minimum_deposit} ${setting.currency}` : 'уточняется менеджером';
  const depositAction = application.deposit_submitted_at
    ? `<section class="review-status compact"><span>🕐</span><h2>Депозит проверяется</h2><p>Менеджер получил подтверждение и проверит его вручную.</p></section>`
    : application.documents?.deposit
      ? action('Я внёс депозит','data-flow-action="deposit"')
      : '<button class="app-btn primary" disabled>Сначала загрузите подтверждение</button>';
  return `<div class="view onboarding-view">${pageHead('Стартовый депозит', application.application_number)}${notice(application)}<section class="deposit-card"><i>${icon('wallet')}</i><span>СЛЕДУЮЩИЙ ЭТАП</span><h1>Заявка предварительно одобрена</h1><p>Минимальная сумма для вашего региона:</p><strong>${e(amount)}</strong><small>${e(application.country || application.geo_code || '')}</small></section><section class="secure-upload"><div><b>Подтверждение депозита</b><small>JPG, PNG или WEBP до 8 МБ. Файл доступен только вам и менеджеру.</small></div>${documentRow('deposit','Чек / подтверждение',application.documents?.deposit)}</section>${depositAction}</div>`;
}

function documents(application) {
  const documentsReady = application.documents?.passport && application.documents?.selfie;
  return `<div class="view onboarding-view">${pageHead('Подтверждение личности', application.application_number)}${notice(application)}<section class="privacy-card">${icon('shield')}<div><b>Защищённая загрузка</b><p>Документы не публикуются и доступны только вам и авторизованному менеджеру.</p></div></section><section class="secure-upload">${documentRow('passport','Фото документа',application.documents?.passport)}${documentRow('selfie','Селфи с документом',application.documents?.selfie)}</section><section class="document-contact-summary"><span>КОНТАКТЫ ДЛЯ ПРОВЕРКИ</span><p>${e(application.phone)} · ${e(application.email)}</p><p>${e(application.cashdesk_name || 'Без названия кассы')} · ${e(application.location)}</p></section>${documentsReady ? action('Отправить документы на проверку','data-flow-action="documents"') : '<button class="app-btn primary" disabled>Загрузите оба изображения</button>'}</div>`;
}

function documentRow(kind, title, uploaded) {
  return `<article class="document-row"><div><b>${title} *</b><small>${uploaded ? 'Файл сохранён' : 'JPG, PNG или WEBP · до 8 МБ'}</small></div><label class="upload-box ${uploaded ? 'uploaded' : ''}"><input type="file" accept="image/jpeg,image/png,image/webp" data-doc-kind="${kind}"><span>${uploaded ? 'Заменить' : 'Загрузить'}</span></label><div class="document-preview" data-preview="${kind}">${uploaded ? `<img data-secure-doc="${kind}" alt="${title}"><button data-delete-doc="${kind}">Удалить</button>` : ''}</div></article>`;
}

function active(application) {
  return `<div class="view onboarding-view">${pageHead('Кабинет агента', 'Аккаунт активирован')}<section class="success-agent"><div class="success-ring">${icon('check')}</div><span>✓ ПРОВЕРЕННЫЙ АГЕНТ</span><h1>Профиль активирован</h1><p>Финальная проверка завершена. Теперь ваш статус можно проверить через официальный сервис.</p><b>${e(application.agent_id || application.application_number)}</b></section><section class="application-facts"><article><span>GEO</span><b>${e(application.geo_code || '—')}</b></article><article><span>ДАТА АКТИВАЦИИ</span><b>${application.activated_at ? new Date(application.activated_at).toLocaleDateString('ru-RU') : '—'}</b></article></section><section class="agent-shortcuts">${action('Открыть кабинет агента','data-nav="profile"')}${action('Моя статистика','data-nav="stats"','secondary')}${action('Поддержка','data-nav="support"','secondary')}</section></div>`;
}

export function renderOnboarding(account, step = 0, started = false, geoSettings = [], justSubmitted = false, forceApplication = false) {
  const application = account?.application;
  if (!application && !started) return infoScreen(false);
  if (!application) return wizard({}, step, geoSettings, account?.telegram || {});
  if (application.status === 'draft') return wizard(application, step, geoSettings, account?.telegram || {});
  if (application.status === 'submitted' && justSubmitted && !forceApplication) return success(application);
  if (application.status === 'waiting_deposit') return deposit(application);
  if (application.status === 'waiting_documents') return documents(application);
  if (application.status === 'approved') return active(application);
  if (application.status === 'need_information') {
    if (!forceApplication && application.resume_state === 'waiting_deposit') return deposit(application);
    if (!forceApplication && ['waiting_documents','final_review'].includes(application.resume_state)) return documents(application);
    if (!forceApplication) return wizard(application, step, geoSettings, account?.telegram || {});
  }
  if (application.status === 'rejected') return `<div class="view onboarding-view">${pageHead('Моя заявка', application.application_number)}${notice(application)}<section class="review-status rejected"><span>❌</span><h1>Заявка отклонена</h1><p>Свяжитесь с менеджером, если вам нужно уточнить причину или возможность повторной подачи.</p></section>${action('Связаться с менеджером','data-nav="support"')}</div>`;
  return myApplication(application);
}

function managerButtons(application) {
  const common = '<button name="action" value="request_information">Запросить данные</button><button class="danger" name="action" value="reject">Отклонить</button>';
  const remove = application.status !== 'approved' ? `<button type="button" class="manager-delete-application" data-delete-application="${application.id}">${icon('trash')} Удалить заявку</button>` : '';
  let actions = '<button name="action" value="comment">Сохранить комментарий</button>';
  if (application.status === 'submitted') actions = `<button name="action" value="start_review">Начать проверку</button>${common}`;
  else if (application.status === 'under_review') actions = `<button name="action" value="pre_approve">Предварительно одобрить</button>${common}`;
  else if (application.status === 'pre_approved') actions = `<button name="action" value="open_deposit">Открыть депозит</button>${common}`;
  else if (application.status === 'waiting_deposit') actions = `${application.deposit_submitted_at ? '<button name="action" value="confirm_deposit">Подтвердить депозит</button>' : ''}${common}`;
  else if (application.status === 'waiting_documents') actions = common;
  else if (application.status === 'final_review') actions = `${application.documents_verified_at ? '<button name="action" value="activate">Активировать агента</button>' : '<button name="action" value="confirm_documents">Подтвердить документы</button>'}${common}`;
  else if (application.status === 'need_information') actions = '<button name="action" value="comment">Сохранить комментарий</button><button class="danger" name="action" value="reject">Отклонить</button>';
  const edit = application.status === 'approved' ? `<button type="button" data-edit-agent="${application.id}">✏️ Редактировать агента</button>` : '';
  return `${actions}${edit}${remove}`;
}

export function renderManager(applications = [], filter = 'all', query = '') {
  const groups = {new:['submitted'],review:['under_review','pre_approved','waiting_deposit','waiting_documents','final_review'],changes:['need_information'],approved:['approved'],rejected:['rejected']};
  const normalisedQuery = query.trim().toLowerCase().replace(/^@/, '');
  const byStatus = filter === 'all' ? applications : applications.filter(application => (groups[filter] || []).includes(application.status));
  const shown = normalisedQuery ? byStatus.filter(application => [application.name, application.telegram_username, application.telegram_id, application.cashdesk_name, application.cashdesk_geo, application.agent_id].filter(Boolean).some(value => String(value).toLowerCase().replace(/^@/, '').includes(normalisedQuery))) : byStatus;
  const cards = shown.length ? shown.map(application => `<article class="manager-application"><header><div><span>${e(application.application_number)}</span><h2>${e(application.name || application.telegram_username || application.telegram_id)}</h2><p>${application.telegram_username ? '@' + e(application.telegram_username) : 'Telegram ID ' + application.telegram_id}</p></div><b>${e(statusCopy[application.status]?.[0] || application.status)}</b></header><dl><dt>Дата</dt><dd>${application.created_at ? new Date(application.created_at).toLocaleString('ru-RU') : '—'}</dd><dt>Телефон</dt><dd>${e(application.phone)}</dd><dt>Email</dt><dd>${e(application.email)}</dd><dt>GEO</dt><dd>${e([application.geo_code,application.country,application.city].filter(Boolean).join(' · '))}</dd><dt>Опыт</dt><dd>${application.has_experience ? e(application.experience || 'Есть') : 'Нет'}</dd><dt>Игроки</dt><dd>${e(application.planned_players || '—')}</dd><dt>Касса</dt><dd>${e(application.cashdesk_name || 'Не указана')}</dd><dt>GEO кассы</dt><dd>${e(application.cashdesk_geo || '—')}</dd><dt>Место</dt><dd>${e(application.location)}</dd><dt>Источник</dt><dd>${e(application.source === 'other' ? application.source_other : application.source)}</dd><dt>Депозит</dt><dd>${application.deposit_submitted_at ? 'Отправлен на проверку' : 'Не отправлен'}</dd><dt>Agent ID</dt><dd>${e(application.agent_id || '—')}</dd></dl><div class="manager-documents">${['deposit','passport','selfie'].filter(kind => application.documents?.[kind]).map(kind => `<button data-manager-document="${kind}" data-application-id="${application.id}">${kind}</button>`).join('')}</div><details class="manager-history"><summary>История статусов (${application.history?.length || 0})</summary><div>${(application.history || []).map(item => `<p><b>${e(item.new_status)}</b><span>${item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : ''}</span><small>${e(item.comment || '')}</small></p>`).join('') || '<p>История пока пуста</p>'}</div></details><form data-form="manager-action" data-application-id="${application.id}"><textarea name="comment" placeholder="Комментарий / причина отклонения">${e(application.manager_comment)}</textarea><div class="manager-actions">${managerButtons(application)}</div></form></article>`).join('') : '<section class="empty-state"><h2>Заявок нет</h2><p>В этой категории пока ничего нет.</p></section>';
  const filters = [['all','Все'],['new','Новые'],['review','На проверке'],['changes','Нужны данные'],['approved','Одобренные'],['rejected','Отклонённые']];
  return `<div class="view manager-view">${pageHead('Кабинет менеджера', `${applications.length} заявок`)}${action('➕ Добавить агента','data-nav="manager-add-agent"')}${action('⚙️ Настройки GEO','data-nav="manager-geo"','secondary')}<label class="field manager-agent-search"><span>Найти агента</span><input data-manager-agent-search value="${e(query)}" autocomplete="off" placeholder="ФИО, @username, ID или касса"></label><div class="manager-filter">${filters.map(([value,label]) => `<button class="${filter === value ? 'active' : ''}" data-manager-filter="${value}">${label}</button>`).join('')}</div>${cards}</div>`;
}

export function renderManagerAddAgent() {
  return managerAgentForm('manager-add-agent', {}, 'Добавить агента', 'Создание подтверждённого профиля');
}

export function renderManagerEditAgent(agent = {}) {
  return managerAgentForm('manager-agent-edit', agent, 'Редактировать агента', agent.agent_id || 'Подтверждённый агент');
}

function managerAgentForm(formType, agent, title, subtitle) {
  const value = field => e(agent[field] || '');
  const telegramId = agent.telegram_id || '';
  const button = formType === 'manager-add-agent' ? 'Добавить агента' : 'Сохранить изменения';
  const attrs = formType === 'manager-agent-edit' ? ` data-agent-id="${e(agent.id)}"` : '';
  return `<div class="view manager-view">${pageHead(title, subtitle)}<form class="flow-card" data-form="${formType}"${attrs}><p class="form-help">ФИО и GEO кассы доступны только менеджерам. Обычным пользователям при проверке отображается только название кассы.</p><label class="field"><span>Telegram ID</span><input name="telegram_id" inputmode="numeric" pattern="[0-9]+" placeholder="123456789" value="${e(telegramId)}"></label><label class="field"><span>Username Telegram</span><input name="telegram_username" maxlength="32" placeholder="@username" value="${value('telegram_username')}"></label><label class="field"><span>Имя и фамилия *</span><input name="name" required maxlength="160" placeholder="Имя Фамилия" value="${value('name')}"></label><label class="field"><span>Название кассы *</span><input name="cashdesk_name" required maxlength="160" placeholder="Например: Central Cashdesk" value="${value('cashdesk_name')}"></label><label class="field"><span>GEO кассы</span><input name="cashdesk_geo" maxlength="32" placeholder="Например: TJ" value="${value('cashdesk_geo')}"></label><label class="field"><span>Страна *</span><input name="country" required maxlength="100" placeholder="Например: Tajikistan" value="${value('country')}"></label><label class="field"><span>Телефон *</span><input name="phone" required type="tel" placeholder="+992 900 000 000" value="${value('phone')}"></label><label class="field"><span>Email *</span><input name="email" required type="email" placeholder="name@example.com" value="${value('email')}"></label><div class="flow-actions">${action('Назад','type="button" data-nav="manager"','secondary')}${action(button,'type="submit"')}</div></form></div>`;
}

export function renderManagerGeoSettings(geoSettings = []) {
  const rows = geoSettings.map(setting => `<form class="geo-admin-row" data-form="manager-geo-setting" data-geo-code="${e(setting.geo_code)}"><header><b>${e(setting.geo_code)}</b><label><input type="checkbox" name="active" ${setting.active ? 'checked' : ''}> Активно</label></header><div class="field-split"><label class="field"><span>Страна</span><input name="country" required value="${e(setting.country)}"></label><label class="field"><span>Минимальный депозит</span><input name="minimum_deposit" type="number" min="0" required value="${e(setting.minimum_deposit)}"></label></div><label class="field"><span>Валюта</span><input name="currency" required maxlength="8" value="${e(setting.currency)}"></label>${action('Сохранить GEO','type="submit"')}</form>`).join('');
  return `<div class="view manager-access-view">${pageHead('Настройки GEO', 'Условия для агентов')}<p class="form-help">Изменения сразу используются в заявках агентов.</p>${rows || '<section class="empty-state"><h2>GEO-настройки не найдены</h2></section>'}${action('Назад в кабинет','data-nav="manager"','secondary')}</div>`;
}

export function renderManagerAccess(managers = [], geoSettings = []) {
  const list = managers.length ? managers.map(manager => `<article class="access-row"><div class="access-avatar">${e((manager.first_name || manager.username || 'M')[0])}</div><div><b>${e(manager.first_name || manager.username || 'Менеджер')}</b><span>${manager.username ? '@' + e(manager.username) + ' · ' : ''}ID ${manager.telegram_id}</span><small>${manager.is_superadmin ? 'Владелец' : manager.active ? 'Доступ активен' : 'Доступ отключён'}</small></div>${manager.source === 'database' && manager.active ? `<button data-revoke-manager="${manager.telegram_id}">Удалить</button>` : '<i>🔒</i>'}</article>`).join('') : '<section class="empty-state"><h2>Менеджеров пока нет</h2></section>';
  const geoList = geoSettings.map(setting => `<form class="geo-admin-row" data-form="geo-setting" data-geo-code="${e(setting.geo_code)}"><header><b>${e(setting.geo_code)}</b><label><input type="checkbox" name="active" ${setting.active ? 'checked' : ''}> Активно</label></header><div class="field-split"><label class="field"><span>Страна</span><input name="country" required value="${e(setting.country)}"></label><label class="field"><span>Минимальный депозит</span><input name="minimum_deposit" type="number" min="0" required value="${e(setting.minimum_deposit)}"></label></div><label class="field"><span>Валюта</span><input name="currency" required maxlength="8" value="${e(setting.currency)}"></label><button type="submit">Сохранить GEO</button></form>`).join('');
  return `<div class="view manager-access-view">${pageHead('Управление', 'Доступно менеджерам')}<section class="owner-warning">${icon('shield')}<div><b>Полный доступ менеджера</b><p>Менеджеры могут добавлять и отключать менеджеров, а также изменять условия GEO.</p></div></section><form class="flow-card" data-form="manager-access"><label class="field"><span>Username или Telegram ID *</span><input name="manager_identifier" required autocomplete="off" placeholder="@username или 123456789"></label><p class="form-help">Чтобы добавление по username работало, человек должен сначала отправить /start этому боту.</p>${action('Дать доступ менеджеру','type="submit"')}</form><div class="access-list"><div class="form-kicker">МЕНЕДЖЕРЫ · ${managers.length}</div>${list}</div><section class="geo-admin"><div class="section-title"><span>НАСТРОЙКИ</span><h2>Условия по GEO</h2></div><p>Суммы сохраняются в базе и автоматически отображаются агенту после выбора страны.</p>${geoList || '<div class="empty-state">GEO-настройки не найдены</div>'}</section></div>`;
}
