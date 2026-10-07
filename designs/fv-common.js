(() => {
  'use strict';
  let cleanup;
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function playIntro() {
    clearTimeout(cleanup);
    document.querySelector('.concept-intro')?.remove();
    document.body.classList.remove('concept-reveal');
    if (reduced()) return;
    const layer = document.createElement('div');
    layer.className = 'concept-intro';
    layer.setAttribute('aria-hidden', 'true');
    const logo = document.createElement('img');
    logo.src = '../img/logo_1-1.png';
    logo.alt = '';
    logo.width = 300;
    logo.height = 137;
    const caption = document.createElement('p');
    caption.textContent = 'ライフスタイルに、音楽をプラス。';
    layer.append(logo, caption);
    document.body.append(layer);
    void document.body.offsetWidth;
    document.body.classList.add('concept-reveal');
    cleanup = setTimeout(() => {
      layer.remove();
      document.body.classList.remove('concept-reveal');
    }, 2800);
  }
  const nav = document.querySelector('.concept-nav');
  if (nav) {
    nav.id = 'concept-menu';
    const toggle = document.createElement('button');
    toggle.className = 'concept-menu-toggle';
    toggle.type = 'button';
    toggle.setAttribute('aria-label', 'メニューを開閉');
    toggle.setAttribute('aria-controls', nav.id);
    toggle.setAttribute('aria-expanded', 'false');
    toggle.append(document.createElement('span'), document.createElement('span'));
    document.querySelector('.concept-header').append(toggle);
    const close = () => {nav.classList.remove('is-open'); toggle.setAttribute('aria-expanded','false');};
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      nav.classList.toggle('is-open', !expanded);
      toggle.setAttribute('aria-expanded', String(!expanded));
    });
    document.addEventListener('keydown', e => {
      if(e.key === 'Escape' && nav.classList.contains('is-open')) {close();toggle.focus();}
    });
    nav.addEventListener('click', e => {if(e.target.closest('a')) close();});
    window.matchMedia('(min-width: 801px)').addEventListener('change', close);
  }
  window.addEventListener('message', e => {
    if (e.origin !== window.location.origin || e.source !== window.parent) return;
    if (e.data?.type === 'modeplus:replay') playIntro();
  });
  // Comparison switches stay immediate; standalone concepts open with the logo.
  if (window.self === window.top || new URLSearchParams(window.location.search).get('intro') === '1') playIntro();
})();
