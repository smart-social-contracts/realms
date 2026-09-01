export type Vec3 = [number, number, number];

type Edge = { a: number; b: number; w: number };

export type Stipple = {
  p: Vec3;
  phase: number;
  digit: boolean;
  scale: number;
  sky?: boolean;
};

export type CapitolGeom = {
  vertices: Vec3[];
  edges: Edge[];
  stipple: Stipple[];
};

export type Camera = {
  eye: Vec3;
  target: Vec3;
  fov: number;
};

type View = {
  eye: Vec3;
  x: Vec3;
  y: Vec3;
  z: Vec3;
  fov: number;
};

const MAIN = 1;
const MID = 0.7;
const FINE = 0.42;
const TAU = Math.PI * 2;
const GOLDEN = Math.PI * (3 - Math.sqrt(5));

function fract(n: number): number {
  return n - Math.floor(n);
}

function hash3(x: number, y: number, z: number): number {
  return fract(Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453);
}

function add(g: CapitolGeom, x: number, y: number, z: number): number {
  g.vertices.push([x, y, z]);
  return g.vertices.length - 1;
}

function join(g: CapitolGeom, a: number, b: number, w = MAIN) {
  g.edges.push({ a, b, w });
}

function polyline(g: CapitolGeom, ids: number[], closed = false, w = MAIN) {
  for (let i = 0; i < ids.length - 1; i++) join(g, ids[i], ids[i + 1], w);
  if (closed && ids.length > 2) join(g, ids[ids.length - 1], ids[0], w);
}

function rectY(g: CapitolGeom, x0: number, z0: number, x1: number, z1: number, y: number, w = MAIN) {
  const a = add(g, x0, y, z0);
  const b = add(g, x1, y, z0);
  const c = add(g, x1, y, z1);
  const d = add(g, x0, y, z1);
  polyline(g, [a, b, c, d], true, w);
  return [a, b, c, d];
}

function box(
  g: CapitolGeom,
  x0: number,
  y0: number,
  z0: number,
  x1: number,
  y1: number,
  z1: number,
  w = MAIN,
) {
  const bottom = rectY(g, x0, z0, x1, z1, y0, w);
  const top = rectY(g, x0, z0, x1, z1, y1, w);
  for (let i = 0; i < 4; i++) join(g, bottom[i], top[i], w);
}

function mark(
  g: CapitolGeom,
  x: number,
  y: number,
  z: number,
  scale: number,
  digitChance: number,
  phase = hash3(x, y, z),
  sky = false,
) {
  const jitter = (hash3(z, x, y) - 0.5) * (sky ? 0.07 : 0.04);
  g.stipple.push({
    p: [x + jitter, y, z + jitter * 0.6],
    phase,
    digit: hash3(y, z, x) < digitChance,
    scale: scale * (0.72 + hash3(x, y + 2, z) * 0.55),
    sky: sky || undefined,
  });
}

function column(
  g: CapitolGeom,
  cx: number,
  cz: number,
  y0: number,
  y1: number,
  r: number,
  sides = 8,
  w = MAIN,
) {
  const bot: number[] = [];
  const top: number[] = [];
  const cap: number[] = [];
  const base: number[] = [];
  for (let i = 0; i < sides; i++) {
    const a = (i / sides) * TAU + Math.PI / sides;
    const x = cx + Math.cos(a) * r;
    const z = cz + Math.sin(a) * r;
    bot.push(add(g, x, y0, z));
    top.push(add(g, x, y1, z));
    cap.push(add(g, cx + Math.cos(a) * r * 1.38, y1 + 0.12, cz + Math.sin(a) * r * 1.38));
    base.push(add(g, cx + Math.cos(a) * r * 1.42, y0, cz + Math.sin(a) * r * 1.42));
  }
  polyline(g, bot, true, w);
  polyline(g, top, true, w);
  polyline(g, cap, true, MID);
  polyline(g, base, true, FINE);
  for (let i = 0; i < sides; i++) join(g, bot[i], top[i], w);

  const n = 52;
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const a = t * TAU * 4.1 + cx * 0.4;
    const y = y0 + t * (y1 - y0);
    mark(
      g,
      cx + Math.cos(a) * r * 1.06,
      y,
      cz + Math.sin(a) * r * 1.06,
      1.12,
      0.32,
      fract(t * 0.35 + cx * 0.07),
    );
  }
  for (let ring = 0; ring < 8; ring++) {
    const y = y0 + ((ring + 0.5) / 8) * (y1 - y0);
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * TAU + ring * 0.2;
      mark(g, cx + Math.cos(a) * r * 0.7, y, cz + Math.sin(a) * r * 0.7, 0.82, 0.28, fract(ring * 0.1 + i * 0.04));
    }
  }
}

