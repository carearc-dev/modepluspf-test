(() => {
  'use strict';

  const root = document.documentElement;
  const INTRO_DELAY_MS = 800;
  const INTRO_FAILSAFE_MS = 3000;
  const INTRO_ANIMATION_MS = 2300;
  const INTRO_STORAGE_KEY = 'modeplus-intro-seen';
  const DESKTOP_QUERY = '(min-width: 1081px)';

  let introTimer;
  let failSafeTimer;
  let introAnimationTimer;

  const safeGet = (key) => {
    try {
      return window.sessionStorage.getItem(key);
    } catch (_) {
      return null;
    }
  };

  const safeSet = (key, value) => {
    try {
      window.sessionStorage.setItem(key, value);
    } catch (_) {
      // Private browsing and restricted storage must not prevent the site loading.
    }
  };

  const prefersReducedMotion = () => window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;

  const clearIntroTimers = () => {
    window.clearTimeout(introTimer);
    window.clearTimeout(failSafeTimer);
  };

  const clearIntroAnimation = () => {
    window.clearTimeout(introAnimationTimer);
    root.classList.remove('intro-animate');
  };

  const finishIntro = () => {
    clearIntroTimers();
    root.classList.remove('intro-running');
    root.classList.add('intro-done');
  };

  const startIntro = ({ replay = false } = {}) => {
    const intro = document.querySelector('#brand-intro');

    clearIntroTimers();
    clearIntroAnimation();
    root.classList.remove('intro-done', 'intro-skip');

    if (!intro || prefersReducedMotion()) {
      root.classList.add('intro-skip');
      finishIntro();
      return;
    }

    root.classList.add('intro-running');

    if (!replay && safeGet(INTRO_STORAGE_KEY)) {
      root.classList.add('intro-skip');
      finishIntro();
      return;
    }

    if (replay) {
      // Restart CSS keyframes even when the user requests a second playback.
      void root.offsetWidth;
    }
    root.classList.add('intro-animate');
    safeSet(INTRO_STORAGE_KEY, 'true');
    introTimer = window.setTimeout(finishIntro, INTRO_DELAY_MS);
    failSafeTimer = window.setTimeout(finishIntro, INTRO_FAILSAFE_MS);
    introAnimationTimer = window.setTimeout(() => {
      root.classList.remove('intro-animate');
    }, INTRO_ANIMATION_MS);
  };

  const setupReveals = () => {
    const revealItems = [...document.querySelectorAll('[data-reveal]')];
    if (!revealItems.length) return;

    const revealAll = () => revealItems.forEach((item) => {
      item.classList.add('is-visible');
    });

    if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
      revealAll();
      return;
    }

    try {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

      // Only hide elements after the observer has been created successfully.
      revealItems.forEach((item) => {
        item.classList.add('will-reveal');
        observer.observe(item);
      });
    } catch (_) {
      revealItems.forEach((item) => item.classList.remove('will-reveal'));
      revealAll();
    }
  };

  const setupMenu = () => {
    const button = document.querySelector('.menu-toggle');
    const menu = document.querySelector('#mobile-menu');
    if (!button || !menu) return;

    const desktopMedia = window.matchMedia(DESKTOP_QUERY);
    const focusFirstMenuItem = () => {
      const focusable = menu.querySelector(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      focusable?.focus();
    };
    const isOpen = () => button.getAttribute('aria-expanded') === 'true';
    const closeMenu = ({ restoreFocus = false } = {}) => {
      if (!isOpen() && menu.hidden) return;
      button.setAttribute('aria-expanded', 'false');
      menu.classList.remove('is-open');
      root.classList.remove('menu-open');
      menu.hidden = true;
      if (restoreFocus) button.focus();
    };
    const openMenu = () => {
      menu.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      menu.classList.add('is-open');
      root.classList.add('menu-open');
      window.requestAnimationFrame(focusFirstMenuItem);
    };

    button.addEventListener('click', () => {
      if (isOpen()) closeMenu({ restoreFocus: true });
      else openMenu();
    });

    menu.addEventListener('click', (event) => {
      if (event.target.closest('a[href]')) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && isOpen()) {
        closeMenu({ restoreFocus: true });
      }
    });

    const closeOnDesktop = () => {
      if (desktopMedia.matches) closeMenu();
    };
    if (desktopMedia.addEventListener) desktopMedia.addEventListener('change', closeOnDesktop);
    else desktopMedia.addListener(closeOnDesktop);
    window.addEventListener('resize', closeOnDesktop, { passive: true });
  };

  const setupReplay = () => {
    document.querySelectorAll('[data-replay-intro]').forEach((control) => {
      control.addEventListener('click', (event) => {
        event.preventDefault();
        startIntro({ replay: true });
      });
    });
  };

  const initialize = () => {
    try {
      setupReveals();
      setupMenu();
      setupReplay();
      startIntro();
    } catch (_) {
      // A non-critical enhancement must never leave the first view obscured.
      finishIntro();
      document.querySelectorAll('[data-reveal]').forEach((item) => {
        item.classList.remove('will-reveal');
        item.classList.add('is-visible');
      });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();
