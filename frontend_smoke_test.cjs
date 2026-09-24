/**
 * ClimaCred AI - frontend runtime smoke test (audit harness)
 *
 * Loads the REAL production bundle (dist/index.html) served by `vite preview`,
 * boots it inside jsdom with a fetch polyfill pointed at the same origin (so the
 * preview server proxies /api to the backend exactly like a browser would),
 * clicks through every page and captures console errors / page errors / failed
 * API calls.
 *
 * Two modes:
 *   node frontend_smoke_test.cjs            -> empty database expectations
 *   node frontend_smoke_test.cjs --with-data-> seeds a real business first
 *
 * Preconditions: backend running on http://localhost:8000, `npm run build` done,
 * `npm run preview` running on http://localhost:4173, and `npm install jsdom`.
 */
const { JSDOM } = require('jsdom');

const PREVIEW = process.env.SMOKE_PREVIEW_URL || 'http://localhost:4173';
const API = process.env.SMOKE_API_URL || 'http://localhost:8000';
const WITH_DATA = process.argv.includes('--with-data');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const TEST_PROFILE = {
  name: 'Vertex Precision Components Pvt Ltd',
  industry: 'Manufacturing',
  businessType: 'CNC machining',
  location: 'Pune, Maharashtra',
  employees: 64,
  workingDaysPerMonth: 26,
  productionVolume: '12000 parts / month',
  operatingHoursPerDay: 16,
  businessSize: 'Small',
  facilityAreaSqFt: 22000,
  contactEmail: 'ops@example.com',
  phone: '',
};

const TEST_ASSESSMENT = {
  energy: {
    monthlyElectricityKwh: 21500,
    monthlyElectricityBillInr: 193500,
    dieselGeneratorHoursPerMonth: 40,
    generatorFuelLitresPerMonth: 480,
    existingSolarCapacityKw: 0,
    energyEfficientEquipmentPercent: 20,
  },
  water: {
    monthlyWaterLitres: 260000,
    waterSource: 'Groundwater / Borewell',
    waterRecyclingAvailable: false,
    rainwaterHarvesting: false,
    leakageFrequency: 'Monthly',
    wastewaterTreatment: 'Primary / Settling',
  },
  waste: {
    organicWasteKgPerMonth: 300,
    plasticWasteKgPerMonth: 950,
    paperWasteKgPerMonth: 400,
    industrialWasteKgPerMonth: 1850,
    textileMaterialWasteKgPerMonth: 3600,
    currentRecyclingPercent: 30,
    wasteSegregationPracticed: false,
  },
  emissions: {
    primaryFuel: 'Diesel',
    monthlyDieselLitres: 620,
    monthlyPetrolLitres: 90,
    monthlyNaturalGasKg: 0,
    mainEmissionSources: ['Grid electricity', 'Diesel genset'],
    airPollutionControlSystem: 'None',
  },
  mobility: {
    deliveryVehiclesCount: 4,
    vehicleFuelType: 'Diesel',
    monthlyFleetFuelLitres: 780,
    employeeCommuteMode: 'Two-Wheelers',
    evAdoptedPercent: 0,
  },
  greenPractices: {
    ledLighting: true,
    solarPanels: false,
    rainwaterHarvesting: false,
    waterRecycling: false,
    wasteSegregation: false,
    energyEfficientMachinery: false,
    evAdoption: false,
    sustainableMaterials: false,
  },
};

// Forbidden strings: any of these appearing in the rendered UI means fabricated
// business data leaked back into the product.
const FORBIDDEN = [
  'ABC Textile',
  'Tirupur Cluster',
  'Demo / Illustrative Data',
  '485,000',
  '38,500',
  '346,500',
  '480,000',
  '41.2 MT',
  'Medium SME Demo',
];

async function post(path, body) {
  const res = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res;
}

