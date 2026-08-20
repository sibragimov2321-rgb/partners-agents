import { esc, icon, pageHead } from './ui.js?v=20260820-1';

const steps = ['Аккаунт', 'Проверка', 'Депозит', 'Анкета', 'Одобрение'];
const stepByStatus = {
  account_review: 1,
  account_approved: 2,
  deposit_review: 2,
  profile_form: 3,
  application_review: 4,
  approved: 4,
  active_agent: 4,
  changes_requested: 3,
  rejected: 4,
};
const e = value => esc(value || '');
const action = (label, attrs = '', kind = 'primary') => `<button class="app-btn ${kind}" ${attrs}>${label}</button>`;

function progress(status) {
  const active = stepByStatus[status] ?? 0;
  return `<div class="flow-progress" aria-label="Этап регистрации">${steps.map((label, index) => `<div class="${index < active ? 'done' : index === active ? 'active' : ''}"><i>${index < active ? icon('check') : index + 1}</i><span>${label}</span></div>`).join('')}</div>`;
}

function notice(application) {
  if (!application?.manager_comment) return '';
  return `<section class="manager-note"><b>Комментарий менеджера</b><p>${e(application.manager_comment)}</p></section>`;
}

function waiting(application, emoji, title, text, badge) {
  return `<div class="view onboarding-view">${pageHead('Стать агентом', 'Регистрация агента')}${progress(application.status)}${notice(application)}<section class="review-status"><span>${emoji}</span><h1>${title}</h1><p>${text}</p><div class="review-badge">${badge}</div><small>Все данные сохранены. Возвращаться к предыдущим полям не нужно.</small></section></div>`;
}

function accountForm(application) {
  return `<div class="view onboarding-view">${pageHead('Стать агентом', 'Новый агент')}${progress('new')}<section class="onboarding-intro"><span>ШАГ 1</span><h1>Создайте рабочий аккаунт</h1><p>Откройте аккаунт на платформе и обязательно привяжите телефон или электронную почту.</p><ol><li><i>1</i><div><b>Откройте аккаунт</b><small>Используйте свои настоящие контактные данные</small></div></li><li><i>2</i><div><b>Привяжите контакт</b><small>Телефон или email нужен для проверки</small></div></li><li><i>3</i><div><b>Отправьте на проверку</b><small>Менеджер подтвердит аккаунт</small></div></li></ol></section>${notice(application)}<form class="flow-card" data-form="account-start"><label class="field"><span>ID, логин или email аккаунта *</span><input name="account_identifier" required minlength="3" value="${e(application?.account_identifier)}" placeholder="Ваш аккаунт"></label><div class="field-split"><label class="field"><span>Телефон</span><input name="phone" inputmode="tel" value="${e(application?.phone)}" placeholder="+7 000 000 00 00"></label><label class="field"><span>Email</span><input name="email" type="email" value="${e(application?.email)}" placeholder="name@example.com"></label></div><p class="form-help">Заполните хотя бы телефон или email.</p>${action('Я создал аккаунт', 'type="submit"')}</form></div>`;
}

function deposit(application, correction = false) {
  return `<div class="view onboarding-view">${pageHead('Стать агентом', 'Первоначальный депозит')}${progress('account_approved')}${notice(application)}<section class="deposit-card"><i>${icon('wallet')}</i><span>ШАГ 3</span><h1>${correction ? 'Исправьте подтверждение' : 'Пополните баланс для начала работы'}</h1><p>Первоначальный депозит станет рабочим балансом для проведения операций с игроками.</p></section><section class="secure-upload"><div><b>Подтверждение депозита</b><small>Необязательно, но ускоряет проверку · JPG, PNG или WEBP до 8 МБ</small></div><label class="upload-box ${application.documents?.deposit ? 'uploaded' : ''}"><input type="file" accept="image/jpeg,image/png,image/webp" data-doc-kind="deposit"><span>${application.documents?.deposit ? 'Заменить скриншот' : 'Загрузить скриншот'}</span></label><div class="document-preview" data-preview="deposit">${application.documents?.deposit ? `<img data-secure-doc="deposit" alt="Подтверждение депозита"><button data-delete-doc="deposit">Удалить</button>` : ''}</div></section>${action('Я сделал депозит', 'data-flow-action="deposit"')}</div>`;
}

