import { esc, icon } from './ui.js?v=20260827-5';
import * as screens from './screens.js?v=20260827-6';
import { renderManager, renderManagerAccess, renderManagerAddAgent, renderManagerGeoSettings, renderOnboarding } from './onboarding.js?v=20260827-7';
import { renderGiveaway, renderGiveawayCreate, renderGiveawayManager, renderGiveawayManagerDetail, renderGiveawayWinners, renderMyGiveaway } from './giveaways.js?v=20260827-6';
import { canManageGiveaways } from './giveaway-permissions.mjs?v=20260826-2';
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();
const giveawayFromUrl=new URLSearchParams(window.location.search).get('giveaway');
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
const state={view:'home',account:null,loading:true,lang:initialLanguage,form:JSON.parse(sessionStorage.getItem('agent-form')||'{}'),agentStep:Number(localStorage.getItem('agent-step')||0),managerApps:[],managerFilter:'all',managers:[],geoSettings:[],managerGeoSettings:[],registrationStarted:false,justSubmitted:false,forceApplication:false,giveaway:null,giveawayParticipation:null,giveawayStage:'view',giveawayDraft:{},managerGiveaways:[],managerGiveaway:null,managerParticipants:{},managerGiveawayHistory:[]};
const words=()=>languageCopy[state.lang]||languageCopy.ru;
const api=(path,options={})=>{const isForm=options.body instanceof FormData;return fetch(path,{...options,headers:{...(!isForm?{'Content-Type':'application/json'}:{}),'X-Telegram-Init-Data':tg?.initData||'',...(options.headers||{})}})};
const confirmAction=message=>new Promise(resolve=>typeof tg?.showConfirm==='function'?tg.showConfirm(message,resolve):resolve(window.confirm(message)));
function note(text){toast.textContent=text;toast.classList.add('show');clearTimeout(note.t);note.t=setTimeout(()=>toast.classList.remove('show'),2600)}
function headerView(){const c=words(),selected=languageOptions.find(item=>item[0]===state.lang)||languageOptions[0];const options=languageOptions.map(([code,label,name])=>`<button class="${state.lang===code?'active':''}" data-language="${code}"><b>${label}</b><span>${name}</span></button>`).join('');header.innerHTML=`<div class="language-picker"><button class="language-trigger" data-language-toggle aria-label="Language">${icon('globe')}<b>${selected[1]}</b></button><div class="language-menu" hidden>${options}</div></div><div class="portal-title"><b>Partners <span>Agent</span></b><small>${c.subtitle}</small></div><button class="header-avatar" data-nav="profile">${esc((state.account?.telegram?.first_name||'P')[0])}</button>`}
function render(){const c=words();const routes={home:()=>screens.home(state.account,state.lang),stats:()=>screens.stats(state.account,state.lang),profile:()=>screens.profile(state.account,state.lang),manager:()=>renderManager(state.managerApps,state.managerFilter,state.lang),manager_add_agent:()=>renderManagerAddAgent(state.lang),manager_geo:()=>renderManagerGeoSettings(state.managerGeoSettings,state.lang),managers:()=>renderManagerAccess(state.managers,state.managerGeoSettings,state.lang),agents:()=>screens.agents(state.account,state.lang),partners:()=>screens.partners(state.lang),banners:()=>screens.banners(state.lang),agent_lookup:()=>screens.lookup('agent',state.lang),manager_lookup:()=>screens.lookup('manager',state.lang),faq:()=>screens.faq(state.lang),apply:()=>renderOnboarding(state.account,state.agentStep,state.registrationStarted,state.geoSettings,state.justSubmitted,state.forceApplication,state.lang),check:()=>screens.check(state.account,state.lang),instructions:()=>screens.instructions(state.lang),support:()=>screens.support(state.lang),ticket:()=>screens.ticket(state.lang),giveaway:()=>renderGiveaway(state.giveaway,state.giveawayParticipation,state.geoSettings,state.giveawayStage,state.giveawayDraft,state.lang),giveaway_mine:()=>renderMyGiveaway(state.giveaway,state.giveawayParticipation,state.geoSettings,state.lang),giveaway_winners:()=>renderGiveawayWinners(state.giveaway,state.lang),manager_giveaways:()=>renderGiveawayManager(state.managerGiveaways,state.geoSettings,state.lang),manager_giveaway_create:()=>renderGiveawayCreate(state.geoSettings,null,state.lang),manager_giveaway_edit:()=>renderGiveawayCreate(state.geoSettings,state.managerGiveaway,state.lang),manager_giveaway:()=>renderGiveawayManagerDetail(state.managerGiveaway,state.managerParticipants,state.managerGiveawayHistory,state.geoSettings,state.lang)};const nav=[['home',c.home,'home'],['stats',c.stats,'chart'],['profile',c.profile,'user']];headerView();content.innerHTML=state.loading?screens.loading():(routes[state.view]||routes.home)();screens.localizeGiveawayDom(content,state.lang);bottomNav.innerHTML=nav.map(([v,l,i])=>`<button class="nav-item ${state.view===v?'active':''}" data-nav="${v}">${icon(i)}<span>${l}</span></button>`).join('');hydrateDocuments();updateGeoCondition(content.querySelector('select[name="country"]'));if(supportsBack)state.view==='home'?tg.BackButton.hide():tg.BackButton.show()}
// data-nav values are HTML-friendly and may use hyphens, while the internal
// route map uses JavaScript-friendly underscores. Normalise once here so a
// manager route can never fall back to the home screen because of its name.
function go(view){state.view=String(view).replaceAll('-','_');if(supportsHaptics)tg.HapticFeedback.impactOccurred('light');render();scrollTo({top:0,behavior:'smooth'})}
async function load(){try{const [meResponse,geoResponse,giveawayResponse]=await Promise.all([api('/api/me'),api('/api/geo-settings'),api('/api/giveaways/active')]);if(meResponse.ok)state.account=await meResponse.json();if(geoResponse.ok)state.geoSettings=await geoResponse.json();if(giveawayResponse.ok){state.giveaway=await giveawayResponse.json();if(state.giveaway){const participation=await api(`/api/giveaways/${state.giveaway.id}/participation`);state.giveawayParticipation=participation.ok?await participation.json():null;if(String(state.giveaway.id)===giveawayFromUrl)state.view='giveaway'}}}catch{}finally{state.loading=false;render()}}
async function readError(response){try{const data=await response.json();const detail=data.detail;const codes={PLAYER_NOT_FOUND:'giveaway.validation.playerNotFound',GEO_MISMATCH:'giveaway.validation.geoMismatch',PLAYER_CHECK_FAILED:'giveaway.validation.checkFailed',CURRENCY_GEO_MAPPING_MISSING:'giveaway.validation.mappingMissing',GIVEAWAY_CLOSED:'giveaway.validation.closed',GIVEAWAY_NOT_STARTED:'giveaway.validation.notStarted',GEO_NOT_ALLOWED:'giveaway.validation.notAllowedGeo',PLAYER_ALREADY_JOINED:'giveaway.validation.duplicatePlayer',ALREADY_JOINED:'giveaway.validation.alreadyJoined'};return codes[detail]?screens.t(state.lang,codes[detail]):(Array.isArray(detail)?detail.map(x=>x.msg).join(' · '):(detail||words().error))}catch{return words().error}}
function agentLookupResult(result){
  if(result.verified&&result.agent){const a=result.agent,date=a.connected_at?new Date(a.connected_at).toLocaleDateString(state.lang==='ru'?'ru-RU':'en-GB'):'—';return `<article class="verified-agent-card"><header><i>${icon('check')}</i><div><span>✓ VERIFIED AGENT</span><h3>${esc(a.name||'Agent')}</h3></div></header><dl><dt>Agent ID</dt><dd>${esc(a.agent_id)}</dd><dt>${state.lang==='ru'?'Страна':'Country'}</dt><dd>${esc(a.country||'—')}</dd><dt>${state.lang==='ru'?'Город':'City'}</dt><dd>${esc(a.city||'—')}</dd><dt>${state.lang==='ru'?'Статус':'Status'}</dt><dd>${state.lang==='ru'?'Подтверждён':'Verified'}</dd><dt>${state.lang==='ru'?'Подключён':'Connected'}</dt><dd>${date}</dd></dl></article>`}
  return `<article class="unverified-agent-card"><i>${icon('shield')}</i><div><b>${state.lang==='ru'?'Агент не подтверждён':'Agent not verified'}</b><p>${state.lang==='ru'?'Не переводите деньги человеку, если он не подтверждён системой. Обратитесь в поддержку для дополнительной проверки.':'Do not transfer money unless the person is verified by the system. Contact support for an additional check.'}</p></div></article>`;
}
async function refreshAccount(){const response=await api('/api/me');if(response.ok)state.account=await response.json()}
function updateGeoCondition(select){if(!select)return;const option=select.selectedOptions?.[0],box=select.closest('form')?.querySelector('[data-geo-condition]');if(!box)return;const amount=option?.dataset.deposit,code=option?.dataset.geo,currency=option?.dataset.currency||'USD';box.hidden=!amount;box.innerHTML=amount?`<b>Условия GEO ${esc(code||'')}</b><span>Стартовый депозит — от ${esc(amount)} ${esc(currency)}</span>`:''}
async function hydrateDocuments(){for(const image of content.querySelectorAll('[data-secure-doc]')){try{const response=await api(`/api/agent-documents/${image.dataset.secureDoc}`);if(response.ok)image.src=URL.createObjectURL(await response.blob())}catch{}}}
async function prepareDocumentImage(file){
  if(!file.type.startsWith('image/')||file.size<=2.5*1024*1024||typeof createImageBitmap!=='function')return file;
  try{
    const bitmap=await createImageBitmap(file),limit=1800,scale=Math.min(1,limit/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));
    canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close?.();
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.86));
    return blob&&blob.size<file.size?new File([blob],`${file.name.replace(/\.[^.]+$/,'')||'document'}.jpg`,{type:'image/jpeg'}):file;
  }catch{return file}
}
document.addEventListener('click',async e=>{
  const language=e.target.closest('[data-language]');
  if(language){state.lang=language.dataset.language;localStorage.setItem('partners-language',state.lang);if(supportsHaptics)tg.HapticFeedback.selectionChanged();return render()}
  const languageToggle=e.target.closest('[data-language-toggle]');
  if(languageToggle){const menu=header.querySelector('.language-menu');menu.hidden=!menu.hidden;return}
  const menu=header.querySelector('.language-menu');if(menu&&!e.target.closest('.language-picker'))menu.hidden=true;
  const giveawayStage=e.target.closest('[data-giveaway-stage]');
  if(giveawayStage){state.giveawayStage=giveawayStage.dataset.giveawayStage;return render()}
  const giveawayMine=e.target.closest('[data-giveaway-mine]');
  if(giveawayMine)return go('giveaway_mine');
  const giveawayWinners=e.target.closest('[data-giveaway-winners]');
  if(giveawayWinners)return go('giveaway_winners');
  const giveawayRules=e.target.closest('[data-giveaway-rules]');
  if(giveawayRules){content.querySelector('[data-giveaway-rules-box]')?.setAttribute('open','');content.querySelector('[data-giveaway-rules-box]')?.scrollIntoView({behavior:'smooth',block:'center'});return}
  const confirmGiveawayJoin=e.target.closest('[data-confirm-giveaway-join]');
  if(confirmGiveawayJoin){
    confirmGiveawayJoin.disabled=true;const response=await api(`/api/giveaways/${state.giveaway.id}/participation`,{method:'POST',body:JSON.stringify(state.giveawayDraft)});
    if(!response.ok){confirmGiveawayJoin.disabled=false;return note(await readError(response))}
    state.giveawayParticipation=await response.json();state.giveawayStage='view';note('🎉 Вы успешно зарегистрированы!');return go('giveaway_mine');
  }
  const openGiveaway=e.target.closest('[data-giveaway-open]');
  if(openGiveaway){
    const id=openGiveaway.dataset.giveawayOpen;const [detail,participants,history]=await Promise.all([api(`/api/manager/giveaways/${id}`),api(`/api/manager/giveaways/${id}/participants`),api(`/api/manager/giveaways/${id}/history`)]);
    if(!detail.ok)return note(await readError(detail));state.managerGiveaway=await detail.json();state.managerParticipants=participants.ok?await participants.json():{};state.managerGiveawayHistory=history.ok?await history.json():[];return go('manager_giveaway');
  }
  const managerGiveawayAction=e.target.closest('[data-giveaway-manager-action]');
  if(managerGiveawayAction){
    const action=managerGiveawayAction.dataset.giveawayManagerAction;const labels={launch:'Запустить этот розыгрыш?',close:'Закрыть регистрацию?',cancel:'Отменить розыгрыш?'};
    if(!await confirmAction(labels[action]||'Подтвердить действие?'))return;managerGiveawayAction.disabled=true;
    const response=await api(`/api/manager/giveaways/${managerGiveawayAction.dataset.giveawayId}/action`,{method:'POST',body:JSON.stringify({action})});
    if(!response.ok){managerGiveawayAction.disabled=false;return note(await readError(response))}state.managerGiveaway=await response.json();const list=await api('/api/manager/giveaways');if(list.ok)state.managerGiveaways=await list.json();note('Статус розыгрыша обновлён');return render();
  }
  const drawGiveaway=e.target.closest('[data-giveaway-draw]');
  if(drawGiveaway){
    if(!await confirmAction(`Выбрать ${state.managerGiveaway?.winner_count||0} победителей случайным образом? Действие нельзя отменить без перевыбора.`))return;drawGiveaway.disabled=true;
    const response=await api(`/api/manager/giveaways/${drawGiveaway.dataset.giveawayDraw}/draw`,{method:'POST'});if(!response.ok){drawGiveaway.disabled=false;return note(await readError(response))}state.managerGiveaway=await response.json();const list=await api('/api/manager/giveaways');if(list.ok)state.managerGiveaways=await list.json();note('🏆 Победители выбраны');return render();
  }
  const excludeParticipant=e.target.closest('[data-giveaway-exclude]');
  if(excludeParticipant){const reason=window.prompt('Причина исключения участника:');if(!reason?.trim())return;excludeParticipant.disabled=true;const response=await api(`/api/manager/giveaways/${state.managerGiveaway.id}/participants/${excludeParticipant.dataset.giveawayExclude}/exclude`,{method:'POST',body:JSON.stringify({reason})});if(!response.ok){excludeParticipant.disabled=false;return note(await readError(response))}const list=await api(`/api/manager/giveaways/${state.managerGiveaway.id}/participants`);state.managerParticipants=list.ok?await list.json():state.managerParticipants;note('Участник исключён');return render()}
  const restoreParticipant=e.target.closest('[data-giveaway-restore]');
  if(restoreParticipant){restoreParticipant.disabled=true;const response=await api(`/api/manager/giveaways/${state.managerGiveaway.id}/participants/${restoreParticipant.dataset.giveawayRestore}/restore`,{method:'POST'});if(!response.ok){restoreParticipant.disabled=false;return note(await readError(response))}const list=await api(`/api/manager/giveaways/${state.managerGiveaway.id}/participants`);state.managerParticipants=list.ok?await list.json():state.managerParticipants;note('Участник возвращён');return render()}
  const editGiveaway=e.target.closest('[data-giveaway-edit]');
  if(editGiveaway)return go('manager_giveaway_edit');
  const replaceWinner=e.target.closest('[data-giveaway-replace]');
  if(replaceWinner){const reason=window.prompt('Причина перевыбора победителя:');if(!reason?.trim())return;const response=await api(`/api/manager/giveaways/${replaceWinner.dataset.giveawayId}/winners/${replaceWinner.dataset.giveawayReplace}/replace`,{method:'POST',body:JSON.stringify({reason})});if(!response.ok)return note(await readError(response));state.managerGiveaway=await response.json();note('Победитель заменён');return render()}
  const startRegistration=e.target.closest('[data-start-registration]');
  if(startRegistration){state.registrationStarted=true;state.agentStep=0;state.forceApplication=false;localStorage.setItem('agent-step','0');return render()}
  const showApplication=e.target.closest('[data-show-application]');
  if(showApplication){state.justSubmitted=false;state.forceApplication=true;return render()}
  const resumeApplication=e.target.closest('[data-resume-application]');
  if(resumeApplication){state.forceApplication=false;state.agentStep=0;return render()}
  const scrollTarget=e.target.closest('[data-scroll-to]');
  if(scrollTarget){document.getElementById(scrollTarget.dataset.scrollTo)?.scrollIntoView({behavior:'smooth',block:'start'});return}
  const step=e.target.closest('[data-agent-step]');
  if(step){state.agentStep=Number(step.dataset.agentStep);localStorage.setItem('agent-step',state.agentStep);return render()}
  const remove=e.target.closest('[data-delete-doc]');
  if(remove){remove.disabled=true;const response=await api(`/api/agent-documents/${remove.dataset.deleteDoc}`,{method:'DELETE'});if(!response.ok)note(await readError(response));else{await refreshAccount();note('Файл удалён');render()}return}
  const managerDocument=e.target.closest('[data-manager-document]');
  if(managerDocument){const response=await api(`/api/manager/applications/${managerDocument.dataset.applicationId}/documents/${managerDocument.dataset.managerDocument}`);if(!response.ok)return note(await readError(response));const url=URL.createObjectURL(await response.blob());window.open(url,'_blank');return}
  const managerFilter=e.target.closest('[data-manager-filter]');
  if(managerFilter){state.managerFilter=managerFilter.dataset.managerFilter;return render()}
  const deleteApplication=e.target.closest('[data-delete-application]');
  if(deleteApplication){
    const confirmed=await confirmAction('Удалить эту заявку? Пользователь сможет подать новую заявку.');
    if(!confirmed)return;
    deleteApplication.disabled=true;
    const card=deleteApplication.closest('.manager-application');
    const reason=card?.querySelector('textarea[name="comment"]')?.value.trim()||'Удалена менеджером как ненужная';
    const response=await api(`/api/manager/applications/${deleteApplication.dataset.deleteApplication}`,{method:'DELETE',body:JSON.stringify({reason})});
    if(!response.ok){deleteApplication.disabled=false;return note(await readError(response))}
    const list=await api('/api/manager/applications');state.managerApps=list.ok?await list.json():state.managerApps;note('Заявка удалена');return render();
  }
  const revokeManager=e.target.closest('[data-revoke-manager]');
  if(revokeManager){revokeManager.disabled=true;const response=await api(`/api/superadmin/managers/${revokeManager.dataset.revokeManager}`,{method:'DELETE'});if(!response.ok)note(await readError(response));else{const list=await api('/api/superadmin/managers');state.managers=await list.json();note('Доступ менеджера удалён');render()}return}
  const flow=e.target.closest('[data-flow-action]');
  if(flow){
    flow.disabled=true;
    const isDeposit=flow.dataset.flowAction==='deposit';
    const endpoint=isDeposit?'/api/agent-onboarding/deposit':'/api/agent-onboarding/submit';
    const response=await api(endpoint,{method:'POST',...(!isDeposit?{body:JSON.stringify({confirmed_truth:true})}:{})});
    if(!response.ok)note(await readError(response));else{await refreshAccount();state.agentStep=0;state.forceApplication=false;localStorage.setItem('agent-step','0');note(isDeposit?'Депозит отправлен на проверку':'Документы отправлены на проверку');render()}
    flow.disabled=false;return;
  }
  const target=e.target.closest('[data-nav]');
  if(target){if(target.dataset.nav==='apply'){state.forceApplication=false;state.justSubmitted=false;state.registrationStarted=false}if(target.dataset.nav==='manager'){const response=await api('/api/manager/applications');if(!response.ok)return note(await readError(response));state.managerApps=await response.json()}if(target.dataset.nav==='manager-geo'){const response=await api('/api/manager/geo-settings');if(!response.ok)return note(await readError(response));state.managerGeoSettings=await response.json()}if(target.dataset.nav==='managers'){const [managersResponse,geoResponse]=await Promise.all([api('/api/superadmin/managers'),api('/api/manager/geo-settings')]);if(!managersResponse.ok)return note(await readError(managersResponse));if(!geoResponse.ok)return note(await readError(geoResponse));state.managers=await managersResponse.json();state.managerGeoSettings=await geoResponse.json()}if(target.dataset.nav==='giveaway'){state.giveawayStage='view';const active=await api('/api/giveaways/active');if(active.ok){state.giveaway=await active.json();if(state.giveaway){const participation=await api(`/api/giveaways/${state.giveaway.id}/participation`);state.giveawayParticipation=participation.ok?await participation.json():null}}}if(target.dataset.nav==='manager-giveaways'){if(!canManageGiveaways(state.account))return note('Доступ к управлению розыгрышами есть только у менеджера.');const response=await api('/api/manager/giveaways');if(!response.ok)return note(await readError(response));state.managerGiveaways=await response.json()}return go(target.dataset.nav)}
  const faq=e.target.closest('.faq-question');if(faq)faq.parentElement.classList.toggle('open');
});

