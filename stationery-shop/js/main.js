// Atelier Lumière — scroll-driven stationery scene
// Three.js (r169) + GSAP ScrollTrigger. All models and textures are procedural.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const params = new URLSearchParams(location.search);
const CAPTURE = params.has('capture');
if (CAPTURE) document.documentElement.classList.add('capture');
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------------ */
/* utilities                                                           */
/* ------------------------------------------------------------------ */
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(20260922);
const rr = (a, b) => a + (b - a) * rand();
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const V3 = (x, y, z) => new THREE.Vector3(x, y, z);

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}
function tex(c, { srgb = true, repeat = null } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}
function grain(g, w, h, amount) {
  const img = g.getImageData(0, 0, w, h);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (rand() - 0.5) * amount;
    d[i] += n; d[i + 1] += n; d[i + 2] += n;
  }
  g.putImageData(img, 0, 0);
}

/* ------------------------------------------------------------------ */
/* procedural textures                                                 */
/* ------------------------------------------------------------------ */
function woodTexture({ base, dark, lines = 150, w = 512, h = 512, planks = 0, repeat = null }) {
  const [c, g] = canvas(w, h);
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < lines; i++) {
    const x0 = rand() * w;
    const a = rr(0.05, 0.28);
    g.strokeStyle = dark;
    g.globalAlpha = a;
    g.lineWidth = rr(0.4, 2.6);
    g.beginPath();
    for (let y = -8; y <= h + 8; y += 6) {
      const x = x0 + Math.sin(y * 0.011 + i) * 7 + Math.sin(y * 0.047 + i * 2.3) * 1.6;
      y === -8 ? g.moveTo(x, y) : g.lineTo(x, y);
    }
    g.stroke();
  }
  // soft figure
  for (let i = 0; i < 18; i++) {
    const grd = g.createRadialGradient(rand() * w, rand() * h, 0, rand() * w, rand() * h, rr(40, 140));
    grd.addColorStop(0, dark); grd.addColorStop(1, 'transparent');
    g.globalAlpha = 0.08; g.fillStyle = grd; g.fillRect(0, 0, w, h);
  }
  g.globalAlpha = 1;
  if (planks) {
    g.strokeStyle = 'rgba(10,5,2,0.75)'; g.lineWidth = 2;
    for (let i = 1; i < planks; i++) { const x = (i / planks) * w; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
  }
  grain(g, w, h, 14);
  return tex(c, { repeat });
}

function noiseTexture(size = 256, repeat = [4, 4]) {
  const [c, g] = canvas(size, size);
  const img = g.createImageData(size, size);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = 110 + rand() * 60;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  return tex(c, { srgb: false, repeat });
}

function goldGradient(g, y0, y1) {
  const grd = g.createLinearGradient(0, y0, 0, y1);
  grd.addColorStop(0, '#f6e3a6'); grd.addColorStop(0.5, '#c9a150'); grd.addColorStop(1, '#8a6424');
  return grd;
}

// Pencil label: canvas u = around the hex, v = along the pencil (top = tip)
function pencilLabel(paint, text, grade) {
  const W = 256, H = 1024, col = W / 6;
  const [c, g] = canvas(W, H);
  g.fillStyle = paint; g.fillRect(0, 0, W, H);
  grain(g, W, H, 6);
  const [m, mg] = canvas(W, H); // metalness (B) + roughness (G) mask
  mg.fillStyle = 'rgb(0,84,0)'; mg.fillRect(0, 0, W, H);
  for (const [ctx, fill] of [[g, null], [mg, 'rgb(0,56,255)']]) {
    ctx.save();
    ctx.translate(col / 2, H * 0.56);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = fill || goldGradient(ctx, -12, 12);
    ctx.font = '600 19px "Cormorant Garamond", Georgia, serif';
    ctx.fillText(text, 0, 1);
    ctx.font = '700 22px "DM Mono", monospace';
    ctx.fillText(grade, -H * 0.36, 1);
    ctx.restore();
  }
  return { map: tex(c), mask: tex(m, { srgb: false }) };
}

function endCapTexture(core) {
  const [c, g] = canvas(128, 128);
  g.fillStyle = '#c99466'; g.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 9; i++) {
    g.strokeStyle = `rgba(120,70,35,${rr(0.15, 0.35)})`; g.lineWidth = rr(0.5, 1.5);
    g.beginPath(); g.arc(64 + rr(-6, 6), 64 + rr(-6, 6), rr(18, 64), 0, Math.PI * 2); g.stroke();
  }
  g.fillStyle = core; g.beginPath(); g.arc(64, 64, 17, 0, Math.PI * 2); g.fill();
  g.strokeStyle = core; g.lineWidth = 6; g.beginPath(); g.arc(64, 64, 61, 0, Math.PI * 2); g.stroke();
  grain(g, 128, 128, 10);
  return tex(c);
}

function paperTexture({ lines = false } = {}) {
  const [c, g] = canvas(512, 512);
  g.fillStyle = '#f2ead8'; g.fillRect(0, 0, 512, 512);
  if (lines) {
    g.strokeStyle = 'rgba(80,110,160,0.35)'; g.lineWidth = 1.2;
    for (let y = 60; y < 500; y += 22) { g.beginPath(); g.moveTo(24, y); g.lineTo(488, y); g.stroke(); }
    g.strokeStyle = 'rgba(190,80,80,0.4)'; g.beginPath(); g.moveTo(70, 20); g.lineTo(70, 500); g.stroke();
  }
  grain(g, 512, 512, 12);
  return tex(c);
}

function pageEdgeTexture() {
  const [c, g] = canvas(64, 512);
  g.fillStyle = '#eee4cf'; g.fillRect(0, 0, 64, 512);
  for (let y = 0; y < 512; y += 2) {
    g.fillStyle = `rgba(120,100,70,${rr(0.04, 0.22)})`; g.fillRect(0, y, 64, 1);
  }
  return tex(c);
}

function leatherBump() {
  const [c, g] = canvas(512, 512);
  g.fillStyle = '#808080'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 5000; i++) {
    g.fillStyle = `rgba(${rand() < 0.5 ? '40,40,40' : '200,200,200'},${rr(0.05, 0.25)})`;
    g.beginPath(); g.arc(rand() * 512, rand() * 512, rr(0.6, 3.2), 0, Math.PI * 2); g.fill();
  }
  return tex(c, { srgb: false, repeat: [2, 2] });
}

function embossTexture() {
  const [c, g] = canvas(512, 700);
  g.clearRect(0, 0, 512, 700);
  g.fillStyle = '#fff';
  g.textAlign = 'center';
  g.font = 'italic 600 62px "Cormorant Garamond", Georgia, serif';
  g.fillText('Atelier Lumière', 256, 300);
  g.font = '500 22px "DM Mono", monospace';
  g.fillText('N O T E B O O K  ·  A5  ·  192 p', 256, 360);
  g.lineWidth = 2; g.strokeStyle = '#fff';
  g.strokeRect(46, 46, 420, 608);
  g.beginPath(); g.arc(256, 190, 26, 0, Math.PI * 2); g.stroke();
  g.beginPath();
  for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2; g.moveTo(256, 190); g.lineTo(256 + Math.cos(a) * 42, 190 + Math.sin(a) * 42); }
  g.stroke();
  return tex(c, { srgb: false });
}

