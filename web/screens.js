import { branding } from './config/branding.js';
import { esc, icon, emptyStat, pageHead } from './ui.js';

const button = (label, attr = '', variant = 'ghost') => `<button class="button ${variant}" ${attr}>${label}</button>`;
const card = (iconName, title, description, target) => `<button class="quick-card" data-nav="${target}"><i class="quick-icon">${icon(iconName)}</i><strong>${title}</strong><small>${description}</small></button>`;
const formField = (label, name, type = 'text', required = false, placeholder = '') => `<label class="field"><span>${label}</span>${type === 'textarea' ? `<textarea name="${name}" ${required ? 'required' : ''} placeholder="${placeholder}"></textarea>` : `<input name="${name}" type="${type}" ${required ? 'required' : ''} placeholder="${placeholder}">`}</label>`;

export function home({ user }) {
  const userName = esc(user?.first_name || user?.username || 'there');
  return `<div class="view">
    <section class="hero"><p class="hero-eyebrow">PARTNER PROGRAM</p><h1>Welcome, ${userName}</h1><p>Your workspace for applications, materials, support and your future dashboard.</p><div class="button-row">${button(`Start now ${icon('arrow')}`, 'data-nav="partners"', 'primary')}<span class="status-badge">Guest account</span></div></section>
    <div class="section-head"><h2>Start here</h2></div>
    <section class="quick-grid">
      ${card('briefcase', 'Agents', 'Apply or sign in', 'agents')}
      ${card('users', 'Partners', 'Create a profile', 'partners')}
      ${card('image', 'Get banner', 'Media library', 'banners')}
      ${card('shield', 'Check contact', 'Availability & block list', 'contact')}
    </section>
    <section class="account-card"><div class="account-top"><i>${icon('user')}</i><div><h3>Your account</h3><p>${user?.username ? `@${esc(user.username)}` : 'Telegram account connected'}</p></div></div><div class="account-empty"><b>Profile details will unlock after approval</b>Affiliate ID · Agent ID · GEO · personal link and status will appear here.</div></section>
    <div class="section-head"><h2>Overview</h2><button data-nav="profile">View profile</button></div>
    <section class="stats-row">${emptyStat('Players', 'users')}${emptyStat('Deposits', 'chart')}${emptyStat('Withdrawals', 'chart')}${emptyStat('Revenue', 'chart')}${emptyStat('Conversion', 'chart')}</section>
    <section class="panel activity-panel"><div class="section-head"><h2>Recent activity</h2></div><div class="activity-empty">${icon('chart')}<b>No activity yet</b><p>Your applications and account updates will appear here.</p></div></section>
  </div>`;
}

function roleScreen(kind) {
  const isAgent = kind === 'agent';
  const title = isAgent ? 'Agents' : 'Partners';
  const description = isAgent ? 'Work with clients and grow an agent profile.' : 'Build traffic partnerships and manage promotional materials.';
  return `<div class="view">${pageHead(title, description)}
    <section class="panel role-card"><h3>Become a ${isAgent ? 'agent' : 'partner'}</h3><p>Send your details. A manager will review the application and contact you in Telegram.</p>${button('Start application', `data-nav="${isAgent ? 'agent-application' : 'partner-application'}"`, 'primary')}</section>
    <section class="panel role-card"><h3>I already have an account</h3><p>Your Telegram ID is used as the main identifier. The workspace will open after approval.</p>${button('Open my profile', 'data-nav="profile"')}</section>
  </div>`;
}
export const agents = () => roleScreen('agent');
export const partners = () => roleScreen('partner');

export function application(kind) {
  const isAgent = kind === 'agent';
  return `<div class="view">${pageHead(isAgent ? 'Agent application' : 'Partner application', 'Required fields are marked with an asterisk.')}
    <section class="form-card"><form class="form" data-form="application" data-kind="${kind}">
      ${formField('Name *', 'name', 'text', true, 'Your name')}
      ${isAgent ? `${formField('Country *', 'country', 'text', true, 'Country')}${formField('City', 'city', 'text', false, 'City')}${formField('Phone *', 'phone', 'tel', true, '+1 000 000 00 00')}` : `${formField('Email *', 'email', 'email', true, 'name@example.com')}${formField('GEO *', 'geo', 'text', true, 'Country / region')}${formField('Traffic source *', 'traffic', 'text', true, 'Website, channel, social network')}`}
      ${formField('Email *', 'email', 'email', true, 'name@example.com')}
      ${formField(isAgent ? 'Experience' : 'Expected volume', 'experience', 'text', false, isAgent ? 'Tell us about your experience' : 'Estimated monthly volume')}
      ${formField('Comment', 'comment', 'textarea', false, 'Anything else we should know?')}
      <label class="consent"><input required type="checkbox"> <span>I agree to the terms and to processing this application.</span></label>
      ${button('Send application', 'type="submit"', 'primary')}
    </form></section>
  </div>`;
}

