const tg=window.Telegram?.WebApp; tg?.ready(); tg?.expand();
const MELBET_URL='https://melbet.org/ru'; const home=document.querySelector('#home'); const screen=document.querySelector('#screen');
const items=[['◈','Агенты','agents'],['♧','Партнёры','partners'],['▧','Получить баннер','banner'],['⌕','Проверить контакт','check'],['⊗','Заблокированный контакт','blocked'],['?','Вопросы и ответы','faq'],['◌','Поддержка','support']];
function showHome(){screen.hidden=true;home.hidden=false;home.innerHTML=items.map(([icon,title,key])=>`<button class="btn ${key==='agents'?'primary':''}" onclick="openScreen('${key}')"><b>${icon}</b>${title}</button>`).join('')}
function shell(title,body){screen.innerHTML=`<div class="topline"><button class="back" onclick="showHome()">‹ Назад</button><span class="brand-small">MB / PARTNERS</span></div><h2>${title}</h2>${body}`}
function openScreen(key){home.hidden=true;screen.hidden=false;
 if(key==='agents') return shell('Агенты','<button class="btn primary" onclick="window.open(\''+MELBET_URL+'\',\'_blank\')">☆ &nbsp;Стать агентом</button><button class="btn">♧ &nbsp;Я уже агент</button>');
 if(key==='partners') return shell('Партнёры','<button class="btn primary" onclick="window.open(\''+MELBET_URL+'\',\'_blank\')">✦ &nbsp;Стать партнёром</button><button class="btn">♧ &nbsp;Я уже партнёр</button>');
 if(key==='banner') return shell('Получить баннер','<p>Выберите рекламные материалы для работы.</p><button class="btn primary" onclick="window.open(\''+MELBET_URL+'\',\'_blank\')">▧ &nbsp;Открыть материалы</button>');
 if(key==='check'||key==='blocked') return shell(key==='check'?'Проверить контакт':'Заблокированный контакт',`<p>Введите Telegram или почту</p><input placeholder="@username или email"><button class="btn primary">⌕ &nbsp;Проверить</button>`);
 if(key==='faq') return shell('Вопросы и ответы',`<div class="tabs"><button class="tab active">Для партнёров</button><button class="tab">Для агентов</button></div>${['Какие виды трафика разрешены?','По каким моделям сотрудничества работаем?','Есть ли реферальная программа?','Как обновляются данные статистики?','Какая минимальная сумма вывода?','Когда производится выплата?'].map(q=>`<details class="card"><summary>${q}⌄</summary><p>Информация появится после подключения правил партнёрской программы.</p></details>`).join('')}`);
 return shell('Поддержка','<div class="note">Опишите вопрос — команда поддержки ответит вам.</div><button class="btn primary" style="margin-top:18px">◌ &nbsp;Написать в поддержку</button>');
}
showHome();