function field(label, name, value, type = 'text', placeholder = '') {
  return `<label class="field"><span>${label} *</span><input type="${type}" name="${name}" required value="${e(value)}" placeholder="${placeholder}"></label>`;
}

function wizard(application, step = 0) {
  const screen = Math.max(0, Math.min(4, Number(step) || 0));
  const data = application || {};
  let body = '';
  if (screen === 0) {
    body = `<form class="flow-card" data-form="agent-draft" data-next="1"><div class="form-kicker">ЛИЧНЫЕ ДАННЫЕ</div>${field('Имя и фамилия', 'name', data.name, 'text', 'Ваше имя')}${field('Номер телефона', 'phone', data.phone, 'tel', '+7 000 000 00 00')}${field('Email', 'email', data.email, 'email', 'name@example.com')}<label class="field"><span>Опыт работы</span><textarea name="experience" placeholder="Коротко расскажите об опыте">${e(data.experience)}</textarea></label>${action('Сохранить и продолжить', 'type="submit"')}</form>`;
  } else if (screen === 1) {
    body = `<section class="privacy-card">${icon('shield')}<div><b>Документы защищены</b><p>Загружайте только чёткие фотографии. Доступ к ним есть только у авторизованных менеджеров.</p></div></section><section class="secure-upload">${documentRow('passport', 'Фото паспорта', data.documents?.passport)}${documentRow('selfie', 'Селфи с паспортом', data.documents?.selfie)}</section><div class="flow-actions">${action('Назад', 'data-agent-step="0"', 'secondary')}${action('Продолжить', 'data-agent-step="2"')}</div>`;
  } else if (screen === 2) {
    body = `<form class="flow-card" data-form="agent-draft" data-next="3"><div class="form-kicker">БУДУЩАЯ КАССА</div>${field('Название кассы', 'cashdesk_name', data.cashdesk_name, 'text', 'Например, Cash Point')}${field('Страна', 'country', data.country, 'text', 'Страна')}${field('Город', 'city', data.city, 'text', 'Город')}${field('Местоположение / район', 'location', data.location, 'text', 'Район или адрес')}<div class="flow-actions">${action('Назад', 'data-agent-step="1"', 'secondary')}${action('Сохранить', 'type="submit"')}</div></form>`;
  } else if (screen === 3) {
    body = `<form class="flow-card" data-form="agent-draft" data-next="4"><div class="form-kicker">ИСТОЧНИК</div><label class="field"><span>Откуда вы узнали о программе? *</span><select name="source" required><option value="">Выберите вариант</option>${[['telegram','Telegram'],['instagram','Instagram'],['facebook','Facebook'],['recommendation','По рекомендации'],['manager','Менеджер'],['other','Другой источник']].map(([value, label]) => `<option value="${value}" ${data.source === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label class="field source-other" ${data.source === 'other' ? '' : 'hidden'}><span>Укажите источник *</span><input name="source_other" value="${e(data.source_other)}" placeholder="Напишите источник"></label><div class="flow-actions">${action('Назад', 'data-agent-step="2"', 'secondary')}${action('Сохранить', 'type="submit"')}</div></form>`;
  } else {
    body = `<section class="review-grid"><article><span>КОНТАКТЫ</span><dl><dt>Имя</dt><dd>${e(data.name)}</dd><dt>Телефон</dt><dd>${e(data.phone)}</dd><dt>Email</dt><dd>${e(data.email)}</dd></dl></article><article><span>ДОКУМЕНТЫ</span><dl><dt>Паспорт</dt><dd>${data.documents?.passport ? '✅ Загружен' : '❌ Не загружен'}</dd><dt>Селфи</dt><dd>${data.documents?.selfie ? '✅ Загружено' : '❌ Не загружено'}</dd></dl></article><article><span>КАССА</span><dl><dt>Название</dt><dd>${e(data.cashdesk_name)}</dd><dt>Страна</dt><dd>${e(data.country)}</dd><dt>Город</dt><dd>${e(data.city)}</dd><dt>Место</dt><dd>${e(data.location)}</dd></dl></article><article><span>ИСТОЧНИК</span><p>${e(data.source === 'other' ? data.source_other : data.source)}</p></article></section><div class="flow-actions vertical">${action('Изменить данные', 'data-agent-step="0"', 'secondary')}${action('Отправить заявку', 'data-flow-action="submit"')}</div>`;
  }
  return `<div class="view onboarding-view">${pageHead('Анкета агента', `Шаг ${screen + 1} из 5`)}${progress('profile_form')}${notice(application)}<div class="substep"><span style="width:${(screen + 1) * 20}%"></span></div>${body}</div>`;
}

function documentRow(kind, title, uploaded) {
  return `<article class="document-row"><div><b>${title} *</b><small>${uploaded ? 'Файл сохранён' : 'JPG, PNG или WEBP · до 8 МБ'}</small></div><label class="upload-box ${uploaded ? 'uploaded' : ''}"><input type="file" accept="image/jpeg,image/png,image/webp" data-doc-kind="${kind}"><span>${uploaded ? 'Заменить' : 'Загрузить'}</span></label><div class="document-preview" data-preview="${kind}">${uploaded ? `<img data-secure-doc="${kind}" alt="${title}"><button data-delete-doc="${kind}">Удалить</button>` : ''}</div></article>`;
}

function active(application) {
  return `<div class="view onboarding-view">${pageHead('Кабинет агента', 'Аккаунт активирован')}${progress('active_agent')}<section class="success-agent"><div class="success-ring">${icon('check')}</div><span>ГОТОВО</span><h1>Вы стали агентом</h1><p>Ваш аккаунт активирован. Теперь вы можете начинать работу с игроками.</p><b>Agent ID · ${application.id}</b></section><section class="agent-shortcuts">${action('Открыть кабинет агента', 'data-nav="profile"')}${action('Как работать с игроками', 'data-nav="instructions"', 'secondary')}${action('Моя статистика', 'data-nav="stats"', 'secondary')}${action('Поддержка', 'data-nav="support"', 'secondary')}</section></div>`;
}

export function renderOnboarding(account, step = 0) {
  const application = account?.application;
  if (!application) return accountForm(null);
  if (application.status === 'reviewing') return waiting(application, '🕐', 'Заявка на проверке', 'Менеджер проверяет ранее отправленную заявку. Все данные сохранены.', 'ПРОВЕРЯЕТСЯ');
  if (application.status === 'account_review') return waiting(application, '🕐', 'Аккаунт на проверке', 'Аккаунт отправлен менеджеру. После проверки здесь появится следующий этап.', 'ПРОВЕРЯЕТСЯ');
  if (application.status === 'account_approved') return deposit(application);
  if (application.status === 'deposit_review') return waiting(application, '🕐', 'Проверяем депозит', 'Менеджер проверяет подтверждение. После одобрения откроется анкета агента.', 'ДЕПОЗИТ НА ПРОВЕРКЕ');
  if (application.status === 'profile_form') return wizard(application, step);
  if (application.status === 'application_review') return waiting(application, '🕐', 'Заявка отправлена', 'Менеджер проверит предоставленную информацию. Статус можно отслеживать здесь.', 'ФИНАЛЬНАЯ ПРОВЕРКА');
  if (application.status === 'approved') return waiting(application, '✅', 'Заявка одобрена', 'Данные проверены. Менеджер готовит активацию рабочего аккаунта.', 'ОЖИДАЕТ АКТИВАЦИИ');
  if (application.status === 'active_agent') return active(application);
  if (application.status === 'changes_requested') {
    if (application.resume_state === 'account_review') return accountForm(application);
    if (application.resume_state === 'deposit_review') return deposit(application, true);
    return wizard(application, step);
  }
  if (application.status === 'rejected') return `<div class="view onboarding-view">${pageHead('Стать агентом', 'Результат проверки')}${progress('rejected')}${notice(application)}<section class="review-status rejected"><span>❌</span><h1>Заявка отклонена</h1><p>Исправьте данные с учётом комментария менеджера и отправьте аккаунт повторно.</p>${action('Исправить и отправить', 'data-flow-action="restart"')}</section></div>`;
  return accountForm(application);
}

function managerButtons(application) {
  if (application.status === 'approved') return '<button name="action" value="activate">Активировать</button><button name="action" value="comment">Комментарий</button>';
  if (['account_review','deposit_review','application_review','reviewing'].includes(application.status)) return '<button name="action" value="approve">Одобрить</button><button name="action" value="changes">Исправить</button><button class="danger" name="action" value="reject">Отклонить</button><button name="action" value="comment">Комментарий</button>';
  if (application.status === 'changes_requested') return '<button name="action" value="comment">Комментарий</button><button class="danger" name="action" value="reject">Отклонить</button>';
  return '<button name="action" value="comment">Сохранить комментарий</button>';
}

export function renderManager(applications = [], filter = 'all') {
  const groups={new:['account_review'],review:['deposit_review','application_review','reviewing'],changes:['changes_requested'],approved:['approved','active_agent'],rejected:['rejected']};
  const shown=filter==='all'?applications:applications.filter(application=>(groups[filter]||[]).includes(application.status));
  const cards = shown.length ? shown.map(application => `<article class="manager-application"><header><div><span>ЗАЯВКА №${application.id}</span><h2>${e(application.name || application.telegram_username || application.telegram_id)}</h2><p>${application.telegram_username ? '@' + e(application.telegram_username) : 'Telegram ID ' + application.telegram_id}</p></div><b>${e(application.status)}</b></header><dl><dt>Аккаунт</dt><dd>${e(application.account_identifier)}</dd><dt>Телефон</dt><dd>${e(application.phone)}</dd><dt>Email</dt><dd>${e(application.email)}</dd><dt>Касса</dt><dd>${e(application.cashdesk_name)}</dd><dt>GEO</dt><dd>${e([application.country, application.city].filter(Boolean).join(', '))}</dd><dt>Источник</dt><dd>${e(application.source_other || application.source)}</dd></dl><div class="manager-documents">${['deposit','passport','selfie'].filter(kind => application.documents?.[kind]).map(kind => `<button data-manager-document="${kind}" data-application-id="${application.id}">${kind}</button>`).join('')}</div><form data-form="manager-action" data-application-id="${application.id}"><textarea name="comment" placeholder="Комментарий менеджера">${e(application.manager_comment)}</textarea><div class="manager-actions">${managerButtons(application)}</div></form></article>`).join('') : '<section class="empty-state"><h2>Заявок нет</h2><p>В этой категории пока ничего нет.</p></section>';
  const filters=[['all','Все'],['new','Новые'],['review','На проверке'],['changes','Исправления'],['approved','Одобренные'],['rejected','Отклонённые']];
  return `<div class="view manager-view">${pageHead('Кабинет менеджера', `${applications.length} заявок`)}<div class="manager-filter">${filters.map(([value,label])=>`<button class="${filter===value?'active':''}" data-manager-filter="${value}">${label}</button>`).join('')}</div>${cards}</div>`;
}

export function renderManagerAccess(managers = []) {
  const list = managers.length ? managers.map(manager => `<article class="access-row"><div class="access-avatar">${e((manager.first_name || manager.username || 'M')[0])}</div><div><b>${e(manager.first_name || manager.username || 'Менеджер')}</b><span>${manager.username ? '@' + e(manager.username) + ' · ' : ''}ID ${manager.telegram_id}</span><small>${manager.is_superadmin ? 'Владелец' : manager.active ? 'Доступ активен' : 'Доступ отключён'}</small></div>${manager.source === 'database' && manager.active ? `<button data-revoke-manager="${manager.telegram_id}">Удалить</button>` : '<i>🔒</i>'}</article>`).join('') : '<section class="empty-state"><h2>Менеджеров пока нет</h2></section>';
  return `<div class="view manager-access-view">${pageHead('Управление менеджерами', 'Доступ может выдавать только владелец')}<section class="owner-warning">${icon('shield')}<div><b>Защищённое управление</b><p>Укажите числовой Telegram ID. Менеджер сможет проверять заявки, но не сможет назначать других менеджеров.</p></div></section><form class="flow-card" data-form="manager-access"><label class="field"><span>Telegram ID менеджера *</span><input name="telegram_id" inputmode="numeric" pattern="[0-9]+" required placeholder="123456789"></label>${action('Дать доступ менеджеру', 'type="submit"')}</form><div class="access-list"><div class="form-kicker">МЕНЕДЖЕРЫ · ${managers.length}</div>${list}</div></div>`;
}
