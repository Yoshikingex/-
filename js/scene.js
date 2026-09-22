/* =========================================================
   Three.js background scene — floating coffee beans + gold dust
   Exposed API: window.PRINTEMPS_SCENE = { setScroll, setGather }
   ========================================================= */
(function () {
  'use strict';

  function boot() {
    const THREE = window.THREE;
    const canvas = document.getElementById('gl');
    if (!THREE || !canvas) return;

    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- renderer / scene / camera ---------- */
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1.25 : 1.6));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x120b08, 9, 24);

    const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 14);

    /* ---------- lights ---------- */
    scene.add(new THREE.AmbientLight(0x6b4a2e, 0.9));
    const key = new THREE.DirectionalLight(0xffe3b8, 2.4);
    key.position.set(5, 8, 7);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xc9a45c, 1.4);
    rim.position.set(-6, 3, -6);
    scene.add(rim);
    const warm = new THREE.PointLight(0xe6c98a, 40, 30, 2);
    warm.position.set(-5, -3, 5);
    scene.add(warm);

    /* ---------- coffee bean geometry ---------- */
    function makeBeanGeometry() {
      const geo = new THREE.SphereGeometry(1, 48, 32);
      const pos = geo.attributes.position;
      const v = new THREE.Vector3();
      for (let i = 0; i < pos.count; i++) {
        v.fromBufferAttribute(pos, i);
        // groove along the long (x) axis on the front face (z > 0)
        if (v.z > 0) {
          const g = Math.exp(-(v.y * v.y) / (2 * 0.13 * 0.13));
          const edge = Math.sqrt(Math.max(0, 1 - v.x * v.x));
          v.z -= 0.42 * g * edge;
          v.z *= 0.92;
        }
        pos.setXYZ(i, v.x * 0.58, v.y * 0.38, v.z * 0.30);
      }
      geo.computeVertexNormals();
      return geo;
    }

    const beanGeo = makeBeanGeometry();
    const beanMat = new THREE.MeshStandardMaterial({
      color: 0x6a3d1e,
      roughness: 0.48,
      metalness: 0.06,
    });

    const COUNT = isMobile ? 120 : 240;
    const beans = new THREE.InstancedMesh(beanGeo, beanMat, COUNT);
    beans.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    scene.add(beans);

    // world volume the beans live in (scroll moves the whole cloud upward)
    const SPAN_Y = 44;                 // total vertical spread
    const SCROLL_TRAVEL = SPAN_Y - 10; // how far the cloud travels over the full page
    const rand = (a, b) => a + Math.random() * (b - a);

    const data = [];
    const color = new THREE.Color();
    const palette = [0x5a3117, 0x6e3f1d, 0x4a2712, 0x7a4a24, 0x3f2210];
    for (let i = 0; i < COUNT; i++) {
      const t = i / COUNT;
      data.push({
        x: rand(-13, 13),
        y: rand(-SPAN_Y + 6, 6),
        z: rand(-7, 3),
        s: rand(0.55, 1.35),
        rx: rand(0, Math.PI * 2), ry: rand(0, Math.PI * 2), rz: rand(0, Math.PI * 2),
        vx: rand(-0.35, 0.35), vy: rand(-0.35, 0.35), vz: rand(-0.35, 0.35),
        fall: rand(0.08, 0.22),
        phase: rand(0, Math.PI * 2),
        // gather (vortex) target around the product visual
        ga: t * Math.PI * 2 * 3 + rand(-0.2, 0.2),
        gr: rand(3.2, 5.2),
        gy: rand(-3.2, 3.2),
        gz: rand(-1.5, 1.5),
      });
      color.setHex(palette[i % palette.length]).offsetHSL(0, rand(-0.04, 0.04), rand(-0.05, 0.06));
      beans.setColorAt(i, color);
    }
    if (beans.instanceColor) beans.instanceColor.needsUpdate = true;

    /* ---------- gold dust ---------- */
    function makeSpriteTexture() {
      const c = document.createElement('canvas');
      c.width = c.height = 64;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, 'rgba(255,236,190,1)');
      g.addColorStop(0.35, 'rgba(230,201,138,0.6)');
      g.addColorStop(1, 'rgba(230,201,138,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 64, 64);
      const tex = new THREE.CanvasTexture(c);
      tex.colorSpace = THREE.SRGBColorSpace;
      return tex;
    }
    const DUST = isMobile ? 260 : 520;
    const dustPos = new Float32Array(DUST * 3);
    const dustSeed = new Float32Array(DUST);
    for (let i = 0; i < DUST; i++) {
      dustPos[i * 3] = rand(-16, 16);
      dustPos[i * 3 + 1] = rand(-SPAN_Y, 8);
      dustPos[i * 3 + 2] = rand(-8, 5);
      dustSeed[i] = rand(0, 100);
    }
    const dustGeo = new THREE.BufferGeometry();
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({
      map: makeSpriteTexture(), size: 0.22, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending, opacity: 0.85, sizeAttenuation: true, color: 0xe6c98a,
    });
    const dust = new THREE.Points(dustGeo, dustMat);
    scene.add(dust);

    /* ---------- state ---------- */
    const state = { scroll: 0, gather: 0, gatherX: -3.6, mx: 0, my: 0, tmx: 0, tmy: 0 };
    const M = new THREE.Matrix4();
    const Q = new THREE.Quaternion();
    const E = new THREE.Euler();
    const P = new THREE.Vector3();
    const S = new THREE.Vector3();
    const clock = new THREE.Clock();

    window.addEventListener('pointermove', (e) => {
      state.tmx = (e.clientX / window.innerWidth - 0.5) * 2;
      state.tmy = (e.clientY / window.innerHeight - 0.5) * 2;
    }, { passive: true });

    function computeGatherX() {
      // the product card sits in the left column on desktop, centred on mobile
      state.gatherX = window.innerWidth > 768 ? -3.6 : 0;
    }
    computeGatherX();

    /* ---------- frame loop ---------- */
    let last = 0;
    function render() {
      requestAnimationFrame(render);
      const t = clock.getElapsedTime();
      const dt = Math.min(0.05, t - last);
      last = t;

      // camera parallax
      state.mx += (state.tmx - state.mx) * 0.04;
      state.my += (state.tmy - state.my) * 0.04;
      camera.position.x = state.mx * 0.9;
      camera.position.y = -state.my * 0.6;
      camera.lookAt(0, 0, 0);

      const cloudY = state.scroll * SCROLL_TRAVEL; // cloud moves up as we scroll down
      const g = state.gather;
      const spin = reduced ? 0 : 1;

      for (let i = 0; i < COUNT; i++) {
        const d = data[i];
        if (!reduced) {
          d.y -= d.fall * dt;
          if (d.y + cloudY < -8) d.y += SPAN_Y; // wrap from bottom to top
        }
        const bx = d.x + Math.sin(t * 0.35 + d.phase) * 0.35;
        const by = d.y + cloudY + Math.cos(t * 0.28 + d.phase) * 0.25;
        const bz = d.z;

        if (g > 0.001) {
          const a = d.ga + t * 0.25;
          const gx = state.gatherX + Math.cos(a) * d.gr;
          const gy = d.gy + Math.sin(t * 0.6 + d.phase) * 0.25;
          const gz = d.gz + Math.sin(a) * 1.2;
          P.set(bx + (gx - bx) * g, by + (gy - by) * g, bz + (gz - bz) * g);
        } else {
          P.set(bx, by, bz);
        }

        E.set(d.rx + t * d.vx * spin, d.ry + t * d.vy * spin, d.rz + t * d.vz * spin);
        Q.setFromEuler(E);
        const sc = d.s * (1 + g * 0.15);
        S.set(sc, sc, sc);
        M.compose(P, Q, S);
        beans.setMatrixAt(i, M);
      }
      beans.instanceMatrix.needsUpdate = true;

      // dust drift
      dust.position.y = cloudY * 0.6;
      const dp = dust.geometry.attributes.position.array;
      if (!reduced) {
        for (let i = 0; i < DUST; i++) {
          dp[i * 3 + 1] += 0.12 * dt;
          dp[i * 3] += Math.sin(t * 0.5 + dustSeed[i]) * 0.002;
          if (dp[i * 3 + 1] + dust.position.y > 9) dp[i * 3 + 1] -= SPAN_Y + 8;
        }
        dust.geometry.attributes.position.needsUpdate = true;
      }
      dustMat.opacity = 0.55 + Math.sin(t * 0.8) * 0.15 + g * 0.3;

      renderer.render(scene, camera);
    }
    render();

    /* ---------- resize ---------- */
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      computeGatherX();
    });

    window.PRINTEMPS_SCENE = {
      setScroll(p) { state.scroll = Math.max(0, Math.min(1, p)); },
      setGather(v) { state.gather = Math.max(0, Math.min(1, v)); },
    };
  }

  if (window.THREE) boot();
  else window.addEventListener('three-ready', boot, { once: true });
})();
