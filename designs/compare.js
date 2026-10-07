(() => {
  'use strict';
  const variants = {
    a: {name: '余白と親しみ', tag:'A / EDITORIAL', text:'写真の表情を明るく見せ、余白と赤いアクセントで、子どもにも大人にも親しみやすく。'},
    b: {name: '音楽のリズム', tag:'B / PLAYFUL', text:'子ども・大人・親子の写真をリズミカルに配置。やわらかな色と曲線で、楽しさを前面に。'},
    c: {name: '教室の空気感', tag:'C / CINEMATIC', text:'実際のレッスン風景を大きく見せる構成。白い文字パネルで、写真の明るさと読みやすさを両立。'}
  };
  const frame = document.querySelector('#concept-preview');
  const panel = document.querySelector('#preview-panel');
  const note = document.querySelector('#concept-note');
  const openLink = document.querySelector('#open-concept');
  const tabs = [...document.querySelectorAll('[data-concept]')];
  const devices = [...document.querySelectorAll('[data-device]')];
  let selected = 'a';
  let device = 'wide';
  function persist() {
    const url = new URL(window.location.href);
    url.searchParams.set('concept', selected);
    url.searchParams.set('view', device);
    history.replaceState(null, '', url);
  }
  function select(value) {
    if (!Object.hasOwn(variants, value)) return;
    selected = value;
    tabs.forEach(tab => {
      const active = tab.dataset.concept === value;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    const variant = variants[value];
    const src = `designs/fv-${value}.html`;
    if (frame.getAttribute('src') !== src) frame.src = src;
    frame.title = `${value.toUpperCase()}案：${variant.name} デザインプレビュー`;
    panel.setAttribute('aria-labelledby', `tab-${value}`);
    openLink.href = src;
    const tag = document.createElement('b');
    tag.textContent = variant.tag;
    note.replaceChildren(tag, document.createTextNode(` ${variant.text}`));
    persist();
  }
  function setDevice(value) {
    device = value === 'mobile' ? 'mobile' : 'wide';
    panel.classList.toggle('is-mobile', device === 'mobile');
    devices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.device === device)));
    persist();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(tab.dataset.concept));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      tabs[next].focus();
      select(tabs[next].dataset.concept);
    });
  });
  devices.forEach(button => button.addEventListener('click', () => setDevice(button.dataset.device)));
  document.querySelector('#replay').addEventListener('click', () => frame.contentWindow?.postMessage({type:'modeplus:replay'}, window.location.origin));
  const params = new URLSearchParams(window.location.search);
  select(params.get('concept') || 'a');
  setDevice(params.get('view'));
})();