function sleeveTexture(bg, fg, name) {
  const [c, g] = canvas(512, 256);
  g.fillStyle = bg; g.fillRect(0, 0, 512, 256);
  g.fillStyle = fg;
  g.fillRect(0, 26, 512, 8); g.fillRect(0, 222, 512, 8);
  g.textAlign = 'center';
  g.font = 'italic 600 58px "Cormorant Garamond", Georgia, serif';
  g.fillText(name, 256, 140);
  g.font = '500 20px "DM Mono", monospace';
  g.fillText('PLASTIC ERASER · DUST-FREE', 256, 186);
  grain(g, 512, 256, 8);
  return tex(c);
}

function tapePattern(bg, fg, kind) {
  const [c, g] = canvas(256, 128);
  g.fillStyle = bg; g.fillRect(0, 0, 256, 128);
  g.fillStyle = fg; g.strokeStyle = fg;
  if (kind === 'dots') {
    for (let x = 8; x < 256; x += 24) for (let y = 10; y < 128; y += 24) { g.beginPath(); g.arc(x + ((y / 24) % 2) * 12, y, 5, 0, Math.PI * 2); g.fill(); }
  } else if (kind === 'stripe') {
    g.lineWidth = 12;
    for (let x = -128; x < 384; x += 32) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x + 128, 128); g.stroke(); }
  } else {
    g.lineWidth = 3;
    for (let x = 0; x < 256; x += 32) for (let y = 0; y < 128; y += 32) { g.strokeRect(x + 6, y + 6, 20, 20); }
  }
  grain(g, 256, 128, 10);
  return tex(c, { repeat: [6, 1] });
}

function ringSideTexture(color) {
  const [c, g] = canvas(256, 256);
  g.fillStyle = color; g.fillRect(0, 0, 256, 256);
  for (let r = 60; r < 128; r += 1.5) {
    g.strokeStyle = `rgba(255,255,255,${rr(0.02, 0.14)})`; g.lineWidth = 1;
    g.beginPath(); g.arc(128, 128, r, 0, Math.PI * 2); g.stroke();
  }
  return tex(c);
}

function rulerTicks() {
  const W = 2048, H = 224;
  const [c, g] = canvas(W, H);
  g.clearRect(0, 0, W, H);
  g.fillStyle = 'rgba(20,20,24,0.92)';
  const pad = 64, mm = (W - pad * 2) / 150;
  for (let i = 0; i <= 150; i++) {
    const x = pad + i * mm;
    const len = i % 10 === 0 ? 70 : i % 5 === 0 ? 48 : 30;
    g.fillRect(x - 1.2, 0, 2.4, len);
    if (i % 10 === 0) {
      g.font = '500 30px "DM Mono", monospace'; g.textAlign = 'center';
      g.fillText(String(i / 10), x, 108);
    }
  }
  g.font = 'italic 600 34px "Cormorant Garamond", Georgia, serif'; g.textAlign = 'left';
  g.fillText('Atelier Lumière  ·  acrylic 15 cm', pad, 186);
  return tex(c);
}

function glowTexture() {
  const [c, g] = canvas(256, 256);
  const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grd.addColorStop(0, 'rgba(255,240,210,1)');
  grd.addColorStop(0.18, 'rgba(255,200,120,0.55)');
  grd.addColorStop(0.5, 'rgba(255,150,80,0.12)');
  grd.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
  return tex(c);
}

/* ------------------------------------------------------------------ */
/* renderer / scene                                                    */
/* ------------------------------------------------------------------ */
const canvasEl = document.getElementById('webgl');
const renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, CAPTURE ? 1 : 1.75));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.98;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.5;
scene.fog = new THREE.FogExp2(0x120c1c, 0.034);

const camera = new THREE.PerspectiveCamera(35, window.innerWidth / window.innerHeight, 0.1, 200);

// sky dome: night atelier gradient with faint nebula
const sky = new THREE.Mesh(
  new THREE.SphereGeometry(80, 48, 24),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { uTime: { value: 0 } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `
      varying vec3 vDir; uniform float uTime;
      float h(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,45.164)))*43758.5453); }
      float n(vec3 p){ vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
        return mix(mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y),
                   mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y),f.z); }
      float fbm(vec3 p){ float s=0., a=.5; for(int i=0;i<5;i++){ s+=a*n(p); p*=2.03; a*=.5; } return s; }
      void main(){
        vec3 d = normalize(vDir);
        float y = d.y;
        vec3 horizon = vec3(0.090,0.040,0.050);
        vec3 mid = vec3(0.030,0.018,0.060);
        vec3 top = vec3(0.006,0.006,0.018);
        vec3 col = mix(horizon, mid, smoothstep(-0.15, 0.25, y));
        col = mix(col, top, smoothstep(0.25, 0.9, y));
        float neb = fbm(d*3.0 + vec3(0.0, uTime*0.01, 0.0));
        col += vec3(0.10,0.05,0.16) * pow(neb, 3.0) * 1.6;
        col += vec3(0.16,0.09,0.04) * pow(fbm(d*5.0+7.0), 4.0);
        float st = step(0.9985, h(floor(d*420.0)));
        col += st * vec3(0.9,0.85,1.0) * (0.5 + 0.5*sin(uTime*2.0 + h(floor(d*420.0))*50.0));
        gl_FragColor = vec4(col, 1.0);
      }`,
  })
);
scene.add(sky);

// lights
const key = new THREE.DirectionalLight(0xffe0bd, 2.8);
key.position.set(4.5, 9, 5.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 30 });
key.shadow.bias = -0.0003;
key.shadow.normalBias = 0.015;
key.target.position.set(0, -1.5, 0);
scene.add(key, key.target);

const rim = new THREE.SpotLight(0x86a8ff, 160, 40, 0.7, 0.8, 2);
rim.position.set(-7, 5, -6);
rim.target.position.set(0, 0, 0);
scene.add(rim, rim.target);

scene.add(new THREE.HemisphereLight(0x8a7cff, 0x2b1a0e, 0.35));

const magic = new THREE.PointLight(0xffbf73, 0, 14, 2);
scene.add(magic);

