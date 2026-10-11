#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class ClassList {
  constructor() { this.values = new Set(); }
  add(...tokens) { tokens.forEach((token) => this.values.add(token)); }
  remove(...tokens) { tokens.forEach((token) => this.values.delete(token)); }
  contains(token) { return this.values.has(token); }
}

class Target {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }
  emit(type, event = {}) {
    (this.listeners.get(type) || []).forEach((callback) => callback({ type, ...event }));
  }
}

class Element extends Target {
  constructor({ throwOnListener = false } = {}) {
    super();
    this.classList = new ClassList();
    this.throwOnListener = throwOnListener;
  }
  addEventListener(type, callback, options) {
    if (this.throwOnListener) throw new Error('listener unavailable');
    super.addEventListener(type, callback, options);
  }
  contains(element) { return element === this || element?.parent === this; }
}

const makeEnvironment = ({ scrollY = 0, throwOnHeaderListener = false } = {}) => {
  const root = new Element();
  const header = new Element({ throwOnListener: throwOnHeaderListener });
  const document = new Target();
  document.documentElement = root;
  document.readyState = 'complete';
  document.activeElement = null;
  document.querySelector = (selector) => {
    if (selector === '.site-header') return header;
    return null;
  };
  document.querySelectorAll = () => [];

  const window = new Target();
  window.scrollY = scrollY;
  window.pageYOffset = 0;
  window.sessionStorage = { getItem: () => null, setItem: () => {} };
  window.matchMedia = () => ({ matches: false, addEventListener: () => {}, addListener: () => {} });
  window.requestAnimationFrame = (callback) => {
    callback();
    return 1;
  };
  window.setTimeout = () => 1;
  window.clearTimeout = () => {};

  return { root, header, document, window };
};

const run = (options) => {
  const environment = makeEnvironment(options);
  const source = fs.readFileSync(path.join(__dirname, '..', 'home.js'), 'utf8');
  vm.runInNewContext(source, {
    document: environment.document,
    window: environment.window,
    IntersectionObserver: undefined,
  }, { filename: 'home.js' });
  return environment;
};

{
  const { root, window } = run();
  assert.equal(root.classList.contains('header-enhanced'), true, 'header enhancement should initialise');
  assert.equal(root.classList.contains('header-visible'), false, 'header starts hidden at the hero top');

  window.scrollY = 90;
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), true, 'header appears from 90px');

  window.scrollY = 40;
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), true, 'middle range keeps visible state');

  window.scrollY = 24;
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), false, 'header hides again at the hero top');
}

{
  const { root, window } = run({ scrollY: 120 });
  assert.equal(root.classList.contains('header-visible'), true, 'restored mid-page loads show the header');
  window.scrollY = 0;
  window.emit('pageshow');
  assert.equal(root.classList.contains('header-visible'), false, 'pageshow also re-evaluates restored scroll');
}

{
  const { root, header, document, window } = run();
  header.emit('focusin');
  window.scrollY = 0;
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), true, 'keyboard focus keeps the header visible');

  document.activeElement = null;
  header.emit('focusout');
  assert.equal(root.classList.contains('header-visible'), false, 'header hides after focus leaves at the hero top');

  root.classList.add('menu-open');
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), true, 'an open menu keeps the header visible');
  root.classList.remove('menu-open');
  window.emit('scroll');
  assert.equal(root.classList.contains('header-visible'), false, 'header can hide after the menu closes');
}

{
  const { root } = run({ throwOnHeaderListener: true });
  assert.equal(root.classList.contains('header-enhanced'), false, 'a failed enhancement fails open');
  assert.equal(root.classList.contains('header-visible'), false, 'fail-open does not leave a visibility class behind');
}

console.log('PASS: header scroll motion, focus/menu safety, history restoration, and fail-open behaviour');
