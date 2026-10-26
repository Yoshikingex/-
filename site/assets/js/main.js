/* CTF GROUP sample LP — scroll-scrubbed film + GSAP/ScrollTrigger + Lenis */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const html = document.documentElement;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const DURATION = 15;
  // [in, out] seconds of each chapter on the film timeline
  const CH_TIMES = [[0, 2.3], [2.5, 5.0], [5.2, 9.0], [9.2, 12.1], [12.3, 15.01]];

  html.classList.add('js');
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Smooth scroll ---------- */
  let lenis = null;
  if (!reduced) {
    lenis = new Lenis({ lerp: 0.09, smoothWheel: true });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(t => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  }

  /* ---------- Header / menu ---------- */
  const header = $('#header'), nav = $('#nav'), burger = $('#burger');
  let menuOpen = false;
  const setMenu = open => {
    menuOpen = open;
    nav.classList.toggle('is-open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
    if (lenis) open ? lenis.stop() : lenis.start();
  };
  burger.addEventListener('click', () => setMenu(!menuOpen));
  addEventListener('keydown', e => { if (e.key === 'Escape' && menuOpen) setMenu(false); });

  ScrollTrigger.create({
    start: 0, end: 'max',
    onUpdate: self => {
      const y = self.scroll();
      header.classList.toggle('is-hidden', !menuOpen && self.direction === 1 && y > 160);
      header.classList.toggle('is-solid', y > $('.film').offsetHeight - innerHeight);
    },
  });

  $$('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
    const id = a.getAttribute('href');
    const target = id === '#top' ? 0 : $(id);
    if (target === null) return;
    e.preventDefault();
    if (menuOpen) setMenu(false);
    if (lenis) lenis.scrollTo(target, { offset: id === '#top' ? 0 : -72, duration: 1.6 });
    else if (target === 0) scrollTo(0, 0); else target.scrollIntoView();
  }));

  /* ---------- Loader ---------- */
  const loader = $('#loader'), loaderBar = $('#loaderBar'), loaderNum = $('#loaderNum');
  const CIRC = 2 * Math.PI * 52;
  const setLoad = p => {
    loaderBar.style.strokeDashoffset = String(CIRC * (1 - p));
    loaderNum.textContent = String(Math.round(p * 100));
  };
  let loaderDone = false;
  const finishLoader = () => {
    if (loaderDone) return;
    loaderDone = true;
    setLoad(1);
    setTimeout(() => { loader.classList.add('is-done'); intro(); }, 250);
  };

  /* ---------- Film ---------- */
  const film = $('.film'), video = $('#filmVideo'), poster = $('#filmPoster');
  const chapters = $$('.chapter');
  const railFill = $('#railFill'), railDots = $$('.rail__dots li'), timecode = $('#timecode'), hint = $('#scrollHint');
  const miniNums = $$('.chapter[data-ch="3"] .num');
  let videoReady = false, cur = 0, target = 0;

  function intro() {
    if (reduced) return;
    const ch0 = chapters[0];
    gsap.timeline({ defaults: { ease: 'expo.out' } })
      .fromTo($$('.line>span', ch0), { yPercent: 110 }, { yPercent: 0, duration: 1.4, stagger: 0.09 })
      .fromTo([$('.eyebrow', ch0), $('.actions', ch0)], { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 1.2, stagger: 0.12 }, 0.35)
      .fromTo(header, { yPercent: -100 }, { yPercent: 0, duration: 1.2, clearProps: 'transform' }, 0.2);
  }

  if (reduced) {
    html.classList.add('is-static');
    finishLoader();
  } else {
    gsap.set(chapters[0], { visibility: 'visible' });
    gsap.set($$('.line>span', chapters[0]), { yPercent: 110 });
    gsap.set([$('.eyebrow', chapters[0]), $('.actions', chapters[0])], { opacity: 0 });
    setLoad(0);
    loadFilm();
    buildFilmTimeline();
  }

  async function loadFilm() {
    const portrait = matchMedia('(max-aspect-ratio: 1/1)').matches;
    const src = portrait ? 'assets/media/hero-mobile.mp4' : 'assets/media/hero-desktop.mp4';
    const giveUp = setTimeout(finishLoader, 10000); // never trap the visitor behind the loader
    try {
      // A Blob URL keeps the whole clip in memory, so seeking while scrolling is instant.
      const res = await fetch(src);
      if (!res.ok) throw new Error(res.status);
      const total = +res.headers.get('content-length') || 0;
      const reader = res.body.getReader();
      const chunks = []; let got = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value); got += value.length;
        if (total) setLoad(Math.min(0.99, got / total));
      }
      video.src = URL.createObjectURL(new Blob(chunks, { type: 'video/mp4' }));
    } catch (_) {
      video.src = src; // progressive fallback
    }
    video.load();
    await new Promise(r => video.readyState >= 1 ? r() : video.addEventListener('loadedmetadata', r, { once: true }));
    // iOS paints seeked frames only after the element has played once
    try { await video.play(); video.pause(); } catch (_) { /* autoplay blocked: seeking still works */ }
    video.currentTime = cur;
    video.addEventListener('seeked', () => poster.classList.add('is-hidden'), { once: true });
    videoReady = true;
    clearTimeout(giveUp);
    finishLoader();
  }

  function buildFilmTimeline() {
    const tl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out' } });
    chapters.forEach((ch, i) => {
      const [a, b] = CH_TIMES[i];
      const lines = $$('.line>span', ch);
      const parts = $$('.eyebrow, .actions, .zero-list li, .mini-stats > div', ch);
      if (i > 0) {
        tl.set(ch, { visibility: 'visible' }, a)
          .fromTo(lines, { yPercent: 110 }, { yPercent: 0, duration: 0.8, stagger: 0.08 }, a)
          .fromTo(parts, { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.7, stagger: 0.08 }, a + 0.2);
      }
      if (i < chapters.length - 1) {
        tl.to(lines, { yPercent: -110, duration: 0.55, stagger: 0.04, ease: 'power2.in', immediateRender: false }, b - 0.6)
          .to(parts, { opacity: 0, y: -20, duration: 0.45, ease: 'power2.in', immediateRender: false }, b - 0.6)
          .set(ch, { visibility: 'hidden' }, b);
      }
    });
    tl.set({}, {}, DURATION);

    ScrollTrigger.create({
      trigger: film, start: 'top top', end: 'bottom bottom',
      onUpdate: self => { target = self.progress * DURATION; },
    });

    gsap.ticker.add(() => {
      const d = target - cur;
      cur = Math.abs(d) < 0.001 ? target : cur + d * 0.2;
      tl.time(Math.min(cur, DURATION - 0.001));
      // coalesce seeks: never queue a new one while the decoder is busy
      if (videoReady && !video.seeking && Math.abs(video.currentTime - cur) > 0.012) video.currentTime = cur;
      railFill.style.transform = `scaleX(${cur / DURATION})`;
      railDots.forEach((dot, i) => dot.classList.toggle('is-on', cur >= CH_TIMES[i][0]));
      timecode.textContent = `00:${String(Math.floor(cur)).padStart(2, '0')}`;
      hint.style.opacity = String(1 - Math.min(1, cur / 0.6));
      const k = Math.min(1, Math.max(0, (cur - 9.4) / 1.6));
      miniNums.forEach(n => { n.textContent = formatNum(+n.dataset.to * (1 - Math.pow(1 - k, 3)), n); });
    });
  }

  function formatNum(v, el) {
    const dec = +(el.dataset.dec || 0);
    const s = v.toFixed(dec);
    return el.dataset.sep ? Number(s).toLocaleString('ja-JP') : s;
  }

  if (reduced) {
    $$('.num').forEach(n => { n.textContent = formatNum(+n.dataset.to, n); });
    return;
  }

  /* ---------- Ticker (reacts to scroll velocity) ---------- */
  const ticker = gsap.to('#ticker', { xPercent: -50, duration: 28, ease: 'none', repeat: -1 });
  ScrollTrigger.create({
    start: 0, end: 'max',
    onUpdate: self => {
      const v = self.getVelocity() / 250;
      gsap.timeline()
        .to(ticker, { timeScale: (self.direction || 1) * Math.min(6, 1 + Math.abs(v)), duration: 0.2, overwrite: true })
        .to(ticker, { timeScale: self.direction || 1, duration: 1.2, ease: 'power2.out' });
    },
  });

  /* ---------- Services: horizontal scroll (desktop) ---------- */
  const mm = gsap.matchMedia();
  mm.add('(min-width: 900px)', () => {
    const track = $('#servicesTrack');
    const dist = () => Math.max(0, track.scrollWidth - innerWidth);
    gsap.to(track, {
      x: () => -dist(), ease: 'none',
      scrollTrigger: { trigger: '.services__pin', start: 'top top', end: () => '+=' + dist() * 1.8, pin: true, scrub: 0.8, invalidateOnRefresh: true },
    });
  });

  /* ---------- Reveal ---------- */
  ScrollTrigger.batch('.reveal', {
    start: 'top 88%', once: true,
    onEnter: els => gsap.to(els, { opacity: 1, y: 0, duration: 1.1, stagger: 0.1, ease: 'power3.out' }),
  });
  ScrollTrigger.batch('.svc', {
    start: 'top 92%', once: true,
    onEnter: els => gsap.fromTo(els, { opacity: 0, y: 60, rotate: 2 }, { opacity: 1, y: 0, rotate: 0, duration: 1.1, stagger: 0.12, ease: 'power3.out' }),
  });

  /* ---------- Count-up stats ---------- */
  ScrollTrigger.create({
    trigger: '.stats', start: 'top 80%', once: true,
    onEnter: () => $$('.stats .num').forEach((n, i) => {
      const o = { v: 0 };
      gsap.to(o, { v: +n.dataset.to, duration: 2, delay: i * 0.12, ease: 'power3.out', onUpdate: () => { n.textContent = formatNum(o.v, n); } });
    }),
  });

  /* ---------- Flow line ---------- */
  gsap.to('.steps__line line', {
    strokeDashoffset: 0, ease: 'none',
    scrollTrigger: { trigger: '#steps', start: 'top 70%', end: 'bottom 70%', scrub: true },
  });
  $$('.step').forEach(s => ScrollTrigger.create({ trigger: s, start: 'top 72%', toggleClass: 'is-on' }));

  /* ---------- Pointer niceties ---------- */
  if (finePointer) {
    $$('.magnetic').forEach(btn => {
      const x = gsap.quickTo(btn, 'x', { duration: 0.5, ease: 'power3.out' });
      const y = gsap.quickTo(btn, 'y', { duration: 0.5, ease: 'power3.out' });
      btn.addEventListener('pointermove', e => {
        const r = btn.getBoundingClientRect();
        x((e.clientX - r.left - r.width / 2) * 0.25); y((e.clientY - r.top - r.height / 2) * 0.35);
      });
      btn.addEventListener('pointerleave', () => { x(0); y(0); });
    });
    $$('.case').forEach(card => {
      const rx = gsap.quickTo(card, 'rotationX', { duration: 0.6, ease: 'power3.out' });
      const ry = gsap.quickTo(card, 'rotationY', { duration: 0.6, ease: 'power3.out' });
      gsap.set(card, { transformPerspective: 900 });
      card.addEventListener('pointermove', e => {
        const r = card.getBoundingClientRect();
        ry(((e.clientX - r.left) / r.width - 0.5) * 10); rx(-((e.clientY - r.top) / r.height - 0.5) * 10);
      });
      card.addEventListener('pointerleave', () => { rx(0); ry(0); });
    });
  }

  /* ---------- Contact form (sample: validates, never sends) ---------- */
  const form = $('#contactForm'), err = $('#formError'), thanks = $('#thanks');
  form.addEventListener('submit', e => {
    e.preventDefault();
    const bad = [];
    $$('input[required], textarea[required]', form).forEach(el => {
      const ok = el.type === 'checkbox' ? el.checked : el.type === 'email' ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value.trim()) : el.value.trim() !== '';
      el.classList.toggle('is-invalid', !ok);
      el.setAttribute('aria-invalid', String(!ok));
      if (!ok) bad.push(el);
    });
    if (bad.length) {
      err.textContent = '未入力または形式が正しくない項目があります。';
      bad[0].focus();
      return;
    }
    err.textContent = '';
    gsap.to(form, {
      opacity: 0, y: -20, duration: 0.5, onComplete: () => {
        form.hidden = true; thanks.hidden = false;
        gsap.fromTo(thanks, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.8 });
        thanks.focus({ preventScroll: true });
        ScrollTrigger.refresh();
      },
    });
  });

  addEventListener('load', () => ScrollTrigger.refresh());
})();