/* ------------------------------------------------------------------ */
/* shared materials                                                    */
/* ------------------------------------------------------------------ */
const noise = noiseTexture();
const woodPencil = woodTexture({ base: '#dcae7c', dark: '#9b6a3e', lines: 110, w: 256, h: 512 });
const MAT = {
  wood: new THREE.MeshStandardMaterial({ map: woodPencil, roughness: 0.78, bumpMap: noise, bumpScale: 0.6 }),
  graphite: new THREE.MeshStandardMaterial({ color: 0x2b2b30, metalness: 0.55, roughness: 0.38 }),
  gold: new THREE.MeshStandardMaterial({ color: 0xd9ad55, metalness: 1, roughness: 0.24 }),
  silver: new THREE.MeshStandardMaterial({ color: 0xdadde2, metalness: 1, roughness: 0.18 }),
  eraser: new THREE.MeshStandardMaterial({ color: 0xe79a93, roughness: 0.86, bumpMap: noise, bumpScale: 1.2 }),
  chrome: new THREE.MeshStandardMaterial({ color: 0xf2f2f5, metalness: 1, roughness: 0.12 }),
  black: new THREE.MeshStandardMaterial({ color: 0x08080a, roughness: 0.4 }),
};

/* ------------------------------------------------------------------ */
/* models                                                              */
/* ------------------------------------------------------------------ */
const P = { r: 0.085, body: 2.6, cone: 0.5, lead: 0.023 };
const hb = P.body / 2;
function shadowAll(o) { o.traverse((m) => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } }); return o; }

const GEO = (() => {
  const hex = new THREE.CylinderGeometry(P.r, P.r, P.body, 6, 1).toNonIndexed();
  hex.computeVertexNormals();
  const coneBaseHex = P.r * 0.866, coneBaseRound = P.r * 0.92;
  const tipLen = (r0) => (P.lead * P.cone) / (r0 - P.lead);
  const ferrulePts = [];
  const fl = 0.28, fr = P.r * 0.94;
  ferrulePts.push(new THREE.Vector2(0.0001, 0.004));
  for (let i = 0; i <= 56; i++) {
    const y = -(i / 56) * fl;
    const nearEnd = i < 12 || i > 44;
    const ridge = nearEnd ? 0.0045 * Math.pow(Math.abs(Math.sin(i * Math.PI / 3)), 0.6) : 0;
    const groove = (i === 22 || i === 34) ? -0.004 : 0;
    ferrulePts.push(new THREE.Vector2(fr + ridge + groove, y));
  }
  ferrulePts.push(new THREE.Vector2(0.0001, -fl));
  const re = P.r * 0.82, er = [];
  er.push(new THREE.Vector2(0.0001, 0));
  er.push(new THREE.Vector2(re, 0));
  er.push(new THREE.Vector2(re, -0.2));
  for (let i = 1; i <= 10; i++) { const a = (i / 10) * Math.PI / 2; er.push(new THREE.Vector2(re - 0.035 + 0.035 * Math.cos(a), -0.2 - 0.035 * Math.sin(a))); }
  er.push(new THREE.Vector2(0.0001, -0.235));
  return {
    hex,
    round: new THREE.CylinderGeometry(coneBaseRound, coneBaseRound, P.body, 40, 1),
    coneHex: new THREE.CylinderGeometry(P.lead, coneBaseHex, P.cone, 40, 1, true),
    coneRound: new THREE.CylinderGeometry(P.lead, coneBaseRound, P.cone, 40, 1, true),
    tipHex: new THREE.CylinderGeometry(0.002, P.lead, tipLen(coneBaseHex), 24),
    tipRound: new THREE.CylinderGeometry(0.002, P.lead, tipLen(coneBaseRound), 24),
    tipLenHex: tipLen(coneBaseHex), tipLenRound: tipLen(coneBaseRound),
    ferrule: new THREE.LatheGeometry(ferrulePts, 48),
    eraser: new THREE.LatheGeometry(er, 40),
    band: new THREE.CylinderGeometry(coneBaseRound + 0.0015, coneBaseRound + 0.0015, 0.022, 40, 1, true),
  };
})();

function graphitePencil(paint, grade) {
  const g = new THREE.Group();
  const lbl = pencilLabel(paint, 'Atelier Lumière  ·  Fine Graphite', grade);
  const paintMat = new THREE.MeshPhysicalMaterial({
    map: lbl.map, metalnessMap: lbl.mask, roughnessMap: lbl.mask, metalness: 1, roughness: 1,
    clearcoat: 0.9, clearcoatRoughness: 0.12,
  });
  const body = new THREE.Mesh(GEO.hex, [paintMat, MAT.wood, paintMat]);
  const cone = new THREE.Mesh(GEO.coneHex, MAT.wood); cone.position.y = hb + P.cone / 2;
  const tip = new THREE.Mesh(GEO.tipHex, MAT.graphite); tip.position.y = hb + P.cone + GEO.tipLenHex / 2;
  const fer = new THREE.Mesh(GEO.ferrule, MAT.gold); fer.position.y = -hb;
  const era = new THREE.Mesh(GEO.eraser, MAT.eraser); era.position.y = -hb - 0.26;
  g.add(body, cone, tip, fer, era);
  g.rotation.order = 'ZXY';
  return shadowAll(g);
}

const colorMatCache = new Map();
function coloredPencil(color) {
  const g = new THREE.Group();
  const c = new THREE.Color().setHSL(...color);
  const hex = '#' + c.getHexString();
  const paint = new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.38, clearcoat: 0.7, clearcoatRoughness: 0.18 });
  const lead = new THREE.MeshStandardMaterial({ color: c, roughness: 0.62 });
  const end = new THREE.MeshStandardMaterial({ map: endCapTexture(hex), roughness: 0.8 });
  const body = new THREE.Mesh(GEO.round, [paint, MAT.wood, end]);
  const cone = new THREE.Mesh(GEO.coneRound, MAT.wood); cone.position.y = hb + P.cone / 2;
  const tip = new THREE.Mesh(GEO.tipRound, lead); tip.position.y = hb + P.cone + GEO.tipLenRound / 2;
  const band1 = new THREE.Mesh(GEO.band, MAT.gold); band1.position.y = -hb + 0.1;
  const band2 = new THREE.Mesh(GEO.band, MAT.gold); band2.position.y = -hb + 0.145;
  g.add(body, cone, tip, band1, band2);
  g.rotation.order = 'ZXY';
  colorMatCache.set(g, hex);
  return shadowAll(g);
}

function fountainPen() {
  const g = new THREE.Group();
  const resin = new THREE.MeshPhysicalMaterial({ color: 0x0c1a2e, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.04, sheen: 0.2 });
  const pts = [
    [0.0001, -1.55], [0.06, -1.55], [0.09, -1.51], [0.104, -1.44], [0.11, -1.2], [0.113, 0.0], [0.112, 0.5],
    [0.1, 0.56], [0.092, 0.6], [0.086, 0.85], [0.08, 1.0], [0.074, 1.06], [0.0001, 1.06],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const barrel = new THREE.Mesh(new THREE.LatheGeometry(pts, 64), resin);
  const bandGeo = new THREE.CylinderGeometry(0.116, 0.116, 0.045, 64, 1, true);
  const b1 = new THREE.Mesh(bandGeo, MAT.gold); b1.position.y = 0.47;
  const b2 = new THREE.Mesh(bandGeo, MAT.gold); b2.position.y = -1.3;
  const fin = new THREE.Mesh(new THREE.SphereGeometry(0.06, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), MAT.gold);
  fin.position.y = -1.53;
  const nibMat = new THREE.MeshStandardMaterial({ color: 0xe4bc6a, metalness: 1, roughness: 0.2, side: THREE.DoubleSide });
  const nib = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.074, 0.46, 40, 6, true, -1.05, 2.1), nibMat);
  nib.position.y = 1.06 + 0.23;
  const feed = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.066, 0.36, 24), MAT.black);
  feed.position.set(0, 1.06 + 0.17, -0.014);
  const slit = new THREE.Mesh(new THREE.BoxGeometry(0.005, 0.2, 0.01), MAT.black);
  slit.position.set(0, 1.42, 0.021); slit.rotation.x = -0.15;
  const hole = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.02, 16), MAT.black);
  hole.rotation.x = Math.PI / 2; hole.position.set(0, 1.3, 0.036);
  g.add(barrel, b1, b2, fin, nib, feed, slit, hole);
  g.rotation.order = 'ZXY';
  return shadowAll(g);
}