function windowGrid(
  g: CapitolGeom,
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  z: number,
  cols: number,
  rows: number,
) {
  const padX = (x1 - x0) * 0.1;
  const padY = (y1 - y0) * 0.14;
  const innerW = x1 - x0 - padX * 2;
  const innerH = y1 - y0 - padY * 2;
  const cellW = innerW / cols;
  const cellH = innerH / rows;
  const ww = cellW * 0.5;
  const hh = cellH * 0.62;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const cx = x0 + padX + (col + 0.5) * cellW;
      const cy = y0 + padY + (row + 0.5) * cellH;
      const a = add(g, cx - ww / 2, cy - hh / 2, z);
      const b = add(g, cx + ww / 2, cy - hh / 2, z);
      const c = add(g, cx + ww / 2, cy + hh / 2, z);
      const d = add(g, cx - ww / 2, cy + hh / 2, z);
      polyline(g, [a, b, c, d], true, FINE);
      join(g, add(g, cx, cy - hh / 2, z), add(g, cx, cy + hh / 2, z), FINE);
      join(g, add(g, cx - ww / 2, cy, z), add(g, cx + ww / 2, cy, z), FINE);
    }
  }
}

function hemisphere(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  r: number,
  meridians: number,
  parallels: number,
  w = MAIN,
) {
  const rows: number[][] = [];
  for (let p = 0; p <= parallels; p++) {
    const phi = (p / parallels) * (Math.PI / 2);
    const rr = r * Math.sin(phi);
    const y = cy + r * Math.cos(phi);
    const ring: number[] = [];
    if (p === 0) {
      ring.push(add(g, cx, y, cz));
    } else {
      for (let m = 0; m < meridians; m++) {
        const th = (m / meridians) * TAU;
        ring.push(add(g, cx + rr * Math.cos(th), y, cz + rr * Math.sin(th)));
      }
    }
    rows.push(ring);
  }
  for (let p = 1; p < rows.length; p++) polyline(g, rows[p], true, w);
  for (let m = 0; m < meridians; m++) {
    const line = [rows[0][0]];
    for (let p = 1; p < rows.length; p++) line.push(rows[p][m]);
    polyline(g, line, false, w);
  }
}

function colonnade(
  g: CapitolGeom,
  x0: number,
  x1: number,
  cz: number,
  y0: number,
  y1: number,
  count: number,
  r: number,
) {
  for (let i = 0; i < count; i++) {
    const t = count === 1 ? 0.5 : i / (count - 1);
    column(g, x0 + (x1 - x0) * t, cz, y0, y1, r);
  }
}

function pediment(g: CapitolGeom, x0: number, x1: number, y: number, z: number, rise: number) {
  const left = add(g, x0, y, z);
  const right = add(g, x1, y, z);
  const peak = add(g, (x0 + x1) / 2, y + rise, z);
  polyline(g, [left, peak, right], false, MAIN);
  join(g, left, right, MID);
  const zBack = z - 1.2;
  const leftB = add(g, x0, y, zBack);
  const rightB = add(g, x1, y, zBack);
  const peakB = add(g, (x0 + x1) / 2, y + rise, zBack);
  polyline(g, [leftB, peakB, rightB], false, MID);
  join(g, left, leftB, MID);
  join(g, right, rightB, MID);
  join(g, peak, peakB, MAIN);

  for (let i = 0; i < 70; i++) {
    const u = hash3(i, 2.1, 0.4);
    const v = hash3(i, 8.2, 1.1);
    const x = x0 + (x1 - x0) * u;
    const top = y + rise * (1 - Math.abs(u * 2 - 1));
    const yy = y + (top - y) * (0.12 + v * 0.82);
    if (yy > top - 0.05) continue;
    mark(g, x, yy, z + 0.04, 0.88, 0.2, u * 0.6);
  }
}