export function banners() {
  const cards = [['Partners launch', 'Partners', '1200 × 628'], ['Telegram story', 'Telegram', '1080 × 1920'], ['Social post', 'Posts', '1080 × 1080']];
  return `<div class="view">${pageHead('Get banner', 'Preview materials prepared for your future campaigns.')}
    <div class="tabs"><button class="tab active">All</button><button class="tab">Agents</button><button class="tab">Partners</button><button class="tab">Telegram</button><button class="tab">Stories</button></div>
    <section class="banner-grid">${cards.map(([title, geo, size]) => `<article class="banner-card"><div class="banner-preview"><span>PARTNERS</span></div><div class="banner-body"><h3>${title}</h3><div class="banner-meta"><span class="chip">${geo}</span><span class="chip">${size}</span></div><div class="button-row">${button(`Open ${icon('external')}`, 'data-action="material"', 'primary')}${button(`Copy text ${icon('copy')}`, 'data-action="copy"')}</div></div></article>`).join('')}</section>
  </div>`;
}

export function lookup({ block = false }) {
  const title = block ? 'Blocked contact' : 'Check contact';
  const text = block ? 'Enter a Telegram username, ID, email, Affiliate ID or Agent ID.' : 'Enter a Telegram username or email.';
  return `<div class="view">${pageHead(title, text)}<section class="form-card"><form class="form" data-form="lookup" data-mode="${block ? 'block' : 'contact'}"><label class="field"><span>Contact</span><div class="search-wrap"><i>${icon('search')}</i><input required name="contact" placeholder="@username, email or ID"></div></label>${button(`Check ${icon('search')}`, 'type="submit"', 'primary')}</form><div id="lookupResult" class="result-card"></div></section></div>`;
}

export function faq() {
  const partner = [['Which traffic types are allowed?', 'The available traffic types and restrictions are confirmed by a manager during approval.'], ['When are statistics updated?', 'Statistics appears after a profile and tracking integration are activated.'], ['How do payouts work?', 'Available payment methods and schedule are determined by your approved programme.']];
  const agent = [['How do I become an agent?', 'Send an application and wait for a manager review in Telegram.'], ['How do I get materials?', 'Open Get banner after your profile is activated.'], ['How can I contact a manager?', 'Use the Support screen to create a request or open Telegram support.']];
  const items = [...partner, ...agent];
  return `<div class="view">${pageHead('FAQ', 'Answers for future partners and agents.')}<div class="search-wrap"><i>${icon('search')}</i><input id="faqSearch" placeholder="Search questions"></div><div class="tabs"><button class="tab active">For partners</button><button class="tab">For agents</button></div><section class="faq-list">${items.map(([q,a]) => `<article class="faq-item" data-faq="${esc(`${q} ${a}`).toLowerCase()}"><button class="faq-question"><span>${q}</span><b>›</b></button><div class="faq-answer">${a}</div></article>`).join('')}</section></div>`;
}

export function support() {
  return `<div class="view">${pageHead('Support', 'Get help from the team or create a request.')}<section class="support-list"><button class="support-card" data-action="support"><i>${icon('message')}</i><span><strong>Telegram support</strong><small>Open the configured support chat</small></span><b>›</b></button><button class="support-card" data-action="manager"><i>${icon('user')}</i><span><strong>Write to a manager</strong><small>Personal account and applications</small></span><b>›</b></button><button class="support-card" data-nav="faq"><i>${icon('help')}</i><span><strong>Questions and answers</strong><small>Quick help for agents and partners</small></span><b>›</b></button><button class="support-card" data-nav="ticket"><i>${icon('plus')}</i><span><strong>Create a request</strong><small>Topic, category and message</small></span><b>›</b></button></section></div>`;
}

export function ticket() {
  return `<div class="view">${pageHead('New request', 'We will send the update to your Telegram account.')}<section class="form-card"><form class="form" data-form="ticket">${formField('Subject *', 'subject', 'text', true, 'What do you need help with?')}<label class="field"><span>Category</span><select name="category"><option>General question</option><option>Application</option><option>Materials</option><option>Technical issue</option></select></label>${formField('Message *', 'message', 'textarea', true, 'Describe your request')}${button('Send request', 'type="submit"', 'primary')}</form></section></div>`;
}

export function profile({ user }) {
  const displayName = esc([user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Telegram user');
  const username = user?.username ? `@${esc(user.username)}` : 'Username is not set';
  const avatar = user?.photo_url ? `<img class="avatar" src="${esc(user.photo_url)}" alt="Profile">` : `<span class="avatar">${displayName.slice(0, 1).toUpperCase()}</span>`;
  return `<div class="view">${pageHead('My profile', 'Your Telegram-based account.')}<section class="profile-card"><div class="profile-row">${avatar}<div><h3>${displayName}</h3><p>${username}</p><p>ID: ${user?.id ? esc(user.id) : 'available in Telegram'}</p></div></div><div class="settings-list"><div class="setting"><span>Role<small>Will be assigned after approval</small></span><b class="chip">Guest</b></div><div class="setting"><span>Account status<small>Application not submitted</small></span><b class="chip">New</b></div><div class="setting"><span>GEO<small>Set in your application</small></span><b>—</b></div><div class="setting"><span>Registration date<small>Will be added after application</small></span><b>—</b></div><div class="setting"><span>Language<small>Follows your Telegram settings</small></span><b>${esc(user?.language_code || 'en').toUpperCase()}</b></div></div></section></div>`;
}