function eraserBlock(bg, fg, name) {
  const g = new THREE.Group();
  const rubber = new THREE.MeshStandardMaterial({ color: 0xf4f2ec, roughness: 0.9, bumpMap: noise, bumpScale: 0.8 });
  const block = new THREE.Mesh(new RoundedBoxGeometry(1.1, 0.4, 0.55, 4, 0.05), rubber);
  const sleeve = new THREE.Mesh(
    new RoundedBoxGeometry(0.72, 0.42, 0.57, 2, 0.012),
    new THREE.MeshPhysicalMaterial({ map: sleeveTexture(bg, fg, name), roughness: 0.55, clearcoat: 0.3 })
  );
  sleeve.position.x = 0.12;
  g.add(block, sleeve);
  return shadowAll(g);
}

function paperClip(mat) {
  const pts = [];
  const line = (x0, y0, x1, y1, n = 10) => { for (let i = 0; i < n; i++) { const t = i / n; pts.push(V3(lerp(x0, x1, t), lerp(y0, y1, t), 0)); } };
  const arc = (cx, cy, r, a0, a1, n = 18) => { for (let i = 0; i < n; i++) { const a = lerp(a0, a1, i / n); pts.push(V3(cx + Math.cos(a) * r, cy + Math.sin(a) * r, 0)); } };
  line(0.07, 0.2, 0.07, -0.45);
  arc(0, -0.45, 0.07, 0, -Math.PI);
  line(-0.07, -0.45, -0.07, 0.55, 16);
  arc(0.035, 0.55, 0.105, Math.PI, 0);
  line(0.14, 0.55, 0.14, -0.6, 16);
  arc(0, -0.6, 0.14, 0, -Math.PI);
  line(-0.14, -0.6, -0.14, 0.35, 14);
  pts.push(V3(-0.14, 0.35, 0));
  const curve = new THREE.CatmullRomCurve3(pts);
  const m = new THREE.Mesh(new THREE.TubeGeometry(curve, 260, 0.013, 12), mat);
  const g = new THREE.Group(); g.add(m); g.scale.setScalar(0.7);
  return shadowAll(g);
}

function ruler() {
  const g = new THREE.Group();
  const acrylic = new THREE.MeshPhysicalMaterial({
    color: 0xeef6ff, transmission: 1, thickness: 0.05, roughness: 0.06, ior: 1.49,
    metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03, attenuationColor: new THREE.Color(0xcfe6ff), attenuationDistance: 1.5,
  });
  const body = new THREE.Mesh(new RoundedBoxGeometry(3.2, 0.035, 0.42, 2, 0.008), acrylic);
  const ticks = new THREE.Mesh(
    new THREE.PlaneGeometry(3.2, 0.35),
    new THREE.MeshStandardMaterial({ map: rulerTicks(), transparent: true, roughness: 0.5, depthWrite: false })
  );
  ticks.rotation.x = -Math.PI / 2; ticks.position.set(0, 0.0185, -0.03);
  g.add(body, ticks);
  body.castShadow = true; body.receiveShadow = true;
  return g;
}

function washiTape(bg, fg, kind) {
  const g = new THREE.Group();
  const ro = 0.36, ri = 0.27, w = 0.15;
  const outer = new THREE.Mesh(
    new THREE.CylinderGeometry(ro, ro, w, 72, 1, true),
    new THREE.MeshPhysicalMaterial({ map: tapePattern(bg, fg, kind), roughness: 0.62, sheen: 0.4, sheenColor: new THREE.Color(0xffffff) })
  );
  const sideMat = new THREE.MeshStandardMaterial({ map: ringSideTexture(bg), roughness: 0.7, side: THREE.DoubleSide, transparent: true, opacity: 0.96 });
  const top = new THREE.Mesh(new THREE.RingGeometry(ri, ro, 72), sideMat); top.rotation.x = -Math.PI / 2; top.position.y = w / 2;
  const bot = top.clone(); bot.rotation.x = Math.PI / 2; bot.position.y = -w / 2;
  const core = new THREE.Mesh(new THREE.CylinderGeometry(ri, ri, w, 48, 1, true), new THREE.MeshStandardMaterial({ color: 0xa27a52, roughness: 0.95, side: THREE.DoubleSide, bumpMap: noise, bumpScale: 1 }));
  g.add(outer, top, bot, core);
  return shadowAll(g);
}

const glowTex = glowTexture();
function glowSprite(color = 0xffd9a0) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
  s.renderOrder = 10;
  return s;
}

function notebook() {
  const g = new THREE.Group();
  const leather = new THREE.MeshPhysicalMaterial({
    color: 0x1b3a33, roughness: 0.62, bumpMap: leatherBump(), bumpScale: 1.4, sheen: 0.35, sheenColor: new THREE.Color(0x6d9a8a),
  });
  const W = 2.0, D = 2.7;
  const back = new THREE.Mesh(new RoundedBoxGeometry(W + 0.05, 0.03, D + 0.05, 2, 0.012), leather);
  back.position.y = 0.015;
  const edge = new THREE.MeshStandardMaterial({ map: pageEdgeTexture(), roughness: 0.9 });
  const pageTop = new THREE.MeshStandardMaterial({ map: paperTexture({ lines: true }), roughness: 0.85, emissive: 0xffc98a, emissiveIntensity: 0 });
  const pages = new THREE.Mesh(new THREE.BoxGeometry(W - 0.06, 0.2, D - 0.08), [edge, edge, pageTop, edge, edge, edge]);
  pages.position.set(0.01, 0.13, 0);
  const spine = new THREE.Mesh(new RoundedBoxGeometry(0.05, 0.27, D + 0.05, 2, 0.02), leather);
  spine.position.set(-W / 2 - 0.01, 0.135, 0);
  const pivot = new THREE.Group(); pivot.position.set(-W / 2 - 0.01, 0.255, 0);
  const cover = new THREE.Mesh(new RoundedBoxGeometry(W + 0.05, 0.03, D + 0.05, 2, 0.012), leather);
  cover.position.x = W / 2 + 0.01;
  const emboss = new THREE.Mesh(
    new THREE.PlaneGeometry(W * 0.78, D * 0.78),
    new THREE.MeshStandardMaterial({ color: 0xd9b064, metalness: 1, roughness: 0.3, alphaMap: embossTexture(), transparent: true })
  );
  emboss.rotation.x = -Math.PI / 2; emboss.position.y = 0.0162;
  cover.add(emboss);
  pivot.add(cover);
  // ribbon bookmark
  const ribbon = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.004, 0.9), new THREE.MeshStandardMaterial({ color: 0x8e1f2c, roughness: 0.5 }));
  ribbon.position.set(0.45, 0.232, D / 2 + 0.3);
  const glow = glowSprite(0xffd49a); glow.position.set(0, 0.6, 0);
  g.add(back, pages, spine, pivot, ribbon, glow);
  shadowAll(g);
  emboss.castShadow = false;
  g.userData = { pivot, pageTop, glow };
  return g;
}

