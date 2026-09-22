// Renders stills / film from the live scene via headless Chromium (?capture mode).
// usage: node tools/render.mjs stills|film|probe <outdir>
import { createRequire } from 'module';
import { spawn, execFileSync } from 'child_process';
const require = createRequire(import.meta.url);
let pw; try { pw = require('playwright'); } catch { pw = require('/opt/node22/lib/node_modules/playwright'); }
const [mode = 'probe', out = 'assets', W = '1600', H = '1000'] = process.argv.slice(2);
const URL = process.env.URL || 'http://localhost:8123/index.html?capture';
const browser = await pw.chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: +W, height: +H }, ignoreHTTPSErrors: true });
const page = await ctx.newPage();
// Headless Chromium can't reach CDNs through the sandbox proxy reliably; fetch them with curl instead.
const cache = new Map();
await page.route(/^https:\/\//, async (route) => {
  const u = route.request().url();
  try {
    if (!cache.has(u)) {
      const body = execFileSync('curl', ['-sSL', '--retry', '3', '-A', 'Mozilla/5.0 Chrome/140', u], { maxBuffer: 64 << 20 });
      cache.set(u, body);
    }
    const ct = u.includes('fonts.googleapis') ? 'text/css' : u.endsWith('.js') ? 'application/javascript' : u.includes('woff2') ? 'font/woff2' : 'application/octet-stream';
    await route.fulfill({ status: 200, body: cache.get(u), headers: { 'content-type': ct, 'access-control-allow-origin': '*' } });
  } catch (e) { console.log('[route fail]', u); await route.abort(); }
});
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.goto(URL);
await page.waitForFunction(() => window.__ready === true, null, { timeout: 120000 });
await page.evaluate(() => document.fonts.ready);
const shot = async (p, t, file, once = false) => {
  if (!once) await page.evaluate(([p, t]) => window.__renderAt(p, t), [p, t]);
  await page.evaluate(([p, t]) => window.__renderAt(p, t), [p, t]);
  return page.screenshot({ path: file, type: 'jpeg', quality: 90 });
};
if (mode === 'probe') {
  for (const p of (process.env.PS || '0,0.5,1,2,2.6,3,4,5').split(',')) await shot(+p, 3, `${out}/probe-${p}.jpg`);
} else if (mode === 'stills') {
  await shot(0.0, 2.0, `${out}/hero.jpg`);
  await shot(3.0, 6.0, `${out}/gallery-01.jpg`);
  await shot(0.45, 4.0, `${out}/gallery-02.jpg`);
  await shot(2.0, 5.0, `${out}/gallery-03.jpg`);
  await shot(2.75, 7.0, `${out}/gallery-04.jpg`);
  await shot(5.0, 1.0, `${out}/flatlay.jpg`);
} else if (mode === 'film') {
  const fps = +(process.env.FPS || 20), secs = +(process.env.SECS || 12);
  const ff = spawn('/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux', ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', 'pipe:0',
    '-c:v', 'vp8', '-b:v', '3500k', '-deadline', 'good', '-pix_fmt', 'yuv420p', '-f', 'webm', `${out}/film.webm`], { stdio: ['pipe', 'ignore', 'ignore'] });
  ff.on('exit', (c) => { if (c) { console.log('ffmpeg exited', c); process.exit(1); } });
  const N = fps * secs;
  // hold–move pacing through chapters 0 → 4
  const path = (u) => { const seg = u * 4; const i = Math.floor(seg); const f = seg - i; return Math.min(4, i + Math.min(1, Math.max(0, (f - 0.25) / 0.75))); };
  for (let k = 0; k < N; k++) {
    const u = k / (N - 1);
    const buf = await shot(path(u), 2 + k / fps, undefined, k > 0);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (k % 20 === 0) console.log('frame', k, '/', N);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
}
await browser.close();