(async () => {
  if (WITH_DATA) {
    await post('/api/profile', TEST_PROFILE);
    await post('/api/assessment', TEST_ASSESSMENT);
    await fetch(API + '/api/climate-fingerprint'); // generate + store a snapshot
    console.log('seeded a real test business through the API');
  }

  const html = await (await fetch(PREVIEW + '/')).text();

  // jsdom does not execute <script type="module">; the single-file bundle has no
  // import/export left, so re-inject it as a classic script at the END of <body>.
  const m = html.match(/<script type="module" crossorigin>([\s\S]*?)<\/script>/);
  if (!m) {
    console.error('FATAL: module script not found in bundle HTML');
    process.exit(2);
  }
  // jsdom executes classic scripts only, so `import.meta` (left by a library for
  // asset URLs) is replaced with a shim before re-injecting the bundle.
  const bundleJs = m[1]
    .replace(/import\.meta/g, '__VITE_IMPORT_META__')
    .replace(/<\/script>/g, () => '<\\/script>');
  const bootHtml = html
    .replace(m[0], '')
    .replace(
      '</body>',
      () => '<script>window.__VITE_IMPORT_META__={url:"' + PREVIEW + '/",env:{}};</script><script>' + bundleJs + '</script></body>'
    );

  const consoleErrors = [];
  const pageErrors = [];
  const failedFetches = [];
  const apiCalls = [];

  const dom = new JSDOM(bootHtml, {
    url: PREVIEW + '/',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = async (input, init) => {
        const raw = typeof input === 'string' ? input : input.url;
        const url = raw.startsWith('/') ? API + raw : raw;
        const method = (init && init.method) || 'GET';
        apiCalls.push(`${method} ${raw.replace(API, '')}`);
        try {
          const res = await fetch(url, init);
          if (!res.ok) failedFetches.push(`${res.status} ${method} ${raw}`);
          return res;
        } catch (e) {
          failedFetches.push(`NETWORK-FAIL ${method} ${raw} :: ${e.message}`);
          throw e;
        }
      };
      window.matchMedia =
        window.matchMedia ||
        ((q) => ({
          matches: false,
          media: q,
          onchange: null,
          addListener() {},
          removeListener() {},
          addEventListener() {},
          removeEventListener() {},
          dispatchEvent() {
            return false;
          },
        }));
      window.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
      };
      window.IntersectionObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
        takeRecords() {
          return [];
        }
      };
      window.scrollTo = () => {};
      window.Element.prototype.scrollTo =
        window.Element.prototype.scrollTo || function () {};
      window.HTMLElement.prototype.scrollIntoView =
        window.HTMLElement.prototype.scrollIntoView || function () {};
      window.SVGPathElement = window.SVGPathElement || class {};
      window.console.error = (...a) => {
        consoleErrors.push(a.map((x) => (x && x.stack) || String(x)).join(' '));
      };
      window.addEventListener('pageerror', (e) =>
        pageErrors.push(e.message + '\n' + ((e.error && e.error.stack) || ''))
      );
    },
  });

  const { window } = dom;
  await sleep(4500);
  const doc = window.document;

  const results = [];
  const check = (name, cond, detail = '') => {
    results.push({ name, cond, detail });
    console.log(`${cond ? 'PASS' : 'FAIL'} | ${name}${cond ? '' : ' | ' + detail}`);
  };

  const visibleText = () => {
    const clone = doc.body.cloneNode(true);
    clone.querySelectorAll('script, style').forEach((n) => n.remove());
    return clone.textContent || '';
  };

  const clickByText = async (selector, label, waitMs = 1500) => {
    const nodes = [...doc.querySelectorAll(selector)];
    const btn = nodes.find((b) =>
      (b.textContent || '').trim().toLowerCase().includes(label.toLowerCase())
    );
    if (!btn) {
      check(`click "${label}"`, false, 'element not found');
      return false;
    }
    btn.click();
    await sleep(waitMs);
    return true;
  };

  // ---------------------------------------------------------------- boot
  const t0 = visibleText();
  check('App boots (no "Initializing" stuck)', !t0.includes('Initializing Climate Intelligence Workspace'), t0.slice(0, 160));

  // ------------------------------------------------ floating chat button
  const fab = doc.querySelector('[data-testid="ai-chat-fab"]');
  check('Floating AI chat button exists on the landing page', !!fab);
  const fabStyle = fab ? window.getComputedStyle(fab) : null;
  if (fab) {
    fab.click();
    await sleep(1500);
  }
  const chatText = visibleText();
  check('Chat panel opens with the required title', chatText.includes('ClimaCred AI Assistant'));
  check('Chat panel shows the required subtitle', chatText.includes('Ask me about your climate data'));
  check(
    'Chat panel offers suggested questions',
    chatText.includes('biggest climate risk') || chatText.includes('climate score')
  );

  // Send a message through the real backend
  const input = doc.querySelector('[data-testid="ai-chat-input"]');
  if (input) {
    input.value = WITH_DATA ? 'What should I do next?' : 'What data do you need from me?';
    input.dispatchEvent(new window.Event('input', { bubbles: true }));
    const send = doc.querySelector('[data-testid="ai-chat-send"]');
    if (send) send.click();
    await sleep(4000);
  }
  const afterAsk = visibleText();
  if (WITH_DATA) {
    check(
      'Chat answers using stored/calculated data',
      /kWh|litres|score|VFD|motors|Water/i.test(afterAsk),
      'no data-based answer text found'
    );
  } else {
    check(
      'Chat shows the exact no-data message',
      afterAsk.includes("I don't have your business climate data yet.") &&
        afterAsk.includes("Complete your Climate Assessment and I'll analyze it for you."),
      'no-data copy missing'
    );
  }

  // Close the panel so the rest of the tour is unobstructed
  if (fab) {
    fab.click();
    await sleep(500);
  }

  // ---------------------------------------------------------------- dashboard
  await clickByText('button, a', 'Dashboard', 3000);
  const dash = visibleText();
  check('Dashboard renders', dash.includes('Climate Readiness') || dash.includes('Dashboard') || dash.length > 800);
  if (WITH_DATA) {
    check('Dashboard shows the stored business name', dash.includes(TEST_PROFILE.name));
    check('Dashboard shows the stored electricity figure', dash.includes('21,500') || dash.includes('21500'));
    check(
      'Dashboard shows calculated AI intelligence or its clean notice',
      /AI Climate Intelligence/.test(dash)
    );
  } else {
    check('Empty dashboard shows a clean empty state', /No business climate data yet|I don.t have your business climate data yet/.test(dash), dash.slice(0, 200));
    check(
      'Empty dashboard shows no fabricated energy figure',
      !dash.includes('38,500') && !dash.includes('3,46,500')
    );
  }

  // ------------------------------------------------------------- every page
  const pages = [
    ['Business Profile', 'Business'],
    ['Climate Assessment', 'Assessment'],
    ['Climate Fingerprint', 'Fingerprint'],
    ['Energy', 'Energy'],
    ['Water', 'Water'],
    ['Waste', 'Waste'],
    ['Emissions', 'Emissions'],
    ['Mobility', 'Mobility'],
    ['Green Solutions', 'Solution'],
    ['Scenario Simulator', 'Scenario'],
    ['Transformation Plan', 'Transformation'],
    ['Impact Verification', 'Impact Verification'],
    ['Impact Report', 'Report'],
    ['Settings', 'Settings'],
  ];
  let rendered = 0;
  for (const [label, marker] of pages) {
    const ok = await clickByText('button, a', label, 1200);
    const body = visibleText();
    const pageOk = ok && body.length > 400 && body.toLowerCase().includes(marker.toLowerCase().split(' ')[0]);
    if (pageOk) rendered++;
    check(`${label} page renders`, pageOk, `text length ${body.length}`);
  }
  check(`All ${pages.length} pages render`, rendered === pages.length, `${rendered}/${pages.length}`);

  // ---------------------------------------------------- fabricated data sweep
  const finalText = visibleText();
  const leaked = FORBIDDEN.filter((needle) => finalText.includes(needle));
  check('No fabricated demo data anywhere in the UI', leaked.length === 0, leaked.join(', '));

  // ------------------------------------------------------------- diagnostics
  console.log('\n--- API calls made by the app ---');
  console.log([...new Set(apiCalls)].join('\n') || '(none)');
  console.log('\n--- failed fetches ---');
  console.log(failedFetches.length ? failedFetches.join('\n') : '(none)');
  console.log('\n--- console errors ---');
  console.log(consoleErrors.length ? consoleErrors.slice(0, 5).join('\n') : '(none)');
  console.log('\n--- page errors ---');
  console.log(pageErrors.length ? pageErrors.slice(0, 5).join('\n') : '(none)');

  check('No page errors', pageErrors.length === 0, pageErrors.slice(0, 2).join(' | '));
  check('No unexpected failed API calls', failedFetches.length === 0, failedFetches.slice(0, 3).join(' | '));

  const failures = results.filter((r) => !r.cond);
  console.log(`\n==================== ${results.length - failures.length}/${results.length} checks passed ====================`);
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((err) => {
  console.error('SMOKE HARNESS ERROR:', err);
  process.exit(3);
});
