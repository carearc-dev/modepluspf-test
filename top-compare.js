(() => {
  const preview = document.querySelector('#site-preview');
  const frame = document.querySelector('#device-frame');
  const label = document.querySelector('#preview-label');
  const variants = {
    a: { src: 'index.html', title: 'A案：写真が主役の、静かな教室案', label: '写真が主役の、静かな教室案' },
    b: { src: 'top-b.html', title: 'B案：音楽と暮らしのマガジン案', label: '音楽と暮らしのマガジン案' }
  };

  function chooseVariant(button) {
    const variant = variants[button.dataset.variant];
    if (!variant || preview.getAttribute('src') === variant.src) return;
    document.querySelectorAll('.variant-button').forEach((item) => {
      const selected = item === button;
      item.classList.toggle('is-current', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    preview.title = variant.title;
    label.innerHTML = `<span>${button.dataset.variant.toUpperCase()}</span> ${variant.label}`;
    preview.src = variant.src;
  }

  document.querySelectorAll('.variant-button').forEach((button) => {
    button.addEventListener('click', () => chooseVariant(button));
  });

  document.querySelectorAll('.device-button').forEach((button) => {
    button.addEventListener('click', () => {
      const mobile = button.dataset.device === 'mobile';
      frame.classList.toggle('is-mobile', mobile);
      document.querySelectorAll('.device-button').forEach((item) => {
        const selected = item === button;
        item.classList.toggle('is-current', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
    });
  });
})();
