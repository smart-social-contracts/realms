import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildCapitol, cameraAt, makeView, project } from "./capitol-scene.ts";

describe("capitol wireframe", () => {
  it("builds a wide civic mass with a stippled dome and mixed digits", () => {
    const g = buildCapitol();
    assert.ok(g.vertices.length > 300);
    assert.ok(g.edges.length > 300);
    assert.ok(g.stipple.length > 4000);

    for (const e of g.edges) {
      assert.ok(e.a >= 0 && e.a < g.vertices.length);
      assert.ok(e.b >= 0 && e.b < g.vertices.length);
      assert.ok(e.w > 0 && e.w <= 1);
    }

    const digits = g.stipple.filter((s) => s.digit).length;
    const dots = g.stipple.length - digits;
    assert.ok(dots > digits * 2, "dots should dominate; digits are the minority material");
    assert.ok(digits > 80, "digits should still be visible");

    let minX = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const [x, y] of g.vertices) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
    assert.ok(maxX - minX > 20, "building should read as a wide capitol");
    assert.ok(maxY > 12, "dome / lantern should rise above the wings");

    const skyMarks = g.stipple.filter((s) => s.sky);
    assert.ok(skyMarks.length > 400, "sky should hold five stippled planets");
    const skyXs = skyMarks.map((s) => s.p[0]);
    assert.ok(Math.max(...skyXs) - Math.min(...skyXs) > 16, "planets should sit in the left and right sky");

    const jupiter = skyMarks.filter((s) => Math.hypot(s.p[0] + 7.55, s.p[1] - 12.5, s.p[2] + 8.35) < 1.4).length;
    const saturnRing = skyMarks.filter((s) => {
      const d = Math.hypot(s.p[0] - 11.85, s.p[1] - 11.5, s.p[2] + 4.35);
      return d > 1.5 && d < 2.25;
    }).length;
    assert.ok(jupiter > 250, "Jupiter should be the largest body");
    assert.ok(saturnRing > 200, "Saturn should keep a wide ring");

    const a0 = makeView(cameraAt(0));
    let planetsOnScreen = 0;
    for (const s of skyMarks) {
      const p = project(s.p, a0, 1440, 900);
      if (p && p.x > 0 && p.x < 1440 && p.y > 0 && p.y < 900) planetsOnScreen += 1;
    }
    assert.ok(planetsOnScreen > 200, "planet dots should land in the hero frame");
  });

  it("projects the mass into the frame and moves the camera over time", () => {
    const g = buildCapitol();
    const a = makeView(cameraAt(0));
    const b = makeView(cameraAt(8));
    assert.notEqual(a.eye[0].toFixed(3), b.eye[0].toFixed(3));
    assert.notEqual(a.eye[2].toFixed(3), b.eye[2].toFixed(3));

    const mid = project([0, 6.2, 0.45], a, 1280, 800);
    assert.ok(mid);
    assert.ok(Math.abs(mid.x - 640) < 80);
    assert.ok(Math.abs(mid.y - 400) < 140);

    let onScreen = 0;
    for (const v of g.vertices) {
      const p = project(v, a, 1280, 800);
      if (p && p.x > 0 && p.x < 1280 && p.y > 0 && p.y < 800) onScreen += 1;
    }
    assert.ok(onScreen > g.vertices.length * 0.45);
  });
});
