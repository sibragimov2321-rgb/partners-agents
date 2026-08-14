const paths = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path d="M9 21v-6h6v6"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3.5 20v-1.5A4.5 4.5 0 0 1 8 14h2a4.5 4.5 0 0 1 4.5 4.5V20M16 5.5a3 3 0 0 1 0 5.7M18 14a4.5 4.5 0 0 1 2.5 4V20"/>',
  briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-4.5-4.5L7 20"/>',
  search: '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.2-4.2"/>',
  shield: '<path d="M12 3 20 7v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7Z"/><path d="m9 12 2 2 4-4"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.2 1.8c-.9.8-1.8 1.3-1.8 2.7M12 16.8h.01"/>',
  message: '<path d="M20 14a4 4 0 0 1-4 4H9l-5 3v-7a4 4 0 0 1-1-2.7V8a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4Z"/><path d="M8 10h8M8 13h5"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  bell: '<path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  arrow: '<path d="m9 18 6-6-6-6"/>', back: '<path d="m15 18-6-6 6-6"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.2-1.2"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/>',
  chart: '<path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/>',
  check: '<path d="m5 12 4 4L19 6"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M17 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h6"/>',
};
export const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.home}</svg>`;
export const esc = (value = '') => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char]);
export const emptyStat = (label, symbol) => `<article class="stat-card"><i>${icon(symbol)}</i><small>${label}</small><strong class="empty">—</strong></article>`;
export const pageHead = (title, subtitle = '') => `<div class="page-head"><button class="back-button" data-nav="home" aria-label="Back">${icon('back')}</button><div><h1>${title}</h1>${subtitle ? `<p>${subtitle}</p>` : ''}</div></div>`;
