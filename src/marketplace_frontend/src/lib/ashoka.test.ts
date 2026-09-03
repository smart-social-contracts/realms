import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { applyStreamEvent, applyStreamLine, emptyStream, parseSuggestions } from "./ashoka.ts";

describe("ashoka stream parser", () => {
  it("accumulates text events and ignores thinking", () => {
    const state = emptyStream();
    applyStreamEvent({ type: "status", text: "Thinking…" }, state);
    assert.equal(state.status, "Thinking…");
    applyStreamEvent({ type: "thinking", text: "hmm" }, state);
    applyStreamEvent({ type: "text", text: "Realms is a GOS." }, state);
    assert.equal(state.text, "Realms is a GOS.");
    assert.equal(state.status, "");
    assert.equal(state.thinking, "hmm");
  });

  it("parses SSE data lines", () => {
    const state = emptyStream();
    applyStreamLine('data: {"type":"text","text":"Hello"}', state);
    applyStreamLine("data: [DONE]", state);
    assert.equal(state.text, "Hello");
  });

  it("maps hostname to the Geister network", async () => {
    const { geisterNetwork } = await import("./ashoka.ts");
    assert.equal(geisterNetwork("demo", ""), "demo");
    assert.equal(geisterNetwork("", "staging.realmsgos.org"), "staging");
    assert.equal(geisterNetwork("", "localhost"), "test");
  });

  it("keeps up to five non-empty suggestion strings", () => {
    assert.deepEqual(
      parseSuggestions({ suggestions: [" What is a realm? ", "", 3, "Who is this for?"] }),
      ["What is a realm?", "Who is this for?"],
    );
    assert.deepEqual(parseSuggestions({ suggestions: null }), []);
  });
});