/* desk + glass cup ------------------------------------------------- */
const DESK_Y = -2;
const desk = new THREE.Mesh(
  new THREE.PlaneGeometry(44, 44),
  new THREE.MeshPhysicalMaterial({
    map: woodTexture({ base: '#4a2c19', dark: '#1f1008', lines: 260, w: 1024, h: 1024, planks: 4, repeat: [5, 5] }),
    roughness: 0.48, clearcoat: 0.35, clearcoatRoughness: 0.4, bumpMap: noise, bumpScale: 0.2,
  })
);
desk.rotation.x = -Math.PI / 2; desk.position.y = DESK_Y; desk.receiveShadow = true;
scene.add(desk);

const CUP = V3(1.7, DESK_Y, 0.1);
const cup = new THREE.Group();
{
  const glass = new THREE.MeshPhysicalMaterial({
    color: 0xffffff, transmission: 1, thickness: 0.12, roughness: 0.04, ior: 1.5, metalness: 0,
    clearcoat: 1, clearcoatRoughness: 0.02, side: THREE.DoubleSide, attenuationColor: new THREE.Color(0xe8fff4), attenuationDistance: 2,
  });
  const wall = new THREE.Mesh(new THREE.CylinderGeometry(0.76, 0.72, 1.35, 72, 1, true), glass);
  wall.position.y = 0.675;
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.72, 0.1, 72), glass);
  base.position.y = 0.05;
  const lip = new THREE.Mesh(new THREE.TorusGeometry(0.76, 0.012, 12, 96), glass);
  lip.rotation.x = Math.PI / 2; lip.position.y = 1.35;
  cup.add(wall, base, lip);
  cup.position.copy(CUP);
  wall.castShadow = false; base.receiveShadow = true;
}
scene.add(cup);
const cupSink = (p) => clamp01(p - 3.6) / 0.4;
const cupGlow = glowSprite(0xffcf8a); cupGlow.position.copy(CUP).add(V3(0, 1.6, 0));
scene.add(cupGlow);

/* ------------------------------------------------------------------ */
/* actors + keyframes (6 chapters: 0 hero … 5 visit)                    */
/* ------------------------------------------------------------------ */
const actors = [];
function actor(obj, keys, { delay = rr(0, 0.22), arcs = null } = {}) {
  const a = {
    obj, keys, delay,
    arcs: arcs || [0, 1, 2, 3, 4].map(() => V3(rr(-0.8, 0.8), rr(0.2, 1.4), rr(-0.8, 0.8))),
    w: rr(0.5, 1.1), ph: rr(0, Math.PI * 2),
  };
  actors.push(a);
  scene.add(obj);
  return a;
}
const K = (p, r = [0, 0, 0], s = 1, f = 1) => ({ p: V3(...p), r: V3(...r), s, f });
const qToR = (dir, spin = 0) => {
  const q = new THREE.Quaternion().setFromUnitVectors(V3(0, 1, 0), dir.clone().normalize());
  const e = new THREE.Euler().setFromQuaternion(q, 'ZXY');
  return [e.x, e.y + spin, e.z];
};

// helix for chapter 4 (gallery vortex)
let helixIndex = 0;
function helixKey() {
  const j = helixIndex++;
  const a = j * 0.62;
  const R = 3.4 + (j % 3) * 0.7;
  const pos = [Math.cos(a) * R * 1.25, Math.sin(a) * R * 0.78, 2.5 - j * 0.34];
  const tangent = V3(-Math.sin(a), Math.cos(a), rr(-0.4, 0.4));
  return K(pos, qToR(tangent, rr(0, 6)), 1, 1);
}

/* pencils ---------------------------------------------------------- */
const GRADES = ['6B', '4B', '2B', 'B', 'HB', '2H'];
const PAINTS = ['#17392c', '#141416', '#c9951f', '#1c2745', '#4f1720', '#e8e1cf'];
const COLORED_N = 24;
const pencils = [];
GRADES.forEach((gr, i) => pencils.push({ obj: graphitePencil(PAINTS[i], gr), kind: 'g', i, bottom: hb + 0.5 }));
for (let i = 0; i < COLORED_N; i++) {
  const h = i / COLORED_N;
  const l = i % 3 === 0 ? 0.3 : i % 3 === 1 ? 0.38 : 0.46;
  pencils.push({ obj: coloredPencil([h, 0.82, l]), kind: 'c', i, bottom: hb });
}

// cup placement: sunflower spiral, tips up, leaning outwards
const order = pencils.map((_, i) => i).sort(() => rand() - 0.5);
order.forEach((pi, k) => {
  const pc = pencils[pi];
  const rho = 0.56 * Math.sqrt((k + 0.5) / pencils.length);
  const ang = k * 2.39996;
  const dx = Math.cos(ang), dz = Math.sin(ang);
  const lean = 0.08 + rho * 0.42;
  const dir = V3(dx * Math.sin(lean), Math.cos(lean), dz * Math.sin(lean));
  const bottom = V3(CUP.x + dx * rho, DESK_Y + 0.11, CUP.z + dz * rho);
  const center = bottom.clone().addScaledVector(dir, pc.bottom);
  pc.k0 = K(center.toArray(), qToR(dir, rr(0, 6)), 1, 0);
});

