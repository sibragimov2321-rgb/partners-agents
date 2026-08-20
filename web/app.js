import { branding } from './config/branding.js?v=20260819-6';
import { esc, icon } from './ui.js?v=20260819-6';
import * as screens from './screens.js?v=20260820-2';
import { renderManager, renderManagerAccess, renderOnboarding } from './onboarding.js?v=20260820-2';
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();
const supportsBack=Boolean(tg?.isVersionAtLeast?.('6.1'));
const supportsHaptics=Boolean(tg?.isVersionAtLeast?.('6.1'));
const header=document.querySelector('#header'),content=document.querySelector('#content'),bottomNav=document.querySelector('#bottomNav'),toast=document.querySelector('#toast');
const languageOptions=[['ru','RU','Русский'],['en','EN','English'],['uz','UZ','O‘zbekcha'],['tg','TJ','Тоҷикӣ'],['tk','TK','Türkmençe'],['ky','KG','Кыргызча'],['kk','KZ','Қазақша'],['tr','TR','Türkçe'],['az','AZ','Azərbaycanca']];
const languageCopy={
  ru:{home:'Главная',stats:'Статистика',profile:'Кабинет',subtitle:'АГЕНТЫ И ПАРТНЁРЫ',applicationSent:'Заявка отправлена',ticketSent:'Обращение отправлено',error:'Не удалось выполнить действие. Откройте приложение в Telegram и попробуйте снова.',managerYes:'✅ Это официальный менеджер',managerNo:'⛔ Менеджер не найден в официальном списке',agentYes:'✅ Агент зарегистрирован в системе',agentNo:'⚠️ Агент не найден'},
  en:{home:'Home',stats:'Statistics',profile:'Account',subtitle:'AGENTS & PARTNERS',applicationSent:'Application submitted',ticketSent:'Ticket submitted',error:'Could not complete the action. Open the app in Telegram and try again.',managerYes:'✅ This is an official manager',managerNo:'⛔ Manager not found in the official list',agentYes:'✅ Agent is registered in the system',agentNo:'⚠️ Agent not found'},
  uz:{home:'Bosh sahifa',stats:'Statistika',profile:'Kabinet',subtitle:'AGENTLAR VA HAMKORLAR',applicationSent:'Ariza yuborildi',ticketSent:'Murojaat yuborildi',error:'Amalni bajarib bo‘lmadi. Ilovani Telegram orqali ochib, qayta urinib ko‘ring.',managerYes:'✅ Bu rasmiy menejer',managerNo:'⛔ Menejer rasmiy ro‘yxatda topilmadi',agentYes:'✅ Agent tizimda ro‘yxatdan o‘tgan',agentNo:'⚠️ Agent topilmadi'},
  tg:{home:'Асосӣ',stats:'Омор',profile:'Кабинет',subtitle:'АГЕНТҲО ВА ШАРИКОН',applicationSent:'Дархост фиристода шуд',ticketSent:'Муроҷиат фиристода шуд',error:'Амал иҷро нашуд. Барномаро дар Telegram кушоед ва боз кӯшиш кунед.',managerYes:'✅ Ин менеҷери расмӣ аст',managerNo:'⛔ Менеҷер дар рӯйхати расмӣ нест',agentYes:'✅ Агент дар система сабт шудааст',agentNo:'⚠️ Агент ёфт нашуд'},
  tk:{home:'Baş sahypa',stats:'Statistika',profile:'Kabinet',subtitle:'AGENTLER WE HYZMATDAŞLAR',applicationSent:'Arza iberildi',ticketSent:'Ýüzlenme iberildi',error:'Amaly ýerine ýetirip bolmady. Programmany Telegram-da açyp, gaýtadan synanyşyň.',managerYes:'✅ Bu resmi menejer',managerNo:'⛔ Menejer resmi sanawda tapylmady',agentYes:'✅ Agent ulgamda hasaba alnan',agentNo:'⚠️ Agent tapylmady'},
  ky:{home:'Башкы бет',stats:'Статистика',profile:'Кабинет',subtitle:'АГЕНТТЕР ЖАНА ӨНӨКТӨШТӨР',applicationSent:'Арыз жөнөтүлдү',ticketSent:'Кайрылуу жөнөтүлдү',error:'Аракет аткарылган жок. Колдонмону Telegram аркылуу ачып, кайра аракет кылыңыз.',managerYes:'✅ Бул расмий менеджер',managerNo:'⛔ Менеджер расмий тизмеден табылган жок',agentYes:'✅ Агент системада катталган',agentNo:'⚠️ Агент табылган жок'},
  kk:{home:'Басты бет',stats:'Статистика',profile:'Кабинет',subtitle:'АГЕНТТЕР МЕН СЕРІКТЕСТЕР',applicationSent:'Өтінім жіберілді',ticketSent:'Өтініш жіберілді',error:'Әрекет орындалмады. Қолданбаны Telegram арқылы ашып, қайталап көріңіз.',managerYes:'✅ Бұл ресми менеджер',managerNo:'⛔ Менеджер ресми тізімнен табылмады',agentYes:'✅ Агент жүйеде тіркелген',agentNo:'⚠️ Агент табылмады'},
  tr:{home:'Ana sayfa',stats:'İstatistik',profile:'Hesap',subtitle:'ACENTELER VE ORTAKLAR',applicationSent:'Başvuru gönderildi',ticketSent:'Talep gönderildi',error:'İşlem tamamlanamadı. Uygulamayı Telegram içinde açıp tekrar deneyin.',managerYes:'✅ Bu resmi bir yönetici',managerNo:'⛔ Yönetici resmi listede bulunamadı',agentYes:'✅ Acente sisteme kayıtlı',agentNo:'⚠️ Acente bulunamadı'},
  az:{home:'Ana səhifə',stats:'Statistika',profile:'Kabinet',subtitle:'AGENTLƏR VƏ TƏRƏFDAŞLAR',applicationSent:'Müraciət göndərildi',ticketSent:'Sorğu göndərildi',error:'Əməliyyatı yerinə yetirmək olmadı. Tətbiqi Telegram-da açıb yenidən cəhd edin.',managerYes:'✅ Bu rəsmi menecerdir',managerNo:'⛔ Menecer rəsmi siyahıda tapılmadı',agentYes:'✅ Agent sistemdə qeydiyyatdan keçib',agentNo:'⚠️ Agent tapılmadı'}
};
const savedLanguage=localStorage.getItem('partners-language');
const telegramLanguage=(tg?.initDataUnsafe?.user?.language_code||'ru').toLowerCase().split('-')[0];
const supportedLanguages=new Set(languageOptions.map(item=>item[0]));
const initialLanguage=supportedLanguages.has(savedLanguage)?savedLanguage:(supportedLanguages.has(telegramLanguage)?telegramLanguage:'ru');
const state={view:'home',account:null,loading:true,lang:initialLanguage,form:JSON.parse(sessionStorage.getItem('agent-form')||'{}'),agentStep:Number(localStorage.getItem('agent-step')||0),managerApps:[],managerFilter:'all',managers:[]};
const words=()=>languageCopy[state.lang]||languageCopy.ru;
const api=(path,options={})=>{const isForm=options.body instanceof FormData;return fetch(path,{...options,headers:{...(!isForm?{'Content-Type':'application/json'}:{}),'X-Telegram-Init-Data':tg?.initData||'',...(options.headers||{})}})};
function note(text){toast.textContent=text;toast.classList.add('show');clearTimeout(note.t);note.t=setTimeout(()=>toast.classList.remove('show'),2600)}
function headerView(){const c=words(),selected=languageOptions.find(item=>item[0]===state.lang)||languageOptions[0];const options=languageOptions.map(([code,label,name])=>`<button class="${state.lang===code?'active':''}" data-language="${code}"><b>${label}</b><span>${name}</span></button>`).join('');header.innerHTML=`<div class="language-picker"><button class="language-trigger" data-language-toggle aria-label="Language">${icon('globe')}<b>${selected[1]}</b></button><div class="language-menu" hidden>${options}</div></div><div class="portal-title"><b><span class="brand-mel">MEL</span><span class="brand-bet">BET</span> PARTNERS</b><span>${c.subtitle}</span></div><button class="header-avatar" data-nav="profile">${esc((state.account?.telegram?.first_name||'P')[0])}</button>`}
function render(){const c=words();const routes={home:()=>screens.home(state.account,state.lang),stats:()=>screens.stats(state.account,state.lang),profile:()=>screens.profile(state.account,state.lang),manager:()=>renderManager(state.managerApps,state.managerFilter),managers:()=>renderManagerAccess(state.managers),agents:()=>screens.agents(state.account,state.lang),partners:screens.partners,banners:screens.banners,agent_lookup:()=>screens.lookup('agent',state.lang),manager_lookup:()=>screens.lookup('manager',state.lang),faq:screens.faq,apply:()=>renderOnboarding(state.account,state.agentStep),check:()=>screens.check(state.account,state.lang),instructions:screens.instructions,support:()=>screens.support(state.lang),ticket:()=>screens.ticket(state.lang)};const nav=[['home',c.home,'home'],['stats',c.stats,'chart'],['profile',c.profile,'user']];headerView();content.innerHTML=state.loading?screens.loading():(routes[state.view]||routes.home)();bottomNav.innerHTML=nav.map(([v,l,i])=>`<button class="nav-item ${state.view===v?'active':''}" data-nav="${v}">${icon(i)}<span>${l}</span></button>`).join('');hydrateDocuments();if(supportsBack)state.view==='home'?tg.BackButton.hide():tg.BackButton.show()}
function go(view){state.view=view;if(supportsHaptics)tg.HapticFeedback.impactOccurred('light');render();scrollTo({top:0,behavior:'smooth'})}
async function load(){try{const r=await api('/api/me');if(r.ok)state.account=await r.json()}catch{}finally{state.loading=false;render()}}
async function readError(response){try{const data=await response.json();const detail=data.detail;return Array.isArray(detail)?detail.map(x=>x.msg).join(' · '):(detail||words().error)}catch{return words().error}}
async function refreshAccount(){const response=await api('/api/me');if(response.ok)state.account=await response.json()}
async function hydrateDocuments(){for(const image of content.querySelectorAll('[data-secure-doc]')){try{const response=await api(`/api/agent-documents/${image.dataset.secureDoc}`);if(response.ok)image.src=URL.createObjectURL(await response.blob())}catch{}}}
document.addEventListener('click',async e=>{
  const language=e.target.closest('[data-language]');
  if(language){state.lang=language.dataset.language;localStorage.setItem('partners-language',state.lang);if(supportsHaptics)tg.HapticFeedback.selectionChanged();return render()}
  const languageToggle=e.target.closest('[data-language-toggle]');
  if(languageToggle){const menu=header.querySelector('.language-menu');menu.hidden=!menu.hidden;return}
  const menu=header.querySelector('.language-menu');if(menu&&!e.target.closest('.language-picker'))menu.hidden=true;
  const step=e.target.closest('[data-agent-step]');
  if(step){state.agentStep=Number(step.dataset.agentStep);localStorage.setItem('agent-step',state.agentStep);return render()}
  const remove=e.target.closest('[data-delete-doc]');
  if(remove){remove.disabled=true;const response=await api(`/api/agent-documents/${remove.dataset.deleteDoc}`,{method:'DELETE'});if(!response.ok)note(await readError(response));else{await refreshAccount();note('Файл удалён');render()}return}
  const managerDocument=e.target.closest('[data-manager-document]');
  if(managerDocument){const response=await api(`/api/manager/applications/${managerDocument.dataset.applicationId}/documents/${managerDocument.dataset.managerDocument}`);if(!response.ok)return note(await readError(response));const url=URL.createObjectURL(await response.blob());window.open(url,'_blank');return}
  const managerFilter=e.target.closest('[data-manager-filter]');
  if(managerFilter){state.managerFilter=managerFilter.dataset.managerFilter;return render()}
  const revokeManager=e.target.closest('[data-revoke-manager]');
  if(revokeManager){revokeManager.disabled=true;const response=await api(`/api/superadmin/managers/${revokeManager.dataset.revokeManager}`,{method:'DELETE'});if(!response.ok)note(await readError(response));else{const list=await api('/api/superadmin/managers');state.managers=await list.json();note('Доступ менеджера удалён');render()}return}
  const flow=e.target.closest('[data-flow-action]');
  if(flow){
    if(flow.dataset.flowAction==='restart'){state.account.application.status='changes_requested';state.account.application.resume_state='account_review';return render()}
    flow.disabled=true;
    const endpoint=flow.dataset.flowAction==='deposit'?'/api/agent-onboarding/deposit':'/api/agent-onboarding/submit';
    const response=await api(endpoint,{method:'POST'});
    if(!response.ok)note(await readError(response));else{await refreshAccount();state.agentStep=0;localStorage.setItem('agent-step','0');note(flow.dataset.flowAction==='deposit'?'Депозит отправлен на проверку':'Заявка отправлена');render()}
    flow.disabled=false;return;
  }
  const target=e.target.closest('[data-nav]');
  if(target){if(target.dataset.nav==='manager'){const response=await api('/api/manager/applications');if(!response.ok)return note(await readError(response));state.managerApps=await response.json()}if(target.dataset.nav==='managers'){const response=await api('/api/superadmin/managers');if(!response.ok)return note(await readError(response));state.managers=await response.json()}return go(target.dataset.nav)}
  const faq=e.target.closest('.faq-question');if(faq)faq.parentElement.classList.toggle('open');
});

