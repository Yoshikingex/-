// Renders scene.html frame-by-frame in headless Chromium and pipes JPEGs into ffmpeg.
// usage: node render.js <out.mp4> [fps=30] [w=1920] [h=1080] [--stills t1,t2,...]
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = __dirname;
const args = process.argv.slice(2);
const out = args[0];
const fps = +(args[1] || 30), W = +(args[2] || 1920), H = +(args[3] || 1080);
const stillsIdx = args.indexOf('--stills');
const stills = stillsIdx >= 0 ? args[stillsIdx + 1].split(',').map(Number) : null;
const DURATION = 15;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript' };

const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${port}/scene.html?w=${W}&h=${H}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });

  const decode = d => Buffer.from(d.split(',')[1], 'base64');
  if (stills) {
    for (const t of stills) {
      fs.writeFileSync(`${out}-${String(t).replace('.', '_')}.jpg`, decode(await page.evaluate(t => window.grab(t, 0.9), t)));
    }
  } else {
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const total = fps * DURATION, t0 = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = decode(await page.evaluate(t => window.grab(t, 0.96), i / fps));
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 30 === 0) console.log(`frame ${i}/${total} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
  server.close();
})();
