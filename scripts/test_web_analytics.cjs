const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('src/static/js/web_analytics.js', 'utf8');

function runtime(storage = {}, queue = []) {
  const calls = [], listeners = {};
  const context = {window: {gtag: (...args) => calls.push(args)},
    document: {addEventListener: (name, fn) => {listeners[name] = fn;},
      getElementById: () => ({textContent: JSON.stringify(queue)})},
    sessionStorage: {getItem: key => storage[key] || null,
      setItem: (key, value) => {storage[key] = value;}}};
  vm.runInNewContext(code, context);
  return {context, calls, listeners, track: context.window.webAnalytics.track};
}

test('generation fires once across duplicate HTMX events and page reloads', () => {
  const storage = {}, first = runtime(storage);
  const detail = {event_id: 'unique-generation', landing_path: '/situations/how-to-respond-to-wyd/'};
  first.listeners.replyGenerated({detail});
  first.listeners.replyGenerated({detail});
  assert.equal(first.calls.length, 1);
  const second = runtime(storage);
  assert.equal(second.track('reply_generated', detail), false);
  assert.equal(second.calls.length, 0);
});

test('signup queue is deduplicated and arbitrary content is excluded', () => {
  const app = runtime({}, [{name: 'sign_up', parameters: {event_id: 'signup-1',
    acquisition_source: 'google', conversation_text: 'private message', email: 'private@example.com'}}]);
  app.listeners.DOMContentLoaded();
  app.listeners.DOMContentLoaded();
  assert.equal(app.calls.length, 1);
  assert.deepEqual(Object.keys(app.calls[0][2]).sort(), ['acquisition_source', 'event_id']);
});

test('copy actions stay distinct; blocked storage or missing GA never breaks the UI', () => {
  const app = runtime();
  app.context.sessionStorage.setItem = () => {throw new Error('blocked');};
  assert.equal(app.track('copy_suggestion', {event_id: 'copy-1'}), true);
  assert.equal(app.track('copy_suggestion', {event_id: 'copy-2'}), true);
  assert.equal(app.track('unknown', {event_id: 'x'}), false);
  delete app.context.window.gtag;
  assert.equal(app.track('reply_generated', {event_id: 'no-ga'}), false);
  assert.equal(app.calls.length, 2);
});
