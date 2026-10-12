#!/usr/bin/env node
'use strict';

const path = require('node:path');
const assert = require('node:assert/strict');

class Tokens {
  constructor(values = []) { this.values = new Set(values); }
  toggle(token, force) { const on = force === undefined ? !this.values.has(token) : force; if (on) this.values.add(token); else this.values.delete(token); return on; }
  contains(token) { return this.values.has(token); }
}
class Element {
  constructor({ dataset = {}, classes = [], attributes = {} } = {}) { this.dataset = dataset; this.classList = new Tokens(classes); this.attributes = { ...attributes }; this.listeners = {}; this.innerHTML = ''; this.title = ''; this.sourceChanges = 0; }
  get src() { return this.attributes.src ?? ''; }
  set src(value) { this.attributes.src = value; this.sourceChanges += 1; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  click() { this.listeners.click(); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
}

const a = new Element({ dataset: { variant: 'a', src: 'index.html' }, classes: ['variant-button', 'is-current'], attributes: { 'aria-pressed': 'true' } });
const b = new Element({ dataset: { variant: 'b', src: 'top-b.html' }, classes: ['variant-button'], attributes: { 'aria-pressed': 'false' } });
const desktop = new Element({ dataset: { device: 'desktop' }, classes: ['device-button', 'is-current'], attributes: { 'aria-pressed': 'true' } });
const mobile = new Element({ dataset: { device: 'mobile' }, classes: ['device-button'], attributes: { 'aria-pressed': 'false' } });
const preview = new Element({ attributes: { src: 'index.html' } });
const frame = new Element();
const label = new Element();
global.document = { querySelector: (selector) => ({ '#site-preview': preview, '#device-frame': frame, '#preview-label': label }[selector] || null), querySelectorAll: (selector) => ({ '.variant-button': [a, b], '.device-button': [desktop, mobile] }[selector] || []) };

require(path.resolve(__dirname, '..', 'top-compare.js'));
a.click();
assert.equal(preview.sourceChanges, 0, 'choosing the current design does not reload it');
b.click();
assert.equal(preview.src, 'top-b.html');
assert.equal(preview.title, 'B案：音楽のアトリエ案');
assert.match(label.innerHTML, />B<\/span> 音楽のアトリエ案/);
assert.equal(a.attributes['aria-pressed'], 'false');
assert.equal(b.attributes['aria-pressed'], 'true');
assert.equal(b.classList.contains('is-current'), true);
b.click();
assert.equal(preview.sourceChanges, 1, 'choosing B again preserves its scroll position');
mobile.click();
assert.equal(frame.classList.contains('is-mobile'), true);
assert.equal(mobile.attributes['aria-pressed'], 'true');
assert.equal(desktop.attributes['aria-pressed'], 'false');
a.click();
assert.equal(preview.src, 'index.html', 'switching back to A updates the iframe source');
assert.equal(preview.title, 'A案：写真が主役の、静かな教室案');
assert.match(label.innerHTML, />A<\/span>/);
assert.equal(a.attributes['aria-pressed'], 'true');
assert.equal(b.attributes['aria-pressed'], 'false');
assert.equal(a.classList.contains('is-current'), true);
assert.equal(b.classList.contains('is-current'), false);
assert.equal(frame.classList.contains('is-mobile'), true, 'changing design retains the selected device width');
desktop.click();
assert.equal(frame.classList.contains('is-mobile'), false);
assert.equal(desktop.classList.contains('is-current'), true);
assert.equal(mobile.attributes['aria-pressed'], 'false');
console.log('PASS: comparison variant and device controls respond with accessible state');