function ringPrism(
  g: CapitolGeom,
  cx: number,
  cz: number,
  y0: number,
  y1: number,
  r: number,
  sides: number,
  w = MAIN,
) {
  const bot: number[] = [];
  const top: number[] = [];
  for (let i = 0; i < sides; i++) {
    const a = (i / sides) * TAU;
    bot.push(add(g, cx + Math.cos(a) * r, y0, cz + Math.sin(a) * r));
    top.push(add(g, cx + Math.cos(a) * r, y1, cz + Math.sin(a) * r));
  }
  polyline(g, bot, true, w);
  polyline(g, top, true, w);
  for (let i = 0; i < sides; i++) join(g, bot[i], top[i], w);
}

function plazaArcs(g: CapitolGeom, y: number) {
  for (const r of [11.2, 14.4, 17.8, 21.2]) {
    const pts: number[] = [];
    const n = 18;
    for (let i = 0; i <= n; i++) {
      const a = -0.78 + (1.56 * i) / n;
      pts.push(add(g, Math.sin(a) * r, y, 6.1 + Math.cos(a) * r * 0.52));
    }
    polyline(g, pts, false, FINE);
    for (let i = 0; i < pts.length; i += 2) {
      const v = g.vertices[pts[i]];
      mark(g, v[0], y + 0.02, v[2], 0.55, 0.12, i * 0.04);
    }
  }
}

function fibonacciHemisphere(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  r: number,
  n: number,
  scale: number,
  digitChance: number,
) {
  for (let i = 0; i < n; i++) {
    const yN = 1 - i / Math.max(1, n - 1);
    const rad = Math.sqrt(Math.max(0, 1 - yN * yN));
    const theta = GOLDEN * i;
    const x = cx + Math.cos(theta) * rad * r;
    const y = cy + yN * r;
    const z = cz + Math.sin(theta) * rad * r;
    mark(g, x, y, z, scale, digitChance, fract(i * 0.045 + yN * 0.3));
  }
}

function facadeStipple(
  g: CapitolGeom,
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  z: number,
  nx: number,
  ny: number,
  scale: number,
  digitChance: number,
) {
  for (let iy = 0; iy < ny; iy++) {
    for (let ix = 0; ix < nx; ix++) {
      const u = (ix + 0.35 + hash3(ix, iy, z) * 0.4) / nx;
      const v = (iy + 0.3 + hash3(iy, ix, 2) * 0.45) / ny;
      mark(g, x0 + (x1 - x0) * u, y0 + (y1 - y0) * v, z, scale, digitChance, fract(u * 0.5 + v * 0.2));
    }
  }
}

function beadEdges(g: CapitolGeom) {
  for (const e of g.edges) {
    const A = g.vertices[e.a];
    const B = g.vertices[e.b];
    const dx = B[0] - A[0];
    const dy = B[1] - A[1];
    const dz = B[2] - A[2];
    const len = Math.hypot(dx, dy, dz);
    if (len < 0.06) continue;
    const spacing = e.w > 0.8 ? 0.4 : e.w > 0.55 ? 0.5 : 0.66;
    const n = Math.max(2, Math.round(len / spacing));
    const scale = 0.78 + e.w * 0.42;
    const digitChance = e.w > 0.8 ? 0.13 : 0.08;
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      mark(g, A[0] + dx * t, A[1] + dy * t, A[2] + dz * t, scale, digitChance, fract(t * 0.37 + e.a * 0.013));
    }
  }
}

