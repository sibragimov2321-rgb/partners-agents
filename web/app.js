import { branding } from './config/branding.js';
import { icon } from './ui.js';
import * as screens from './screens.js';
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();
const header=document.querySelector('#header'),content=document.querySelector('#content'),bottomNav=document.querySelector('#bottomNav'),toast=document.querySelector('#toast');
const state={view:'home',account:null,loading:true,form:JSON.parse(sessionStorage.getItem('agent-form')||'{}')};
const nav=[['home','Главная','home'],['stats','Статистика','chart'],['profile','Кабинет','user']];
const api=(path,options={})=>fetch(path,{...options,headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||'',...(options.headers||{})}});
function note(text){toast.textContent=text;toast.classList.add('show');clearTimeout(note.t);note.t=setTimeout(()=>toast.classList.remove('show'),2600)}
function headerView(){header.innerHTML=`<button class="portal-mark" data-nav="home">PA</button><div class="portal-title"><b>${branding.name} Agent</b><span>AGENT SERVICE</span></div><button class="header-avatar" data-nav="profile">${(state.account?.telegram?.first_name||'P')[0]}</button>`}
function render(){const routes={home:()=>screens.home(state.account),stats:()=>screens.stats(state.account),profile:()=>screens.profile(state.account),apply:()=>screens.application(state.form),check:()=>screens.check(state.account),instructions:screens.instructions,support:screens.support,ticket:screens.ticket};headerView();content.innerHTML=state.loading?screens.loading():(routes[state.view]||routes.home)();bottomNav.innerHTML=nav.map(([v,l,i])=>`<button class="nav-item ${state.view===v?'active':''}" data-nav="${v}">${icon(i)}<span>${l}</span></button>`).join('');if(tg?.BackButton)state.view==='home'?tg.BackButton.hide():tg.BackButton.show()}
function go(view){state.view=view;tg?.HapticFeedback?.impactOccurred?.('light');render();scrollTo({top:0,behavior:'smooth'})}
async function load(){try{const r=await api('/api/me');if(r.ok)state.account=await r.json()}catch{}finally{state.loading=false;render()}}
document.addEventListener('click',e=>{const target=e.target.closest('[data-nav]');if(target)go(target.dataset.nav)});
document.addEventListener('input',e=>{if(e.target.closest('[data-form="application"]')){state.form={...state.form,[e.target.name]:e.target.value};sessionStorage.setItem('agent-form',JSON.stringify(state.form))}});
document.addEventListener('submit',async e=>{const form=e.target,type=form.dataset.form;if(!type)return;e.preventDefault();const button=form.querySelector('[type="submit"]');button.disabled=true;const data=Object.fromEntries(new FormData(form));try{const endpoint=type==='application'?'/api/agent-applications':'/api/support-tickets';const body=type==='application'?data:{subject:data.subject,category:data.category,body:data.body};const r=await api(endpoint,{method:'POST',body:JSON.stringify(body)});if(!r.ok)throw Error();if(type==='application'){sessionStorage.removeItem('agent-form');state.form={};await load();note('Заявка отправлена');go('home')}else{note('Обращение отправлено');go('support')}}catch{note('Не удалось выполнить действие. Откройте приложение в Telegram и попробуйте снова.')}finally{button.disabled=false}});
tg?.BackButton?.onClick(()=>go('home'));load();
