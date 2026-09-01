<script>
  import { onMount } from "svelte";
  import { createCapitolScene } from "../capitol-scene";

  let canvas;

  onMount(() => {
    if (!canvas) return;
    const scene = createCapitolScene(canvas);
    return () => scene.destroy();
  });
</script>

<canvas bind:this={canvas} aria-hidden="true"></canvas>

<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    background: #ffffff;
  }
</style>