function fibonacciSphere(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  r: number,
  n: number,
  scale: number,
  digitChance: number,
  sky = false,
  flattenY = 1,
) {
  for (let i = 0; i < n; i++) {
    const yN = 1 - ((i + 0.5) / n) * 2;
    const rad = Math.sqrt(Math.max(0, 1 - yN * yN));
    const theta = GOLDEN * i;
    mark(
      g,
      cx + Math.cos(theta) * rad * r,
      cy + yN * r * flattenY,
      cz + Math.sin(theta) * rad * r,
      scale,
      digitChance,
      fract(i * 0.031 + r * 0.07),
      sky,
    );
  }
}

function latitudeBand(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  r: number,
  yN: number,
  n: number,
  scale: number,
  flattenY = 1,
) {
  const rad = Math.sqrt(Math.max(0, 1 - yN * yN)) * r;
  const y = cy + yN * r * flattenY;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU;
    mark(g, cx + Math.cos(a) * rad, y, cz + Math.sin(a) * rad, scale, 0.08, i / n, true);
  }
}

function planetRing(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  radius: number,
  n: number,
  scale: number,
  tilt = 0.72,
  yaw = 0,
) {
  // Start face-on to +Z, then tilt toward horizontal so the disc reads as a wide oval.
  const cosT = Math.cos(tilt);
  const sinT = Math.sin(tilt);
  const cosY = Math.cos(yaw);
  const sinY = Math.sin(yaw);
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU;
    const lx = Math.cos(a) * radius;
    const ly = Math.sin(a) * radius;
    const y1 = ly * cosT;
    const z1 = ly * sinT;
    const x = lx * cosY + z1 * sinY;
    const z = -lx * sinY + z1 * cosY;
    mark(g, cx + x, cy + y1, cz + z, scale, 0.08, i / n, true);
  }
}

function satellite(
  g: CapitolGeom,
  cx: number,
  cy: number,
  cz: number,
  orbit: number,
  angle: number,
  elev: number,
  r: number,
  n: number,
) {
  const x = cx + Math.cos(angle) * orbit;
  const y = cy + Math.sin(elev) * orbit * 0.55;
  const z = cz + Math.sin(angle) * orbit * 0.72;
  fibonacciSphere(g, x, y, z, r, n, 0.92, 0.12, true);
}

function addPlanets(g: CapitolGeom) {
  // Mars — small, polar cap, two tiny moons.
  fibonacciSphere(g, -10.15, 9.35, -5.35, 0.38, 90, 0.98, 0.1, true);
  latitudeBand(g, -10.15, 9.35, -5.35, 0.38, 0.82, 18, 0.7);
  satellite(g, -10.15, 9.35, -5.35, 0.78, 0.4, 0.55, 0.09, 14);
  satellite(g, -10.15, 9.35, -5.35, 1.05, 2.7, -0.4, 0.07, 10);

  // Jupiter — largest, equatorial bands, Great Red Spot, Galilean moons.
  fibonacciSphere(g, -7.55, 12.5, -8.35, 1.32, 340, 1.08, 0.08, true);
  for (const yN of [-0.58, -0.32, -0.1, 0.12, 0.34, 0.56]) {
    latitudeBand(g, -7.55, 12.5, -8.35, 1.32, yN, 56, 0.72);
  }
  for (let i = 0; i < 28; i++) {
    const a = (i / 28) * TAU;
    mark(
      g,
      -7.55 + 1.18 + Math.cos(a) * 0.2,
      12.5 + 0.12 + Math.sin(a) * 0.1,
      -8.35 + Math.sin(a) * 0.16,
      0.85,
      0.12,
      i / 28,
      true,
    );
  }
  satellite(g, -7.55, 12.5, -8.35, 2.05, 0.15, 0.45, 0.2, 28);
  satellite(g, -7.55, 12.5, -8.35, 2.35, 1.4, -0.2, 0.16, 22);
  satellite(g, -7.55, 12.5, -8.35, 2.65, 2.6, 0.35, 0.18, 24);
  satellite(g, -7.55, 12.5, -8.35, 2.95, 4.1, -0.5, 0.14, 18);

  // Saturn — slightly oblate, wide rings, Titan.
  fibonacciSphere(g, 11.85, 11.5, -4.35, 1.08, 240, 1.04, 0.08, true, 0.86);
  planetRing(g, 11.85, 11.5, -4.35, 2.12, 150, 0.7, 0.68, 0.58);
  planetRing(g, 11.85, 11.5, -4.35, 1.92, 130, 0.64, 0.68, 0.58);
  planetRing(g, 11.85, 11.5, -4.35, 1.68, 110, 0.58, 0.68, 0.58);
  satellite(g, 11.85, 11.5, -4.35, 2.85, 0.45, 0.55, 0.22, 36);

  // Uranus — ice giant, rings nearly on end (tipped axis).
  fibonacciSphere(g, 8.35, 13.05, -8.7, 0.66, 150, 1.0, 0.1, true);
  planetRing(g, 8.35, 13.05, -8.7, 1.05, 90, 0.52, 1.42, 0.15);
  planetRing(g, 8.35, 13.05, -8.7, 0.9, 72, 0.48, 1.42, 0.15);
  satellite(g, 8.35, 13.05, -8.7, 1.45, 1.1, 0.7, 0.12, 18);

  // Neptune — similar to Uranus, fainter ring, larger moon.
  fibonacciSphere(g, 13.65, 8.65, -0.95, 0.62, 140, 1.0, 0.1, true);
  planetRing(g, 13.65, 8.65, -0.95, 0.92, 64, 0.5, 0.85, 0.35);
  satellite(g, 13.65, 8.65, -0.95, 1.55, 0.2, 0.4, 0.18, 26);
}

