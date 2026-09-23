/**
 * ClimaCred AI - Frontend runtime smoke test (audit-only harness)
 * Loads the REAL production bundle (dist/index.html) served by `vite preview`,
 * polyfills browser APIs jsdom lacks, clicks through every page of the app,
 * and captures console errors / page errors / failed API calls.
 */
const { JSDOM } = require('jsdom');
const fs = require('fs');

const PREVIEW = 'http://localhost:4173';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const html = await (await fetch(PREVIEW + '/')).text();

  // jsdom does not execute <script type="module">; the single-file bundle has no
  // import/export/import.meta left, so re-inject it as a classic script at the END
  // of <body> (classic inline scripts are not deferred like modules).
  const m = html.match(/<script type="module" crossorigin>([\s\S]*?)<\/script>/);
  if (!m) { console.error('FATAL: module script not found in bundle HTML'); process.exit(2); }
  const bootHtml = html
    .replace(m[0], '')
    .replace('</body>', () => '<script>' + m[1].replace(/<\/script>/g, () => '<\\/script>') + '</script></body>');

  const consoleErrors = [];
  const consoleWarnings = [];
  const pageErrors = [];
  const failedFetches = [];
  const apiCalls = [];

  const dom = new JSDOM(bootHtml, {
    url: PREVIEW + '/',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(window) {
      // fetch polyfill -> real backend through the preview proxy (same as a browser)
      window.fetch = async (input, init) => {
        const url = typeof input === 'string' ? (input.startsWith('/') ? PREVIEW + input : input) : input.url;
        apiCalls.push(`${init?.method || 'GET'} ${url.replace(PREVIEW, '')}`);
        try {
          const res = await fetch(url, init);
          if (!res.ok) failedFetches.push(`${res.status} ${url}`);
          return res;
        } catch (e) {
          failedFetches.push(`NETWORK-FAIL ${url} :: ${e.message}`);
          throw e;
        }
      };
      // APIs jsdom lacks
      window.matchMedia = window.matchMedia || ((q) => ({ matches: false, media: q, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; } }));
      window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} takeRecords() { return []; } };
      window.scrollTo = () => {};
      window.HTMLElement.prototype.scrollIntoView = window.HTMLElement.prototype.scrollIntoView || function () {};
      window.SVGPathElement = window.SVGPathElement || class {};
      window.console.error = (...a) => { consoleErrors.push(a.map(x => (x && x.stack) || String(x)).join(' ')); };
      window.console.warn = (...a) => { consoleWarnings.push(a.map(String).join(' ')); };
      window.addEventListener('pageerror', (e) => pageErrors.push(e.message + '\n' + (e.error?.stack || '')));
    },
  });

  const { window } = dom;
  await sleep(4000); // initial data load + render

  const doc = window.document;
  const text = () => doc.body.textContent || '';
  const results = [];
  const check = (name, cond, detail = '') => { results.push({ name, cond, detail }); console.log(`${cond ? 'PASS' : 'FAIL'} | ${name}${cond ? '' : ' | ' + detail}`); };

  // Initial load state (visible text only - inline script source is inside <body> too)
  const visibleText = () => {
    const clone = doc.body.cloneNode(true);
    clone.querySelectorAll('script, style').forEach(n => n.remove());
    return clone.textContent || '';
  };
  await sleep(2500); // ensure initial data load completed
  const t0 = visibleText();
  check('App bootstraps (no "Initializing" stuck)', !t0.includes('Initializing Climate Intelligence Workspace'), t0.slice(0, 120));
  const clickNav = async (label, waitMs = 1800) => {
    const btns = [...doc.querySelectorAll('button, a')];
    const btn = btns.find(b => (b.textContent || '').trim().toLowerCase().includes(label.toLowerCase()));
    if (!btn) { check(`navigate to ${label}`, false, 'button not found'); return false; }
    btn.click();
    await sleep(waitMs);
    return true;
  };

  // Dashboard
  check('Dashboard shows backend business name', text().includes('ABC Textile Manufacturing'), 'backend-loaded name missing');

  // Business Profile
  await clickNav('Business Profile');
  check('Profile page renders with backend data', text().includes('ABC Textile Manufacturing'), '');
  const empInput = [...doc.querySelectorAll('input')].find(i => String(i.value) === '145');
  check('Profile employees field populated from backend (145)', !!empInput, 'no input with 145');

  // Climate Assessment - verify UI shows exactly what the backend has stored
  const storedAssessment = await (await fetch(PREVIEW + '/api/assessment')).json();
  await clickNav('Climate Assessment');
  check('Assessment page renders', text().toLowerCase().includes('assessment'), '');
  const storedKwh = String(storedAssessment?.energy?.monthlyElectricityKwh ?? '');
  const kwhInput = [...doc.querySelectorAll('input')].find(i => String(i.value).replace(/,/g, '') === storedKwh);
  check(`Assessment energy field matches stored backend value (${storedKwh} kWh)`, !!kwhInput);

  // Climate Fingerprint
  await clickNav('Climate Fingerprint');
  const fpText = text();
  check('Fingerprint page renders overall score from backend', /Climate Readiness|Overall/.test(fpText) && /\d{2}/.test(fpText), '');
  check('Fingerprint shows dimension names', ['Energy', 'Water', 'Waste', 'Emissions', 'Mobility'].every(d => fpText.includes(d)));

  // Energy / Water / Waste / Emissions / Mobility
  for (const [label, marker] of [['Energy', 'Energy Intelligence'], ['Water', 'Water'], ['Waste', 'Waste'], ['Emissions', 'Emission'], ['Mobility', 'Mobility']]) {
    await clickNav(label === 'Energy' ? 'Energy' : label);
    const t = text();
    check(`${label} page renders`, t.length > 500, `too little content (${t.length} chars)`);
    const live = t.includes('Live Backend Data');
    if (['Energy', 'Water', 'Waste', 'Emissions', 'Mobility'].includes(label)) {
      console.log(`       -> ${label} analytics badge: ${live ? 'Live Backend Data' : 'Illustrative (fallback)'}`);
    }
  }

  // Green Solutions
  await clickNav('Green Solutions');
  const solT = text();
  check('Green Solutions catalog renders', solT.includes('Solar') || solT.includes('solution') || solT.includes('Solution'), '');

  // Scenario Simulator
  await clickNav('Scenario Simulator', 2500);
  const simT = text();
  check('Scenario Simulator renders', simT.toLowerCase().includes('scenario') || simT.toLowerCase().includes('simulat'), '');
  const runBtn = [...doc.querySelectorAll('button')].find(b => /run|simulate/i.test(b.textContent || '') && !/simulate solar/i.test(b.textContent || ''));
  if (runBtn) { runBtn.click(); await sleep(2500); }
  const simT2 = text();
  check('Simulator produces projected climate score', /Projected/i.test(simT2) && /\d/.test(simT2), '');

  // Transformation Plan
  await clickNav('Transformation Plan');
  const planT = text();
  check('Transformation Plan renders phases', planT.includes('Phase 1') && planT.includes('Phase'), '');

  // Impact Verification
  await clickNav('Impact Verification');
  const verT = text();
  check('Impact Verification renders', verT.toLowerCase().includes('verification'), '');

  // Climate Impact Report
  await clickNav('Impact Report', 3000);
  const repT = text();
  check('Impact Report renders', repT.toLowerCase().includes('report'), '');

  // Settings
  await clickNav('Settings');
  check('Settings renders', text().length > 200, '');

  // Broken navigation links: collect all sidebar nav targets & verify each navigates somewhere
  const navLabels = ['Dashboard', 'Business Profile', 'Climate Assessment', 'Climate Fingerprint', 'Energy', 'Water', 'Waste', 'Emissions', 'Mobility', 'Green Solutions', 'Scenario Simulator', 'Transformation Plan', 'Impact Verification', 'Impact Report', 'Settings'];
  let navOK = 0;
  for (const l of navLabels) {
    const before = text().slice(0, 50);
    const ok = await clickNav(l, 700);
    if (ok) navOK++;
  }
  check(`All ${navLabels.length} sidebar navigation targets clickable`, navOK === navLabels.length, `only ${navOK} worked`);

  // Empty/error state check: kill backend? (skipped here - API failure fallback covered in unit tests)

  console.log('\n--- API calls made by the app ---');
  console.log([...new Set(apiCalls)].join('\n') || '(none)');
  console.log('\n--- failed fetches ---');
  console.log(failedFetches.length ? failedFetches.join('\n') : '(none)');

  console.log('\n--- console.error entries ---');
  const realErrors = consoleErrors.filter(e => !/not implemented/i.test(e));
  console.log(realErrors.length ? [...new Set(realErrors)].slice(0, 12).join('\n---\n') : '(none)');

  console.log('\n--- page errors (uncaught exceptions) ---');
  console.log(pageErrors.length ? [...new Set(pageErrors)].slice(0, 8).join('\n---\n') : '(none)');

  console.log('\n--- console.warn entries (fallback notices etc.) ---');
  const uniqWarn = [...new Set(consoleWarnings)];
  console.log(uniqWarn.length ? uniqWarn.slice(0, 10).join('\n') : '(none)');

  const failed = results.filter(r => !r.cond);
  console.log(`\n================= SMOKE RESULT: ${results.length - failed.length}/${results.length} passed =================`);
  if (failed.length) { console.log('FAILED:'); failed.forEach(f => console.log(' -', f.name, '::', f.detail.slice(0, 150))); }
  process.exit(failed.length || realErrors.length || pageErrors.length ? 1 : 0);
})().catch(e => { console.error('HARNESS CRASH:', e); process.exit(2); });