pencils.forEach((pc) => {
  const keys = [pc.k0];
  if (pc.kind === 'g') {
    // ch1: a parallel lineup of hardness grades, tips to the upper right
    const i = pc.i, t = i - 2.5;
    const dir = V3(Math.sin(0.62), Math.cos(0.62), 0.12);
    keys.push(K([1.75 + t * 0.34, -0.1 - t * 0.12 + (i % 2) * 0.25, 0.6 - Math.abs(t) * 0.28], qToR(dir, 0.3 + i * 0.35), 1, 1));
    // ch2: drift far back to the right
    keys.push(K([4.2 + i * 0.6, 2.4 - i * 0.5, -7 - i * 0.4], [rr(-1, 1), rr(0, 6), rr(-1, 1)], 1, 1));
    // ch3: sunburst halo behind the notebook
    const a3 = (pc.i / 6) * Math.PI * 2 + 0.2;
    keys.push(K([1.4 + Math.cos(a3) * 5.2, 0.6 + Math.sin(a3) * 3.6, -8], qToR(V3(Math.cos(a3), Math.sin(a3), 0.2), 0), 1, 1));
    keys.push(helixKey());
    // ch5: flat lay
    keys.push(K([0.15 + i * 0.22, DESK_Y + 0.079, 0.0], [Math.PI / 2, Math.PI / 6, 0], 1, 0));
  } else {
    const i = pc.i;
    // ch1: slow ring far behind
    const a1 = (i / COLORED_N) * Math.PI * 2;
    keys.push(K([Math.cos(a1) * 7.5, 1.2 + Math.sin(a1) * 4.2, -10], [0, rr(0, 6), a1], 1, 1));
    // ch2: blooming colour flower facing the camera
    const a2 = (i / COLORED_N) * Math.PI * 2 + Math.PI / 2;
    const d2 = V3(Math.cos(a2) * 0.62, Math.sin(a2) * 0.62, 0.78).normalize();
    const W = V3(-1.55, 0.05, -2.4);
    keys.push(K(W.clone().addScaledVector(d2, 0.62 + hb).toArray(), qToR(d2, rr(0, 6)), 1, 1));
    // ch3: part of the sunburst halo
    const a3 = (i / COLORED_N) * Math.PI * 2;
    const R3 = 6.4 + (i % 2) * 1.1;
    keys.push(K([1.4 + Math.cos(a3) * R3, 0.6 + Math.sin(a3) * R3 * 0.72, -10 - (i % 2)], qToR(V3(Math.cos(a3), Math.sin(a3), 0.1), rr(0, 6)), 1, 1));
    keys.push(helixKey());
    // ch5: flat lay, one row of 24 like a tin set
    keys.push(K([-5.35 + i * 0.19, DESK_Y + 0.079, 0.05], [Math.PI / 2, 0, 0], 1, 0));
  }
  const arcs = [
    V3(rr(-1.2, 1.2), rr(2.2, 3.6), rr(-0.6, 1.2)),
    V3(rr(-1, 1), rr(0.3, 1.5), rr(-1, 1)),
    V3(rr(-1, 1), rr(0.3, 1.5), rr(-1, 1)),
    V3(rr(-1.5, 1.5), rr(-1, 1), rr(0, 1.5)),
    V3(rr(-0.5, 0.5), rr(1.2, 2.4), rr(-0.5, 0.5)),
  ];
  pc.actor = actor(pc.obj, keys, { arcs, delay: rr(0, 0.25) });
});

/* notebook + stationery -------------------------------------------- */
const book = notebook();
const N3 = V3(1.45, -1.0, -0.9); // notebook in chapter 3
const bookRot3 = [1.05, -0.25, 0.08];
const bookA = actor(book, [
  K([-2.9, DESK_Y, -1.6], [0, 0.35, 0], 1, 0),
  K([-6.5, -4.2, -7], [0.6, 0.8, 0.2], 1, 1),
  K([N3.x, N3.y - 3.5, N3.z - 2], [0.9, -0.2, 0.1], 1, 1),
  K(N3.toArray(), bookRot3, 1, 0.35),
  helixKey(),
  K([3.45, DESK_Y, 0.1], [0, 0, 0], 1, 0),
], { delay: 0 });
bookA.coverKeys = [0, 0, 0, 2.55, 1.1, 0];
bookA.glowKeys = [0, 0, 0.2, 1, 0.25, 0];

// helper: a point on/above the open notebook, in world space for ch3
const bookMatrix3 = new THREE.Matrix4().compose(N3, new THREE.Quaternion().setFromEuler(new THREE.Euler(...bookRot3)), V3(1, 1, 1));
const fromBook = (x, y, z) => V3(x, y, z).applyMatrix4(bookMatrix3);
const hidden = (p) => K(p.toArray(), [0, 0, 0], 0.001, 0);

function stationery(obj, deskKey, burstPos, burstRot, flatKey) {
  const inside = fromBook(0.3, 0.2, 0);
  const keys = [
    deskKey,
    hidden(V3(-6.5, -4.2, -7)),
    hidden(inside),
    K(burstPos.toArray(), burstRot, 1, 1),
    helixKey(),
    flatKey,
  ];
  const arcs = [V3(0, 1.5, 0), V3(0, 0, 0), V3(0, 0, 0), V3(rr(-0.5, 0.5), rr(0.8, 1.6), rr(0.2, 1)), V3(0, 1.5, 0)];
  return actor(obj, keys, { arcs, delay: rr(0, 0.3) });
}

const pen = fountainPen();
stationery(pen,
  K([-0.4, DESK_Y + 0.113, 1.9], [0, 0.3, -Math.PI / 2 - 0.25], 1, 0),
  fromBook(-0.1, 2.3, 0.2), [0.25, 1.2, -0.75],
  K([1.75, DESK_Y + 0.113, 0.0], [Math.PI / 2, 0, 0], 1, 0));

const rul = ruler();
stationery(rul,
  K([-2.6, DESK_Y + 0.018, 1.05], [0, 0.18, 0], 1, 0),
  fromBook(0.1, 1.2, -2.2), [0.9, 0.3, 0.35],
  K([-2.75, DESK_Y + 0.018, 2.55], [0, 0, 0], 1, 0));

const erasers = [
  eraserBlock('#1f3f78', '#f4efe2', 'Lumière'),
  eraserBlock('#e9b7b1', '#5a2a2c', 'Lumière'),
];
stationery(erasers[0],
  K([-1.1, DESK_Y + 0.2, -0.6], [0, -0.5, 0], 1, 0),
  fromBook(1.9, 1.3, 0.8), [0.6, 0.9, 0.4],
  K([0.55, DESK_Y + 0.2, -2.65], [0, 0, 0], 1, 0));
stationery(erasers[1],
  K([4.1, DESK_Y + 0.2, 1.3], [0, 0.4, 0], 1, 0),
  fromBook(-1.8, 0.9, 1.4), [-0.4, -0.7, 0.3],
  K([1.95, DESK_Y + 0.2, -2.65], [0, 0, 0], 1, 0));

const tapes = [
  washiTape('#d9a441', '#fff6dc', 'dots'),
  washiTape('#6f8fa8', '#eef4f7', 'stripe'),
  washiTape('#b9585b', '#f9e8e2', 'grid'),
];
[
  [[-4.2, DESK_Y + 0.075, 0.2], [2.2, 1.1, 1.2], [1.2, 0.2, 0.3]],
  [[-3.7, DESK_Y + 0.075, 1.1], [-1.9, 1.8, 0.4], [0.3, 0.1, -0.9]],
  [[3.9, DESK_Y + 0.225, 0.2], [1.3, 2.7, 1.5], [1.4, 0, 0.5]],
].forEach(([desk0, burst, rot], i) => {
  const deskKey = i === 2
    ? K(desk0, [0, 0, 0], 1, 0)
    : K(desk0, [0, 0, 0], 1, 0);
  stationery(tapes[i], deskKey, fromBook(...burst), rot, K([-4.2 + i * 0.95, DESK_Y + 0.075, -2.65], [0, 0, 0], 1, 0));
});
// the third tape sits stacked on the first one in the hero
actors[actors.length - 1].keys[0] = K([-4.2, DESK_Y + 0.225, 0.2], [0, 0, 0], 1, 0);