export function buildCapitol(): CapitolGeom {
  const g: CapitolGeom = { vertices: [], edges: [], stipple: [] };

  const pod = 2.05;
  plazaArcs(g, 0);

  const stepCount = 10;
  for (let i = 0; i < stepCount; i++) {
    const y = (pod * i) / stepCount;
    const inset = i * 0.36;
    const half = 12.7 - i * 0.07;
    rectY(g, -half, 4.65, half, 9.45 - inset, y, i === stepCount - 1 ? MAIN : MID);
    const dots = 18 - Math.floor(i * 0.4);
    for (let k = 0; k < dots; k++) {
      const u = (k + 0.5) / dots;
      mark(g, -half + 2 * half * u, y + 0.04, 9.45 - inset - 0.08, 0.62, 0.16, u * 0.4);
    }
  }

  box(g, -13.5, 0, -4.5, 13.5, pod, 4.7, MID);

  const wingH = pod + 4.4;
  box(g, -13.25, pod, -3.75, -4.32, wingH, 3.88);
  box(g, 4.32, pod, -3.75, 13.25, wingH, 3.88);
  windowGrid(g, -12.55, -5.05, pod + 0.55, wingH - 0.38, 3.9, 7, 3);
  windowGrid(g, 5.05, 12.55, pod + 0.55, wingH - 0.38, 3.9, 7, 3);
  facadeStipple(g, -12.6, -5.0, pod + 0.45, wingH - 0.25, 3.92, 28, 14, 0.82, 0.18);
  facadeStipple(g, 5.0, 12.6, pod + 0.55, wingH - 0.25, 3.92, 28, 14, 0.82, 0.18);

  const centerH = pod + 5.4;
  box(g, -4.38, pod, -4.35, 4.38, centerH, 4.18);
  box(g, -4.2, centerH - 0.18, -4.1, 4.2, centerH, 4.05, MID);

  const colY0 = pod + 0.12;
  const colY1 = pod + 4.58;
  colonnade(g, -3.6, 3.55, 4.88, colY0, colY1, 8, 0.23);
  colonnade(g, -12.25, -5.1, 4.18, colY0, pod + 3.58, 7, 0.155);
  colonnade(g, 5.1, 12.25, 4.18, colY0, pod + 3.58, 7, 0.155);

  box(g, -4.2, colY1, 3.5, 4.2, colY1 + 0.58, 5.08, MID);
  pediment(g, -4.08, 4.08, colY1 + 0.58, 5.05, 1.92);

  box(g, -13.0, wingH, -3.45, -4.5, wingH + 0.46, 3.58, MID);
  box(g, 4.5, wingH, -3.45, 13.0, wingH + 0.46, 3.58, MID);

  const domeX = 0;
  const domeZ = -0.12;
  const drumY0 = centerH;
  const drumY1 = centerH + 1.72;
  const drumR = 3.48;
  ringPrism(g, domeX, domeZ, drumY0, drumY1, drumR, 16, MAIN);
  ringPrism(g, domeX, domeZ, drumY0, drumY1, drumR + 0.58, 16, MID);
  ringPrism(g, domeX, domeZ, drumY1 - 0.18, drumY1, drumR + 0.72, 16, FINE);

  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * TAU;
    column(
      g,
      domeX + Math.cos(a) * (drumR + 0.3),
      domeZ + Math.sin(a) * (drumR + 0.3),
      drumY0,
      drumY1 - 0.08,
      0.125,
      6,
      MID,
    );
  }

  const domeR = 3.42;
  hemisphere(g, domeX, drumY1, domeZ, domeR, 22, 8, FINE);
  fibonacciHemisphere(g, domeX, drumY1, domeZ, domeR * 1.02, 720, 1.32, 0.15);
  fibonacciHemisphere(g, domeX, drumY1, domeZ, domeR * 0.78, 400, 1.18, 0.17);
  fibonacciHemisphere(g, domeX, drumY1, domeZ, domeR * 0.52, 220, 1.05, 0.2);
  fibonacciHemisphere(g, domeX, drumY1, domeZ, domeR * 0.28, 100, 0.95, 0.22);

  const lanternY0 = drumY1 + domeR;
  ringPrism(g, domeX, domeZ, lanternY0 - 0.12, lanternY0 + 1.08, 0.64, 8, MID);
  hemisphere(g, domeX, lanternY0 + 1.08, domeZ, 0.66, 10, 4, FINE);
  fibonacciHemisphere(g, domeX, lanternY0 + 1.08, domeZ, 0.68, 70, 0.9, 0.22);
  const spireBase = add(g, domeX, lanternY0 + 1.58, domeZ);
  const spireTop = add(g, domeX, lanternY0 + 2.62, domeZ);
  join(g, spireBase, spireTop, MAIN);
  mark(g, domeX, lanternY0 + 2.55, domeZ, 1.15, 0.35, 0.08);
  beadEdges(g);
  addPlanets(g);
  return g;
}