document.addEventListener('change',async e=>{
  if(e.target.name==='source'){const other=e.target.closest('form')?.querySelector('.source-other');if(other)other.hidden=e.target.value!=='other'}
  if(!e.target.matches('[data-doc-kind]'))return;
  const file=e.target.files?.[0];if(!file)return;
  const preview=content.querySelector(`[data-preview="${e.target.dataset.docKind}"]`);
  if(preview)preview.innerHTML=`<img src="${URL.createObjectURL(file)}" alt="Предпросмотр"><small>Загружается…</small>`;
  const body=new FormData();body.append('document',file);
  const response=await api(`/api/agent-documents/${e.target.dataset.docKind}`,{method:'POST',body});
  if(!response.ok)note(await readError(response));else{await refreshAccount();note('Файл сохранён');render()}
});

document.addEventListener('input',e=>{if(e.target.closest('[data-form="application"]')){state.form={...state.form,[e.target.name]:e.target.value};sessionStorage.setItem('agent-form',JSON.stringify(state.form))}});

document.addEventListener('submit',async e=>{
  const form=e.target,type=form.dataset.form;if(!type)return;e.preventDefault();
  const button=e.submitter||form.querySelector('[type="submit"]');if(button)button.disabled=true;
  const data=Object.fromEntries(new FormData(form)),c=words();
  try{
    if(type==='lookup'){
      const manager=form.dataset.check==='manager';const response=await api(manager?'/api/check-manager':'/api/check-contact',{method:'POST',body:JSON.stringify({query:data.query})});
      if(!response.ok)throw new Error(await readError(response));const result=await response.json(),box=form.parentElement.querySelector('.lookup-result');box.hidden=false;box.innerHTML=manager?(result.verified?c.managerYes:c.managerNo):(result.registered?c.agentYes:c.agentNo);return;
    }
    if(type==='account-start'){
      const body={account_identifier:data.account_identifier,phone:data.phone||null,email:data.email||null};const response=await api('/api/agent-onboarding/account',{method:'POST',body:JSON.stringify(body)});
      if(!response.ok)throw new Error(await readError(response));await refreshAccount();note('Аккаунт отправлен менеджеру');return render();
    }
    if(type==='agent-draft'){
      const response=await api('/api/agent-onboarding/draft',{method:'PATCH',body:JSON.stringify(data)});if(!response.ok)throw new Error(await readError(response));await refreshAccount();state.agentStep=Number(form.dataset.next||0);localStorage.setItem('agent-step',state.agentStep);note('Данные сохранены');return render();
    }
    if(type==='manager-action'){
      const actionValue=e.submitter?.value;if(!actionValue)return;const response=await api(`/api/manager/applications/${form.dataset.applicationId}/action`,{method:'POST',body:JSON.stringify({action:actionValue,comment:data.comment||null})});if(!response.ok)throw new Error(await readError(response));const list=await api('/api/manager/applications');state.managerApps=await list.json();note('Статус заявки обновлён');return render();
    }
    if(type==='manager-access'){
      const response=await api('/api/superadmin/managers',{method:'POST',body:JSON.stringify({telegram_id:Number(data.telegram_id)})});if(!response.ok)throw new Error(await readError(response));const list=await api('/api/superadmin/managers');state.managers=await list.json();form.reset();note('Менеджеру выдан доступ');return render();
    }
    const endpoint=type==='application'?'/api/agent-applications':'/api/support-tickets';const body=type==='application'?data:{subject:data.subject,category:data.category,body:data.body};const response=await api(endpoint,{method:'POST',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));
    if(type==='application'){sessionStorage.removeItem('agent-form');state.form={};await refreshAccount();note(c.applicationSent);go('apply')}else{note(c.ticketSent);go('support')}
  }catch(error){note(error.message||c.error)}finally{if(button)button.disabled=false}
});
if(supportsBack)tg.BackButton.onClick(()=>go('home'));load();