const clipMats = [MAT.chrome, MAT.chrome, MAT.gold,
  new THREE.MeshPhysicalMaterial({ color: 0xe0a7b4, roughness: 0.35, clearcoat: 1 }),
  new THREE.MeshPhysicalMaterial({ color: 0x7fb2a3, roughness: 0.35, clearcoat: 1 }),
  MAT.chrome];
clipMats.forEach((m, i) => {
  const clip = paperClip(m);
  const a = (i / 6) * Math.PI * 2;
  stationery(clip,
    K([-0.2 + i * 0.28 + rr(-0.1, 0.1), DESK_Y + 0.01, -1.4 + rr(-0.2, 0.2)], [-Math.PI / 2, 0, rr(-0.8, 0.8)], 1, 0),
    fromBook(Math.cos(a) * 1.5 + 0.2, 1.7 + Math.sin(a) * 0.6, Math.sin(a) * 1.3), [rr(-1, 1), rr(-1, 1), rr(-1, 1)],
    K([0.5 + i * 0.58, DESK_Y + 0.01, 2.6], [-Math.PI / 2, 0, 0.12 * (i % 2 ? 1 : -1)], 1, 0));
});

/* ------------------------------------------------------------------ */
/* magic dust                                                          */
/* ------------------------------------------------------------------ */
const DUST = window.innerWidth < 700 ? 900 : 1700;
const dustGeo = new THREE.BufferGeometry();
{
  const pos = new Float32Array(DUST * 3), col = new Float32Array(DUST * 3), sc = new Float32Array(DUST), sd = new Float32Array(DUST);
  const palette = [new THREE.Color(1.0, 0.78, 0.42), new THREE.Color(1.0, 0.9, 0.7), new THREE.Color(0.55, 0.75, 1.0), new THREE.Color(1.0, 0.55, 0.7)];
  for (let i = 0; i < DUST; i++) {
    const r = Math.pow(rand(), 0.6) * 11;
    const a = rand() * Math.PI * 2;
    pos[i * 3] = Math.cos(a) * r; pos[i * 3 + 1] = rr(-2.2, 6); pos[i * 3 + 2] = Math.sin(a) * r - 2;
    const c = palette[rand() < 0.72 ? (rand() < 0.5 ? 0 : 1) : (rand() < 0.5 ? 2 : 3)];
    col.set([c.r, c.g, c.b], i * 3);
    sc[i] = rr(0.4, 1.6); sd[i] = rand();
  }
  dustGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  dustGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  dustGeo.setAttribute('aScale', new THREE.BufferAttribute(sc, 1));
  dustGeo.setAttribute('aSeed', new THREE.BufferAttribute(sd, 1));
}
const dustMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, vertexColors: true,
  uniforms: { uTime: { value: 0 }, uProg: { value: 0 }, uPR: { value: renderer.getPixelRatio() }, uGain: { value: 1 } },
  vertexShader: `
    attribute float aScale; attribute float aSeed;
    uniform float uTime; uniform float uProg; uniform float uPR;
    varying vec3 vColor; varying float vTw;
    void main(){
      vec3 p = position;
      float ang = uTime * 0.04 * (0.4 + aSeed) + uProg * 0.9 * (aSeed - 0.35);
      float c = cos(ang), s = sin(ang);
      p.xz = mat2(c, -s, s, c) * (p.xz + vec2(0.0, 2.0)) - vec2(0.0, 2.0);
      p.y += sin(uTime * 0.35 + aSeed * 30.0) * 0.35 + uProg * 0.15;
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_Position = projectionMatrix * mv;
      gl_PointSize = min(aScale * 34.0 * uPR / -mv.z, 18.0 * uPR);
      vColor = color;
      vTw = 0.35 + 0.65 * pow(0.5 + 0.5 * sin(uTime * (1.2 + aSeed * 2.5) + aSeed * 60.0), 3.0);
      vTw *= smoothstep(1.5, 4.0, -mv.z);
    }`,
  fragmentShader: `
    uniform float uGain; varying vec3 vColor; varying float vTw;
    void main(){
      float d = length(gl_PointCoord - 0.5);
      float a = smoothstep(0.5, 0.0, d);
      a = pow(a, 2.2);
      gl_FragColor = vec4(vColor * 2.4 * uGain, a * vTw);
    }`,
});
const dust = new THREE.Points(dustGeo, dustMat);
dust.frustumCulled = false;
scene.add(dust);

/* ------------------------------------------------------------------ */
/* camera keys                                                         */
/* ------------------------------------------------------------------ */
const CAM = [
  { p: V3(-0.2, 0.9, 8.2), t: V3(0.2, -0.8, 0) },
  { p: V3(0.0, 0.35, 6.6), t: V3(0.85, 0.05, 0) },
  { p: V3(0.3, 0.25, 6.4), t: V3(-1.2, 0.1, -1.2) },
  { p: V3(-0.6, 1.1, 8.6), t: V3(0.9, 0.3, -0.6) },
  { p: V3(0.0, 0.0, 9.5), t: V3(0.0, 0.0, -3) },
  { p: V3(-0.45, 9.8, 1.9), t: V3(-0.45, -2, 0.05) },
];