function sub(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}

function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function hypot3(v: Vec3): number {
  return Math.hypot(v[0], v[1], v[2]);
}

function norm(v: Vec3): Vec3 {
  const l = hypot3(v) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
}

export function cameraAt(t: number): Camera {
  const yaw = -0.4 + 0.38 * Math.sin(t * 0.13);
  const elev = 0.29 + 0.04 * Math.sin(t * 0.085 + 0.5);
  const dist = 26.4 + 1.2 * Math.sin(t * 0.075);
  const cosE = Math.cos(elev);
  const eye: Vec3 = [
    dist * cosE * Math.sin(yaw),
    4.15 + dist * Math.sin(elev),
    dist * cosE * Math.cos(yaw),
  ];
  return { eye, target: [0, 6.2, 0.45], fov: 0.6 };
}

export function makeView(cam: Camera): View {
  const z = norm(sub(cam.eye, cam.target));
  let x = cross([0, 1, 0], z);
  if (hypot3(x) < 1e-5) x = [1, 0, 0];
  else x = norm(x);
  const y = cross(z, x);
  return { eye: cam.eye, x, y, z, fov: cam.fov };
}

export function project(
  p: Vec3,
  view: View,
  width: number,
  height: number,
): { x: number; y: number; depth: number } | null {
  const d = sub(p, view.eye);
  const vx = dot(d, view.x);
  const vy = dot(d, view.y);
  const depth = -dot(d, view.z);
  if (depth < 0.08) return null;
  const f = 1 / Math.tan(view.fov / 2);
  const aspect = width / height;
  const ndcX = (vx * f) / aspect / depth;
  const ndcY = (vy * f) / depth;
  return {
    x: (ndcX * 0.5 + 0.5) * width,
    y: (-ndcY * 0.5 + 0.5) * height,
    depth,
  };
}

function depthFade(depth: number): number {
  const t = (33 - depth) / 18;
  return Math.max(0, Math.min(1, t));
}

