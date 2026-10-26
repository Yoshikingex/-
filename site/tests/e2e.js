// End-to-end checks for the sample LP. usage: node tests/e2e.js [rootDir] [shotDir]
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const REMOTE = /^https?:\/\//.test(process.argv[2] || '') ? process.argv[2] : null; // test a live URL instead of a local folder
const ROOT = REMOTE ? null : path.resolve(process.argv[2] || path.join(__dirname, '..'));
const SHOTS = process.argv[3] || path.join(__dirname, '..', 'test-results');
fs.mkdirSync(SHOTS, { recursive: true });
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mp4': 'video/mp4', '.jpg': 'image/jpeg' };

// static server with Range support (like a real host)
const server = http.createServer((req, res) => {
  let p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (p.endsWith(path.sep)) p = path.join(p, 'index.html');
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  const size = fs.statSync(p).size, type = TYPES[path.extname(p)] || 'application/octet-stream';
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
  if (m) {
    const s = m[1] ? +m[1] : 0, e = m[2] ? +m[2] : size - 1;
    res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${s}-${e}/${size}`, 'Content-Length': e - s + 1, 'Accept-Ranges': 'bytes' });
    return fs.createReadStream(p, { start: s, end: e }).pipe(res);
  }
  res.writeHead(200, { 'Content-Type': type, 'Content-Length': size, 'Accept-Ranges': 'bytes' });
  fs.createReadStream(p).pipe(res);
});

const results = [];
const check = (name, ok, info = '') => { results.push({ name, ok: !!ok, info }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info ? '  — ' + info : ''}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function openPage(browser, base, ctxOpts) {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  const errors = [], bad = [], requests = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  page.on('request', r => requests.push(r.url()));
  await page.goto(base, { waitUntil: 'load' });
  return { ctx, page, errors, bad, requests };
}

// scroll so that the film timeline sits at `sec` seconds, then wait for smoothing + seek
async function scrubTo(page, sec) {
  await page.evaluate(s => {
    const f = document.querySelector('.film');
    const y = f.offsetTop + (f.offsetHeight - innerHeight) * (s / 15);
    window.scrollTo(0, y);
  }, sec);
  await sleep(1600);
}
const videoTime = page => page.evaluate(() => document.getElementById('filmVideo').currentTime);
const visibleChapter = page => page.evaluate(() => [...document.querySelectorAll('.chapter')].findIndex(c => getComputedStyle(c).visibility === 'visible'));
const noHScroll = page => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);

(async () => {
  if (!REMOTE) await new Promise(r => server.listen(0, r));
  const base = REMOTE || `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch();

  /* ---------- Desktop ---------- */
  {
    const { ctx, page, errors, bad, requests } = await openPage(browser, base, { viewport: { width: 1440, height: 900 } });
    await page.waitForSelector('#loader.is-done', { state: 'attached', timeout: 30000 });
    check('PC: loader finishes', true);
    check('PC: desktop (16:9) film requested', requests.some(u => u.endsWith('hero-desktop.mp4')) && !requests.some(u => u.endsWith('hero-mobile.mp4')));
    await sleep(1800);
    await page.screenshot({ path: path.join(SHOTS, 'pc-hero.png') });
    check('PC: hero chapter visible at top', (await visibleChapter(page)) === 0);
    for (const [sec, ch] of [[7, 2], [10.6, 3], [14.2, 4], [3.6, 1]]) {
      await scrubTo(page, sec);
      const vt = await videoTime(page);
      check(`PC: scroll → video ${sec}s`, Math.abs(vt - sec) < 0.35, `currentTime=${vt.toFixed(2)}`);
      check(`PC: chapter ${ch} shown at ${sec}s`, (await visibleChapter(page)) === ch);
      if (sec === 10.6) await page.screenshot({ path: path.join(SHOTS, 'pc-film-ai.png') });
    }
    check('PC: poster hidden once video paints', await page.evaluate(() => document.getElementById('filmPoster').classList.contains('is-hidden')));

    // sales journey film
    const jScrub = async sec => { await page.evaluate(s => { const j = document.getElementById('journey'); window.scrollTo(0, j.offsetTop + (j.offsetHeight - innerHeight) * (s / 15)); }, sec); await sleep(1800); };
    await jScrub(0.5); await sleep(1500);
    check('PC: journey film (16:9) requested', requests.some(u => u.endsWith('sales-desktop.mp4')) && !requests.some(u => u.endsWith('sales-mobile.mp4')));
    for (const [sec, step] of [[7.5, 2], [12, 4], [3.5, 1]]) {
      await jScrub(sec);
      const r = await page.evaluate(() => ({ t: document.getElementById('journeyVideo').currentTime, a: [...document.querySelectorAll('.jstep')].findIndex(s => s.classList.contains('is-active')) }));
      check(`PC: journey scroll → video ${sec}s, step ${step + 1}`, Math.abs(r.t - sec) < 0.35 && r.a === step, `currentTime=${r.t.toFixed(2)} step=${r.a + 1}`);
      if (sec === 7.5) await page.screenshot({ path: path.join(SHOTS, 'pc-journey.png') });
    }

    // horizontal services
    await page.evaluate(() => window.scrollTo(0, document.getElementById('services').offsetTop - innerHeight)); await sleep(1500);
    const t0 = await page.evaluate(() => getComputedStyle(document.getElementById('servicesTrack')).transform);
    await page.evaluate(() => { const s = document.getElementById('services'); window.scrollTo(0, s.getBoundingClientRect().top + scrollY + innerHeight * 0.5); }); // the section, not the (fixed) pin
    await sleep(1500);
    const t1 = await page.evaluate(() => new DOMMatrix(getComputedStyle(document.getElementById('servicesTrack')).transform).m41);
    check('PC: services track scrolls horizontally', t1 < -50, `before=${t0} x=${t1.toFixed(0)}`);
    const pinFits = await page.evaluate(() => { const r = document.querySelector('.services__pin').getBoundingClientRect(); return r.top >= -1 && r.bottom <= innerHeight + 1; });
    check('PC: pinned services fit the viewport', pinFits);
    await page.screenshot({ path: path.join(SHOTS, 'pc-services.png') });

    // nav anchor
    await page.evaluate(() => window.scrollTo(0, 0)); await sleep(800);
    await page.click('.nav a[href="#company"]'); await sleep(2400);
    const top = await page.evaluate(() => document.getElementById('company').getBoundingClientRect().top);
    check('PC: nav link scrolls to 会社概要', Math.abs(top - 72) < 40, `top=${top.toFixed(0)}`);

    // stats count-up
    await page.evaluate(() => document.querySelector('.facts').scrollIntoView({ block: 'center' })); await sleep(2800);
    const stat = await page.evaluate(() => [...document.querySelectorAll('.facts .num')].map(n => n.textContent).join(','));
    check('PC: facts count up to final values', stat === '2022,3,250,500', stat);
    check('PC: page is noindex', await page.evaluate(() => /noindex/.test(document.querySelector('meta[name=robots]')?.content || '')));
    check('PC: unofficial-sample notice present', await page.evaluate(() => /非公式のデザインサンプル/.test(document.querySelector('.footer__notice').textContent) && /送信されません/.test(document.querySelector('.form__demo').textContent)));

    // form
    await page.evaluate(() => document.getElementById('contact').scrollIntoView()); await sleep(1200);
    await page.click('#contactForm button[type=submit]'); await sleep(300);
    check('PC: empty form shows error', (await page.textContent('#formError')).length > 0);
    await page.fill('#f-company', 'サンプル株式会社'); await page.fill('#f-name', '山田 太郎');
    await page.fill('#f-email', 'taro@example.com'); await page.check('input[name=agree]');
    await page.click('#contactForm button[type=submit]'); await sleep(1500);
    check('PC: valid form shows thanks', await page.isVisible('#thanks'));
    await page.screenshot({ path: path.join(SHOTS, 'pc-contact.png') });

    check('PC: no horizontal scroll', await noHScroll(page));
    check('PC: console errors = 0', errors.length === 0, errors.join(' | '));
    check('PC: 4xx/5xx = 0', bad.length === 0, bad.join(' | '));
    await ctx.close();
  }

  /* ---------- Mobile ---------- */
  {
    const { ctx, page, errors, bad, requests } = await openPage(browser, base, { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    await page.waitForSelector('#loader.is-done', { state: 'attached', timeout: 30000 });
    check('SP: portrait (9:16) film requested', requests.some(u => u.endsWith('hero-mobile.mp4')) && !requests.some(u => u.endsWith('hero-desktop.mp4')));
    await sleep(1800);
    await page.screenshot({ path: path.join(SHOTS, 'sp-hero.png') });
    await scrubTo(page, 7);
    const vt = await videoTime(page);
    check('SP: scroll → video 7s', Math.abs(vt - 7) < 0.35, `currentTime=${vt.toFixed(2)}`);
    check('SP: services chapter shown', (await visibleChapter(page)) === 2);
    const fits = await page.evaluate(() => { const c = document.querySelector('.chapter[data-ch="2"]'); return [...c.children].every(el => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }); });
    check('SP: services chapter fits on screen', fits);
    await page.screenshot({ path: path.join(SHOTS, 'sp-film-services.png') });
    await page.evaluate(() => window.scrollBy(0, -120)); await sleep(900); // scrolling up reveals the header
    await page.tap('#burger'); await sleep(600);
    check('SP: burger opens menu', await page.evaluate(() => document.getElementById('nav').classList.contains('is-open')));
    await page.tap('.nav a[href="#news"]'); await sleep(2400);
    check('SP: menu link closes menu & scrolls', await page.evaluate(() => !document.getElementById('nav').classList.contains('is-open') && Math.abs(document.getElementById('news').getBoundingClientRect().top - 72) < 60));
    await page.evaluate(() => document.getElementById('services').scrollIntoView()); await sleep(1500);
    await page.screenshot({ path: path.join(SHOTS, 'sp-services.png') });
    await page.evaluate(() => { const j = document.getElementById('journey'); window.scrollTo(0, j.offsetTop + (j.offsetHeight - innerHeight) * 0.68); }); await sleep(3500);
    const jr = await page.evaluate(() => ({ t: document.getElementById('journeyVideo').currentTime, a: [...document.querySelectorAll('.jstep')].findIndex(s => s.classList.contains('is-active')), vis: [...document.querySelectorAll('.jstep')].filter(s => getComputedStyle(s).display !== 'none').length }));
    check('SP: journey portrait film requested', requests.some(u => u.endsWith('sales-mobile.mp4')) && !requests.some(u => u.endsWith('sales-desktop.mp4')));
    check('SP: journey shows only the active step (step 4)', jr.a === 3 && jr.vis === 1 && Math.abs(jr.t - 10.2) < 0.4, `t=${jr.t.toFixed(2)} step=${jr.a + 1} visible=${jr.vis}`);
    await page.screenshot({ path: path.join(SHOTS, 'sp-journey.png') });
    check('SP: no horizontal scroll', await noHScroll(page));
    check('SP: console errors = 0', errors.length === 0, errors.join(' | '));
    check('SP: 4xx/5xx = 0', bad.length === 0, bad.join(' | '));
    await ctx.close();
  }

  /* ---------- Reduced motion ---------- */
  {
    const { ctx, page, errors, requests } = await openPage(browser, base, { viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    await sleep(1000);
    check('RM: static layout, no film download', await page.evaluate(() => document.documentElement.classList.contains('is-static')) && !requests.some(u => u.endsWith('.mp4')));
    check('RM: every chapter readable', await page.evaluate(() => [...document.querySelectorAll('.chapter')].every(c => getComputedStyle(c).visibility === 'visible')));
    check('RM: console errors = 0', errors.length === 0, errors.join(' | '));
    await ctx.close();
  }

  await browser.close();
  if (!REMOTE) server.close();
  const failed = results.filter(r => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})();