/* ------------------------------------------------------------------ */
/* post-processing                                                     */
/* ------------------------------------------------------------------ */
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.42, 0.55, 0.96);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const lensPass = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: 0.035 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime; uniform float uGrain; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    void main(){
      vec2 d = vUv - 0.5;
      float r2 = dot(d, d);
      vec2 off = d * r2 * 0.012;
      vec3 col = vec3(texture2D(tDiffuse, vUv + off).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - off).b);
      col *= mix(0.62, 1.0, smoothstep(0.62, 0.12, sqrt(r2)));
      col += (h(vUv * 1000.0 + fract(uTime) * 91.0) - 0.5) * uGrain;
      gl_FragColor = vec4(col, 1.0);
    }`,
});
composer.addPass(lensPass);

/* ------------------------------------------------------------------ */
/* frame update                                                        */
/* ------------------------------------------------------------------ */
const tmpP = new THREE.Vector3(), tmpR = new THREE.Vector3();
const camPos = new THREE.Vector3(), camTarget = new THREE.Vector3();
const mouse = { x: 0, y: 0, sx: 0, sy: 0 };

function segment(p) {
  const i = Math.min(4, Math.max(0, Math.floor(p)));
  return [i, clamp01(p - i)];
}

function applyActor(a, p, t) {
  const [i, f] = segment(p);
  const lf = clamp01((f - a.delay) / (1 - a.delay * 0.9));
  const e = easeInOut(lf);
  const A = a.keys[i], B = a.keys[i + 1];
  tmpP.lerpVectors(A.p, B.p, e).addScaledVector(a.arcs[i], Math.sin(Math.PI * lf));
  tmpR.lerpVectors(A.r, B.r, e);
  const s = lerp(A.s, B.s, e);
  const fl = lerp(A.f, B.f, e);
  tmpP.y += Math.sin(t * a.w + a.ph) * 0.09 * fl;
  tmpR.x += Math.sin(t * a.w * 0.7 + a.ph) * 0.06 * fl;
  tmpR.y += Math.sin(t * 0.25 + a.ph) * 0.5 * fl;
  a.obj.position.copy(tmpP);
  a.obj.rotation.set(tmpR.x, tmpR.y, tmpR.z);
  a.obj.scale.setScalar(Math.max(s, 0.0001));
  a.obj.visible = s > 0.002;
}

function keyScalar(keys, p) {
  const [i, f] = segment(p);
  return lerp(keys[i], keys[i + 1], easeInOut(f));
}

function renderAt(p, t) {
  for (const a of actors) applyActor(a, p, t);

  // notebook cover + inner light
  const ud = book.userData;
  ud.pivot.rotation.z = keyScalar(bookA.coverKeys, p);
  const glowK = keyScalar(bookA.glowKeys, p);
  const [seg, f] = segment(p);
  const burstBook = seg === 2 ? Math.sin(Math.PI * clamp01((f - 0.3) / 0.7)) : 0;
  const burstCup = seg === 0 ? Math.sin(Math.PI * clamp01(f / 0.7)) : 0;
  ud.pageTop.emissiveIntensity = glowK * 0.18 + burstBook * 0.5;
  ud.glow.material.opacity = Math.min(0.8, glowK * 0.35 + burstBook * 0.8);
  ud.glow.scale.setScalar(1.8 + burstBook * 3 + Math.sin(t * 1.3) * 0.2);

  const sink = cupSink(p);
  cup.visible = sink < 1;
  cup.position.y = CUP.y - sink * 2;
  const cupIdle = p < 1 ? (1 - clamp01(p)) * 0.35 : 0;
  cupGlow.material.opacity = Math.min(1, cupIdle + burstCup * 1.2);
  cupGlow.scale.setScalar(2.4 + burstCup * 5 + Math.sin(t * 1.1) * 0.15);

  const bookWorld = book.getWorldPosition(tmpP);
  magic.position.lerpVectors(V3(CUP.x, CUP.y + 1.5, CUP.z), bookWorld.add(V3(0, 0.8, 0)), clamp01(p - 1.5));
  magic.intensity = 4 + burstCup * 45 + burstBook * 40 + glowK * 8;

  // camera
  const e = easeInOut(f);
  camPos.lerpVectors(CAM[seg].p, CAM[seg + 1].p, e);
  camTarget.lerpVectors(CAM[seg].t, CAM[seg + 1].t, e);
  const aspect = window.innerWidth / window.innerHeight;
  if (aspect < 1) {
    const k = 1 + (1 - aspect) * 1.25;
    camPos.sub(camTarget).multiplyScalar(k).add(camTarget);
  }
  camera.position.copy(camPos);
  camera.position.x += mouse.sx * 0.35;
  camera.position.y += mouse.sy * 0.2;
  camera.lookAt(camTarget);

  scene.fog.density = lerp(0.034, 0.012, clamp01(p - 4));
  dustMat.uniforms.uTime.value = t;
  dustMat.uniforms.uProg.value = p;
  dustMat.uniforms.uGain.value = 1 + (burstCup + burstBook) * 1.6 - clamp01(p - 4) * 0.55;
  sky.material.uniforms.uTime.value = t;
  lensPass.uniforms.uTime.value = t;

  composer.render();
}

/* ------------------------------------------------------------------ */
/* scroll wiring (GSAP ScrollTrigger)                                  */
/* ------------------------------------------------------------------ */
const state = { target: 0, current: 0 };

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  camera.fov = w / h < 1 ? 42 : 35;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer.setSize(w, h);
  bloom.setSize(w, h);
}
window.addEventListener('resize', resize);
resize();

if (CAPTURE) {
  window.__renderAt = (p, t) => { renderAt(p, t); return true; };
  window.__ready = true;
} else {
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);

  // p = 0…5 : each chapter's sticky panel rests, then the next chapter
  // rising from the bottom of the viewport drives the transition.
  const chapters = gsap.utils.toArray('.chapter');
  const seg = new Array(chapters.length - 1).fill(0);
  chapters.slice(1).forEach((ch, i) => {
    ScrollTrigger.create({
      trigger: ch, start: 'top bottom', end: 'top top',
      onUpdate: (self) => { seg[i] = self.progress; state.target = seg.reduce((s, v) => s + v, 0); },
      onRefresh: (self) => { seg[i] = self.progress; state.target = seg.reduce((s, v) => s + v, 0); },
    });
  });

  // copy reveals
  gsap.utils.toArray('.chapter').forEach((ch) => {
    const items = ch.querySelectorAll('[data-reveal]');
    if (!items.length) return;
    gsap.fromTo(items, { y: 40, autoAlpha: 0.0, filter: 'blur(6px)' }, {
      y: 0, autoAlpha: 1, filter: 'blur(0px)', duration: 1.1, ease: 'power3.out', stagger: 0.08,
      scrollTrigger: { trigger: ch, start: 'top 75%', end: 'bottom 25%', toggleActions: 'play reverse play reverse' },
    });
  });

  // progress rail + chapter index
  const bar = document.querySelector('.rail__fill');
  const idx = document.querySelectorAll('.rail__dot');
  ScrollTrigger.create({
    start: 0, end: 'max',
    onUpdate: (self) => { if (bar) bar.style.transform = `scaleY(${self.progress})`; },
  });

  // gallery tiles parallax
  gsap.utils.toArray('.shot').forEach((el, i) => {
    gsap.fromTo(el, { yPercent: 12 + i * 4 }, {
      yPercent: -6, ease: 'none',
      scrollTrigger: { trigger: '#gallery', start: 'top bottom', end: 'bottom top', scrub: true },
    });
  });

  window.addEventListener('pointermove', (e) => {
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -((e.clientY / window.innerHeight) * 2 - 1);
  });

  const clock = new THREE.Clock();
  let first = true;
  renderer.setAnimationLoop(() => {
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    state.current += (state.target - state.current) * (1 - Math.exp(-dt * (REDUCED ? 20 : 3.2)));
    mouse.sx += (mouse.x - mouse.sx) * (1 - Math.exp(-dt * 2));
    mouse.sy += (mouse.y - mouse.sy) * (1 - Math.exp(-dt * 2));
    idx.forEach((d, i) => d.classList.toggle('is-on', Math.round(state.current) === i));
    renderAt(state.current, t);
    if (first) { first = false; document.documentElement.classList.add('is-loaded'); }
  });
}
