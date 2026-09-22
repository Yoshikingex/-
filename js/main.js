/* =========================================================
   GSAP ScrollTrigger + Lenis — page choreography
   ========================================================= */
(function () {
  'use strict';
  if (!window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));
  const scene = () => window.PRINTEMPS_SCENE;

  /* ---------- smooth scroll (Lenis) ---------- */
  let lenis = null;
  if (window.Lenis && !reduced) {
    lenis = new Lenis({ lerp: 0.085, smoothWheel: true, wheelMultiplier: 1 });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    lenis.stop();
  } else {
    document.body.classList.add('is-locked');
  }
  function unlockScroll() {
    if (lenis) lenis.start();
    document.body.classList.remove('is-locked');
  }

  /* ---------- text splitting ---------- */
  function splitChars(el) {
    const text = el.textContent;
    el.textContent = '';
    const frag = document.createDocumentFragment();
    for (const ch of text.trim()) {
      const s = document.createElement('span');
      s.className = 'c';
      s.textContent = ch === ' ' ? ' ' : ch;
      frag.appendChild(s);
    }
    el.appendChild(frag);
    return $$('.c', el);
  }
  function splitWords(el) {
    // Japanese has no spaces: split into characters, keep runs of latin/digits together
    const text = el.textContent.replace(/\s+/g, ' ').trim();
    el.textContent = '';
    const tokens = text.match(/[A-Za-z0-9¥¥.,'’&\-]+|\S|\s/g) || [];
    const frag = document.createDocumentFragment();
    tokens.forEach((tk) => {
      if (tk === ' ') { frag.appendChild(document.createTextNode(' ')); return; }
      const s = document.createElement('span');
      s.className = 'w';
      s.textContent = tk;
      frag.appendChild(s);
    });
    el.appendChild(frag);
    return $$('.w', el);
  }
  $$('[data-split="chars"]').forEach(splitChars);
  $$('[data-words]').forEach(splitWords);

  /* ---------- navigation ---------- */
  function scrollToHash(hash) {
    const target = $(hash);
    if (!target) return;
    if (lenis) lenis.scrollTo(target, { duration: 1.6, easing: (t) => 1 - Math.pow(1 - t, 4) });
    else target.scrollIntoView({ behavior: 'smooth' });
  }
  $$('[data-nav]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const href = a.getAttribute('href');
      if (!href || !href.startsWith('#')) return;
      e.preventDefault();
      document.body.classList.remove('nav-open');
      scrollToHash(href);
    });
  });
  const burger = $('#burger');
  if (burger) burger.addEventListener('click', () => document.body.classList.toggle('nav-open'));

  /* ---------- loader + hero intro ---------- */
  const heroTitleChars = $$('.hero__title .c');
  const heroEyebrowChars = $$('.hero__eyebrow .c');
  const heroJpChars = $$('.hero__jp .c');

  gsap.set('#heroFrame', { scale: 0.7, opacity: 0, filter: 'blur(14px)' });
  gsap.set(heroTitleChars, { yPercent: 110, opacity: 0, rotateX: -60 });
  gsap.set(heroEyebrowChars, { opacity: 0, y: 8 });
  gsap.set(heroJpChars, { opacity: 0, y: 12 });

  const intro = gsap.timeline({ paused: true, defaults: { ease: 'expo.out' } });
  intro
    .to('.loader__ornament', { opacity: 1, duration: 0.8 }, 0)
    .to('.loader__title span', { opacity: 1, duration: 0.8 }, 0.15)
    .to('.loader__title strong', { opacity: 1, duration: 1, y: 0 }, 0.3)
    .to('#loaderBar', { scaleX: 1, duration: 1.5, ease: 'power2.inOut' }, 0.2)
    .to('.loader__inner', { opacity: 0, y: -20, duration: 0.6, ease: 'power2.in' }, 1.75)
    .to('#loader', { yPercent: -100, duration: 1.2, ease: 'expo.inOut' }, 2.05)
    .to('#heroFrame', { scale: 1, opacity: 1, filter: 'blur(0px)', duration: 1.8 }, 2.35)
    .to(heroTitleChars, { yPercent: 0, opacity: 1, rotateX: 0, duration: 1.4, stagger: 0.05 }, 2.55)
    .to(heroEyebrowChars, { opacity: 1, y: 0, duration: 0.8, stagger: 0.015 }, 2.9)
    .to(heroJpChars, { opacity: 1, y: 0, duration: 0.8, stagger: 0.03 }, 3.1)
    .to('.hero__tagline', { opacity: 1, duration: 1 }, 3.4)
    .to('.hero__meta-item', { opacity: 1, y: 0, duration: 1, stagger: 0.1 }, 3.3)
    .to('#heroScroll', { opacity: 1, duration: 1 }, 3.6)
    .to('#header', { y: 0, duration: 1.2 }, 2.9)
    .add(() => { unlockScroll(); ScrollTrigger.refresh(); }, 2.8);

  let loaded = false;
  const startIntro = () => { if (loaded) return; loaded = true; intro.play(); };
  window.addEventListener('load', startIntro);
  setTimeout(startIntro, 3500); // never wait on a slow network forever

  const heroVideo = $('#heroVideo');
  if (heroVideo) heroVideo.play().catch(() => {});

  /* ---------- global progress + 3D scroll ---------- */
  ScrollTrigger.create({
    trigger: '#main', start: 'top top', end: 'bottom bottom', scrub: 0.3,
    onUpdate: (self) => {
      gsap.set('#progressBar', { scaleX: self.progress });
      if (scene()) scene().setScroll(self.progress);
    },
  });

  /* ---------- HERO scroll (video frame expands to full screen) ---------- */
  const heroTl = gsap.timeline({
    scrollTrigger: { trigger: '.hero', start: 'top top', end: '+=150%', pin: '.hero__pin', scrub: 0.8, anticipatePin: 1 },
  });
  heroTl
    .to('#heroFrame', { width: '100vw', height: '100vh', maxHeight: '100vh', borderRadius: 0, ease: 'power2.inOut', duration: 1 }, 0)
    .to('.hero__video', { scale: 1, ease: 'none', duration: 1 }, 0)
    .to(heroTitleChars, { yPercent: -60, opacity: 0, stagger: 0.02, ease: 'power2.in', duration: 0.5 }, 0.05)
    .to(['.hero__eyebrow', '.hero__jp', '.hero__tagline'], { opacity: 0, y: -30, ease: 'power2.in', duration: 0.4 }, 0)
    .to(['.hero__meta', '#heroScroll'], { opacity: 0, y: 20, ease: 'power2.in', duration: 0.3 }, 0)
    .to('.hero__frame-shade', { opacity: 1, ease: 'none', duration: 0.6 }, 0.4)
    .fromTo('.hero__frame-shade', { background: 'linear-gradient(180deg, rgba(18,11,8,0.05) 40%, rgba(18,11,8,0.55) 100%)' },
      { background: 'linear-gradient(180deg, rgba(18,11,8,0.35) 0%, rgba(18,11,8,0.95) 100%)', ease: 'none', duration: 0.6 }, 0.4);

  /* ---------- generic reveals ---------- */
  $$('.line-mask > span').forEach((line) => {
    gsap.to(line, {
      y: 0, duration: 1.4, ease: 'expo.out',
      scrollTrigger: { trigger: line.parentElement, start: 'top 88%', once: true },
    });
  });
  $$('[data-reveal]').forEach((el) => {
    gsap.to(el, {
      opacity: 1, y: 0, duration: 1.2, ease: 'expo.out',
      scrollTrigger: { trigger: el, start: 'top 90%', once: true },
    });
  });
  $$('[data-words]').forEach((p) => {
    const words = $$('.w', p);
    gsap.to(words, {
      opacity: 1, y: 0, ease: 'none', stagger: 0.6,
      scrollTrigger: { trigger: p, start: 'top 85%', end: 'bottom 55%', scrub: 0.5 },
    });
  });
  $$('[data-parallax]').forEach((el) => {
    const v = parseFloat(el.dataset.parallax) || 0;
    gsap.fromTo(el, { yPercent: -v }, {
      yPercent: v, ease: 'none',
      scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom top', scrub: true },
    });
  });

  /* ---------- STORY: horizontal scroll ---------- */
  const track = $('#storyTrack');
  if (track) {
    const distance = () => Math.max(0, track.scrollWidth - window.innerWidth);
    const storyTween = gsap.to(track, {
      x: () => -distance(), ease: 'none',
      scrollTrigger: {
        trigger: '.story', start: 'top top', end: () => '+=' + distance() * 1.1,
        pin: '.story__pin', scrub: 1, invalidateOnRefresh: true, anticipatePin: 1,
        onUpdate: (self) => gsap.set('#storyProgress', { scaleX: self.progress }),
      },
    });
    $$('[data-story-img]').forEach((img) => {
      gsap.fromTo(img, { xPercent: -18 }, {
        xPercent: 0, ease: 'none',
        scrollTrigger: { trigger: img.parentElement, containerAnimation: storyTween, start: 'left right', end: 'right left', scrub: true },
      });
    });
    $$('.story__text').forEach((txt) => {
      gsap.from(txt.children, {
        y: 50, opacity: 0, duration: 1, stagger: 0.08, ease: 'expo.out',
        scrollTrigger: { trigger: txt, containerAnimation: storyTween, start: 'left 85%', once: true },
      });
    });
    $$('.story__img').forEach((box) => {
      gsap.from(box, {
        scale: 0.86, opacity: 0.4, duration: 1.2, ease: 'expo.out',
        scrollTrigger: { trigger: box, containerAnimation: storyTween, start: 'left 95%', once: true },
      });
    });
    const endPanel = $('.story__panel--end');
    if (endPanel) {
      gsap.from(endPanel.children, {
        y: 60, opacity: 0, duration: 1.2, stagger: 0.15, ease: 'expo.out',
        scrollTrigger: { trigger: endPanel, containerAnimation: storyTween, start: 'left 80%', once: true },
      });
    }
  }

  /* ---------- PRODUCT: 3D tilt + bean vortex ---------- */
  const card = $('#productCard');
  if (card) {
    gsap.to('#productImg', {
      scale: 1, ease: 'none',
      scrollTrigger: { trigger: '.product', start: 'top bottom', end: 'bottom top', scrub: true },
    });
    gsap.from(card, {
      y: 120, opacity: 0, rotateY: -18, duration: 1.6, ease: 'expo.out',
      scrollTrigger: { trigger: card, start: 'top 85%', once: true },
    });
    gsap.from('.product__float', {
      scale: 0.7, opacity: 0, duration: 1.4, stagger: 0.15, ease: 'expo.out',
      scrollTrigger: { trigger: card, start: 'top 75%', once: true },
    });
    if (!reduced && window.matchMedia('(hover: hover)').matches) {
      const rx = gsap.quickTo(card, 'rotateX', { duration: 0.6, ease: 'power3' });
      const ry = gsap.quickTo(card, 'rotateY', { duration: 0.6, ease: 'power3' });
      const wrap = card.parentElement;
      wrap.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        ry((px - 0.5) * 18);
        rx((0.5 - py) * 14);
        card.style.setProperty('--mx', px * 100 + '%');
        card.style.setProperty('--my', py * 100 + '%');
      });
      wrap.addEventListener('pointerleave', () => { rx(0); ry(0); });
    }
    const smooth = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
    ScrollTrigger.create({
      trigger: '.product', start: 'top 85%', end: 'bottom 15%', scrub: true,
      onUpdate: (self) => {
        const p = self.progress;
        const g = smooth(0, 0.3, p) * (1 - smooth(0.7, 1, p));
        if (scene()) scene().setGather(g);
      },
      onLeave: () => scene() && scene().setGather(0),
      onLeaveBack: () => scene() && scene().setGather(0),
    });
  }

  /* ---------- FILM: video reveal ---------- */
  const filmFrame = $('#filmFrame');
  const filmVideo = $('#filmVideo');
  if (filmFrame) {
    const quoteChars = $$('.film__quote .c');
    gsap.set(quoteChars, { opacity: 0, y: 30 });
    const filmTl = gsap.timeline({
      scrollTrigger: {
        trigger: '.film', start: 'top top', end: '+=140%', pin: '.film__pin', scrub: 0.8, anticipatePin: 1,
        onEnter: () => filmVideo && filmVideo.play().catch(() => {}),
        onEnterBack: () => filmVideo && filmVideo.play().catch(() => {}),
        onLeave: () => filmVideo && filmVideo.pause(),
        onLeaveBack: () => filmVideo && filmVideo.pause(),
      },
    });
    filmTl
      .to(filmFrame, { width: '100vw', height: '100vh', borderRadius: 0, ease: 'power2.inOut', duration: 1 }, 0)
      .to(quoteChars, { opacity: 1, y: 0, stagger: 0.04, ease: 'expo.out', duration: 0.5 }, 0.45)
      .to('.film__sub', { opacity: 1, duration: 0.3 }, 0.8);
    // pre-reveal: frame grows slightly as it approaches
    gsap.from(filmFrame, {
      scale: 0.8, opacity: 0.6, ease: 'none',
      scrollTrigger: { trigger: '.film', start: 'top bottom', end: 'top top', scrub: true },
    });
  }

  /* ---------- MENU ---------- */
  ScrollTrigger.batch('[data-menu]', {
    start: 'top 88%', once: true,
    onEnter: (batch) => gsap.to(batch, { opacity: 1, y: 0, duration: 1.1, stagger: 0.1, ease: 'expo.out' }),
  });

  /* ---------- MARQUEE ---------- */
  const marquee = $('#marquee');
  if (marquee && !reduced) {
    const tween = gsap.to(marquee, { xPercent: -50, ease: 'none', duration: 26, repeat: -1 });
    ScrollTrigger.create({
      onUpdate: (self) => {
        const v = Math.min(4, 1 + Math.abs(self.getVelocity()) / 600);
        gsap.to(tween, { timeScale: v, duration: 0.6, overwrite: true });
      },
    });
  }

  /* ---------- header: hide on scroll down, show on scroll up ---------- */
  ScrollTrigger.create({
    start: 'top -80', end: 99999,
    onUpdate: (self) => {
      if (document.body.classList.contains('nav-open')) return;
      gsap.to('#header', { y: self.direction === 1 ? '-110%' : 0, duration: 0.6, ease: 'expo.out', overwrite: true });
    },
  });

  window.addEventListener('load', () => ScrollTrigger.refresh());
})();
