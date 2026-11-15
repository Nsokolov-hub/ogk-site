/** Consent, readiness and conversion regressions without contacting either analytics service. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText).toString('base64')}`;
const consentUrl = moduleUrl(await readFile(new URL('../src/lib/consent.ts', import.meta.url), 'utf8'));
const analyticsUrl = moduleUrl((await readFile(new URL('../src/lib/analytics.ts', import.meta.url), 'utf8'))
  .replace("from './consent'", `from '${consentUrl}'`));
process.env.NODE_ENV = 'production';
const storage = new Map();
const calls = [];
const target = new EventTarget();
globalThis.window = Object.assign(target, {
  location: { origin: 'https://www.ogk-chem.ru', href: 'https://www.ogk-chem.ru/product/sample/' },
  localStorage: { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
  ym: (...args) => calls.push(['ym', ...args]),
  gtag: (...args) => calls.push(['ga', ...args]),
});
const { setCookieConsent } = await import(consentUrl);
const { track, configureCounters, afterAnalyticsConsent, trackLeadSubmit, sanitizeAnalyticsUrl } = await import(analyticsUrl);

setCookieConsent('necessary');
let views = 0;
const disposeView = afterAnalyticsConsent(() => { views += 1; track('product_view', { sku: '1235831' }); });
assert.equal(track('form_start', { form_type: 'request' }), false);
assert.equal(views, 0);
assert.equal(window.dataLayer, undefined);
assert.equal(calls.length, 0);

// A product mounted before consent must be counted once after consent. Counter initialization may follow later.
setCookieConsent('all');
assert.equal(views, 1);
assert.equal(window.dataLayer.length, 1);
assert.equal(calls.length, 0);
configureCounters({ ym: 123, ga: 'G-TEST' });
assert.equal(calls.filter(([system]) => system === 'ym').length, 1);
assert.equal(calls.filter(([system]) => system === 'ga').length, 1);
configureCounters({ ym: 123, ga: 'G-TEST' });
setCookieConsent('all');
assert.equal(views, 1);
assert.equal(calls.length, 2);
disposeView();

assert.equal(trackLeadSubmit('subscribe', { request_id: 'subscription-1' }), false);
assert.equal(trackLeadSubmit('request', { request_id: '' }), false);
assert.equal(trackLeadSubmit('request', { request_id: 'saved-request-1' }), true);
assert.equal(trackLeadSubmit('request', { request_id: 'saved-request-1' }), false);
assert.equal(window.dataLayer.filter((event) => event.event === 'lead_submit').length, 1);

const privateLink = 'https://www.ogk-chem.ru/rfq/?repeat=SECRET&token=SECRET&utm_source=mail#repeat=SECRET';
assert.equal(sanitizeAnalyticsUrl(privateLink), 'https://www.ogk-chem.ru/rfq/?utm_source=mail');
assert.equal(sanitizeAnalyticsUrl('/public/requests/repeat/SECRET?token=SECRET'), '/public/requests/repeat/redacted');
track('form_error', { page: privateLink, token: 'SECRET', refresh_token: 'SECRET', context: { destination: privateLink, signature: 'SECRET' } });
assert.ok(!JSON.stringify(window.dataLayer.at(-1)).includes('SECRET'));
assert.ok(!JSON.stringify(calls.slice(-2)).includes('SECRET'));

setCookieConsent('necessary');
configureCounters(null);
const measured = window.dataLayer.length;
assert.equal(track('quote_request'), false);
assert.equal(window.dataLayer.length, measured);
let unmountedViews = 0;
const disposeUnmounted = afterAnalyticsConsent(() => { unmountedViews += 1; });
disposeUnmounted();
setCookieConsent('all');
assert.equal(unmountedViews, 0);
console.log('Analytics consent/readiness, real-lead deduplication and repeat-token privacy checks passed.');