export function createCapitolScene(canvas: HTMLCanvasElement): { destroy: () => void } {
  const geom = buildCapitol();
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx) return { destroy() {} };

  let raf = 0;
  let elapsed = 0;
  let last = 0;
  let running = true;
  let cssW = 0;
  let cssH = 0;
  let dprUsed = 0;
  const reduced =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  const host = canvas.parentElement || canvas;
  const ro = new ResizeObserver(() => paint(elapsed));
  ro.observe(host);

  const io = new IntersectionObserver((entries) => {
    const on = entries.some((e) => e.isIntersecting);
    if (on) {
      if (reduced) paint(0);
      else start();
    } else stopLoop();
  });
  io.observe(host);

  function size() {
    const w = Math.max(1, host.clientWidth);
    const h = Math.max(1, host.clientHeight);
    const dpr = Math.min(typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1, 2);
    if (w !== cssW || h !== cssH || dpr !== dprUsed) {
      cssW = w;
      cssH = h;
      dprUsed = dpr;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    return { w, h };
  }

  function paint(t: number) {
    const { w, h } = size();
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);

    const view = makeView(cameraAt(t));

    type Drawn = { x: number; y: number; depth: number; r: number; alpha: number; digit: boolean; phase: number };
    const dots: Drawn[] = [];
    for (const s of geom.stipple) {
      const p = project(s.p, view, w, h);
      if (!p) continue;
      if (p.x < -16 || p.y < -16 || p.x > w + 16 || p.y > h + 16) continue;
      const fade = s.sky ? Math.max(0.55, depthFade(p.depth)) : depthFade(p.depth);
      const breathe = reduced ? 1 : 0.78 + 0.22 * Math.sin(t * 0.55 + s.phase * TAU);
      const r = Math.max(0.85, Math.min(5.4, s.scale * (40 / p.depth) * (0.9 + 0.4 * fade)));
      const alpha = ((s.sky ? 0.4 : 0.34) + 0.52 * fade) * breathe;
      dots.push({ x: p.x, y: p.y, depth: p.depth, r, alpha, digit: s.digit, phase: s.phase });
    }
    dots.sort((a, b) => b.depth - a.depth);

    const buckets: Drawn[][] = [[], [], [], [], [], [], [], []];
    const glyphs: Drawn[] = [];
    for (const d of dots) {
      if (d.digit) glyphs.push(d);
      else buckets[Math.min(7, Math.floor(d.alpha * 8))].push(d);
    }

    for (let b = 0; b < buckets.length; b++) {
      const list = buckets[b];
      if (!list.length) continue;
      ctx.fillStyle = `rgba(17, 17, 17, ${(0.28 + b / 8 * 0.62)})`;
      ctx.beginPath();
      for (const d of list) {
        ctx.moveTo(d.x + d.r, d.y);
        ctx.arc(d.x, d.y, d.r, 0, TAU);
      }
      ctx.fill();
    }

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (const d of glyphs) {
      const tick = Math.floor(t * 0.48 + d.phase * 13);
      ctx.font = `${Math.max(7, Math.min(13, d.r * 2.6))}px "SF Mono", ui-monospace, monospace`;
      ctx.fillStyle = `rgba(23, 23, 23, ${d.alpha * 1.05})`;
      ctx.fillText(tick % 2 === 0 ? '0' : '1', d.x, d.y);
    }
  }

  function frame(now: number) {
    if (!running) return;
    if (last) elapsed += (now - last) / 1000;
    last = now;
    paint(reduced ? 0 : elapsed);
    if (!reduced) raf = requestAnimationFrame(frame);
  }

  function start() {
    if (running && raf) return;
    running = true;
    last = 0;
    raf = requestAnimationFrame(frame);
  }

  function stopLoop() {
    running = false;
    cancelAnimationFrame(raf);
    raf = 0;
  }

  function onVis() {
    if (document.hidden) stopLoop();
    else start();
  }

  document.addEventListener('visibilitychange', onVis);
  paint(0);
  if (!reduced) start();

  return {
    destroy() {
      stopLoop();
      ro.disconnect();
      io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
    },
  };
}