document.addEventListener('change',async e=>{
  if(e.target.name==='source'){const form=e.target.closest('form'),other=form?.querySelector('.source-other'),referral=form?.querySelector('.referral-agent');if(other){other.hidden=e.target.value!=='other';const input=other.querySelector('input');if(input)input.required=e.target.value==='other'}if(referral){referral.hidden=e.target.value!=='agent';const input=referral.querySelector('input');if(input)input.required=e.target.value==='agent'}}
  if(e.target.name==='country'){const other=e.target.closest('form')?.querySelector('.country-other');if(other){other.hidden=e.target.value!=='__other__';const input=other.querySelector('input');if(input)input.required=e.target.value==='__other__'}updateGeoCondition(e.target)}
  if(e.target.name==='has_experience'){const details=e.target.closest('form')?.querySelector('.experience-details');if(details){details.hidden=e.target.value!=='true';const textarea=details.querySelector('textarea');if(textarea)textarea.required=e.target.value==='true'}}
  if(!e.target.matches('[data-doc-kind]'))return;
  const original=e.target.files?.[0];if(!original)return;
  if(original.size>20*1024*1024){note('Исходный файл должен быть не больше 20 МБ');e.target.value='';return}
  const file=await prepareDocumentImage(original);
  const preview=content.querySelector(`[data-preview="${e.target.dataset.docKind}"]`);
  if(preview)preview.innerHTML=`<img src="${URL.createObjectURL(file)}" alt="Предпросмотр"><small>${file.size<original.size?'Фото сжато · ':''}Загружается…</small>`;
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
      if(!response.ok)throw new Error(await readError(response));const result=await response.json(),box=form.parentElement.querySelector('.lookup-result');box.hidden=false;box.innerHTML=manager?(result.verified?c.managerYes:c.managerNo):agentLookupResult(result);box.classList.toggle('detailed',!manager);return;
    }
    if(type==='account-start'){
      const body={account_identifier:data.account_identifier,phone:data.phone||null,email:data.email||null};const response=await api('/api/agent-onboarding/account',{method:'POST',body:JSON.stringify(body)});
      if(!response.ok)throw new Error(await readError(response));await refreshAccount();note('Аккаунт отправлен менеджеру');return render();
    }
    if(type==='agent-draft'){
      if(data.country==='__other__'){data.country=(data.country_other||'').trim();if(!data.country)throw new Error('Введите название страны')}
      delete data.country_other;
      for(const field of ['has_experience','physical_point'])if(field in data)data[field]=data[field]==='true';
      const response=await api('/api/agent-onboarding/draft',{method:'PATCH',body:JSON.stringify(data)});if(!response.ok)throw new Error(await readError(response));await refreshAccount();state.agentStep=Number(form.dataset.next||0);localStorage.setItem('agent-step',state.agentStep);note('Данные сохранены');return render();
    }
    if(type==='agent-submit'){
      const response=await api('/api/agent-onboarding/submit',{method:'POST',body:JSON.stringify({confirmed_truth:data.confirmed_truth==='true'})});if(!response.ok)throw new Error(await readError(response));await refreshAccount();state.justSubmitted=true;state.forceApplication=false;state.agentStep=0;localStorage.setItem('agent-step','0');note(c.applicationSent);return render();
    }
    if(type==='giveaway-join-data'){
      state.giveawayDraft={geo_code:(data.geo_code||'').trim(),player_id:(data.player_id||'').trim().replace(/\s+/g,'')};state.giveawayStage='confirm';return render();
    }
    if(type==='manager-add-agent'){
      const telegramId=(data.telegram_id||'').trim();const body={telegram_id:telegramId?Number(telegramId):null,telegram_username:(data.telegram_username||'').trim(),name:(data.name||'').trim(),country:(data.country||'').trim(),phone:(data.phone||'').trim(),email:(data.email||'').trim()};const response=await api('/api/manager/agents',{method:'POST',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));const list=await api('/api/manager/applications');state.managerApps=list.ok?await list.json():state.managerApps;note('Агент добавлен и подтверждён');return go('manager');
    }
    if(type==='giveaway-create'||type==='giveaway-edit'){
      const raw=new FormData(form);const body={title:(raw.get('title')||'').trim(),description:(raw.get('description')||'').trim(),prize:(raw.get('prize')||'').trim(),winner_count:Number(raw.get('winner_count')),start_at:new Date(raw.get('start_at')).toISOString(),end_at:new Date(raw.get('end_at')).toISOString(),geo_codes:raw.getAll('geo_codes'),rules:(raw.get('rules')||'').trim()};
      const endpoint=type==='giveaway-create'?'/api/manager/giveaways':`/api/manager/giveaways/${form.dataset.giveawayId}`;const response=await api(endpoint,{method:type==='giveaway-create'?'POST':'PATCH',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));state.managerGiveaway=await response.json();
      const banner=raw.get('banner');if(type==='giveaway-create'&&banner instanceof File&&banner.size){const upload=new FormData();upload.append('banner',banner);const bannerResponse=await api(`/api/manager/giveaways/${state.managerGiveaway.id}/banner`,{method:'POST',body:upload});if(!bannerResponse.ok)note(await readError(bannerResponse));else{const refresh=await api(`/api/manager/giveaways/${state.managerGiveaway.id}`);if(refresh.ok)state.managerGiveaway=await refresh.json()}}
      const [list,participants,history]=await Promise.all([api('/api/manager/giveaways'),api(`/api/manager/giveaways/${state.managerGiveaway.id}/participants`),api(`/api/manager/giveaways/${state.managerGiveaway.id}/history`)]);if(list.ok)state.managerGiveaways=await list.json();state.managerParticipants=participants.ok?await participants.json():{};state.managerGiveawayHistory=history.ok?await history.json():[];note(type==='giveaway-create'?'Preview розыгрыша создан':'Розыгрыш обновлён');return go('manager_giveaway');
    }
    if(type==='giveaway-participants-filter'){
      const params=new URLSearchParams();if(data.query?.trim())params.set('query',data.query.trim());if(data.status)params.set('status',data.status);if(data.geo_code)params.set('geo_code',data.geo_code);const response=await api(`/api/manager/giveaways/${form.dataset.giveawayId}/participants?${params}`);if(!response.ok)throw new Error(await readError(response));state.managerParticipants=await response.json();return render();
    }
    if(type==='giveaway-broadcast'){
      if(!await confirmAction('Отправить это сообщение выбранным участникам?'))return;const geo_codes=(data.geo_codes||'').split(',').map(value=>value.trim().toUpperCase()).filter(Boolean);const response=await api(`/api/manager/giveaways/${form.dataset.giveawayId}/broadcast`,{method:'POST',body:JSON.stringify({audience:data.audience,geo_codes,message:data.message,button_text:data.button_text||null})});if(!response.ok)throw new Error(await readError(response));const result=await response.json();note(result.status==='queued'?`Рассылка запущена: ${result.recipients} получателей`:`Рассылка завершена: ${result.sent}/${result.recipients}`);return;
    }
    if(type==='manager-action'){
      const actionValue=e.submitter?.value;if(!actionValue)return;const response=await api(`/api/manager/applications/${form.dataset.applicationId}/action`,{method:'POST',body:JSON.stringify({action:actionValue,comment:data.comment||null})});if(!response.ok)throw new Error(await readError(response));const list=await api('/api/manager/applications');state.managerApps=await list.json();note('Статус заявки обновлён');return render();
    }
    if(type==='manager-access'){
      const identifier=(data.manager_identifier||'').trim();const body=/^[0-9]+$/.test(identifier)?{telegram_id:Number(identifier)}:{username:identifier};const response=await api('/api/superadmin/managers',{method:'POST',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));const list=await api('/api/superadmin/managers');state.managers=await list.json();form.reset();note('Менеджеру выдан доступ');return render();
    }
    if(type==='geo-setting'||type==='manager-geo-setting'){
      const body={country:data.country,currency:data.currency,minimum_deposit:Number(data.minimum_deposit),active:data.active==='on'};const endpoint=type==='geo-setting'?`/api/superadmin/geo-settings/${form.dataset.geoCode}`:`/api/manager/geo-settings/${form.dataset.geoCode}`;const response=await api(endpoint,{method:'PUT',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));const [publicResponse,managerResponse]=await Promise.all([api('/api/geo-settings'),api('/api/manager/geo-settings')]);state.geoSettings=publicResponse.ok?await publicResponse.json():state.geoSettings;state.managerGeoSettings=managerResponse.ok?await managerResponse.json():state.managerGeoSettings;note('GEO-настройки сохранены');return render();
    }
    const endpoint=type==='application'?'/api/agent-applications':'/api/support-tickets';const body=type==='application'?data:{subject:data.subject,category:data.category,body:data.body};const response=await api(endpoint,{method:'POST',body:JSON.stringify(body)});if(!response.ok)throw new Error(await readError(response));
    if(type==='application'){sessionStorage.removeItem('agent-form');state.form={};await refreshAccount();note(c.applicationSent);go('apply')}else{note(c.ticketSent);go('support')}
  }catch(error){note(error.message||c.error)}finally{if(button)button.disabled=false}
});
if(supportsBack)tg.BackButton.onClick(()=>go('home'));load();
