const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
const MELBET_URL = 'https://melbet.org/ru';
const home = document.querySelector('#home');
const screen = document.querySelector('#screen');
const items = [
  ['💼', 'Агенты', 'agents'], ['👥', 'Партнёры', 'partners'],
  ['🖼', 'Получить баннер', 'banner'], ['🔎', 'Проверить контакт', 'check'],
  ['🛡', 'Заблокированный контакт', 'blocked'], ['❓', 'Вопросы и ответы', 'faq'],
  ['💬', 'Поддержка', 'support'],
];
function showHome() {
  screen.hidden = true;
  home.hidden = false;
  home.innerHTML = items.map(([icon, title, key]) =>
    `<button class="btn ${key === 'agents' ? 'primary' : ''}" onclick="openScreen('${key}')">${icon} ${title}</button>`).join('');
}
function openScreen(key) {
  home.hidden = true;
  screen.hidden = false;
  const title = items.find((x) => x[2] === key)?.[1] || '';
  let body = '';
  if (key === 'agents' || key === 'partners') body = `<p>Регистрация и вход в партнёрскую программу.</p><button class="btn primary" onclick="window.open('${MELBET_URL}', '_blank')">Открыть Melbet</button>`;
  else if (key === 'banner') body = `<p>Рекламные материалы доступны на странице партнёрской программы.</p><button class="btn primary" onclick="window.open('${MELBET_URL}', '_blank')">Перейти к материалам</button>`;
  else if (key === 'check' || key === 'blocked') body = '<p>Введите Telegram или email</p><input placeholder="@username или email"><button class="btn primary">Проверить</button>';
  else if (key === 'faq') body = ['Какие виды трафика разрешены?', 'По каким моделям работаем?', 'Есть ли реферальная программа?', 'Как обновляется статистика?', 'Какая минимальная сумма вывода?'].map((x) => `<div class="faq">${x}⌄</div>`).join('');
  else if (key === 'support') body = '<p>Напишите в поддержку партнёрской программы.</p>';
  else body = '<p>Раздел будет подключён после добавления API.</p>';
  screen.innerHTML = `<button class="back" onclick="showHome()">‹ Назад</button><h2>${title}</h2>${body}`;
}
showHome();
