<script lang="ts">
  // Small accessible help affordance: a question-mark icon that reveals an
  // explanatory bubble on hover/focus (pointer) and on tap (touch).
  export let text: string;
  export let label = 'More information';

  let open = false;

  function toggle(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    open = !open;
  }
</script>

<span
  class="infotip"
  class:open
  on:mouseenter={() => (open = true)}
  on:mouseleave={() => (open = false)}
>
  <button
    type="button"
    class="trigger"
    aria-label={label}
    aria-expanded={open}
    on:click={toggle}
    on:focus={() => (open = true)}
    on:blur={() => (open = false)}
  >
    <i class="ti ti-info-circle" aria-hidden="true"></i>
  </button>
  <span class="bubble" role="tooltip">{text}</span>
</span>

<style>
  .infotip {
    position: relative;
    display: inline-flex;
    align-items: center;
  }
  .trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    background: none;
    color: var(--text-faint);
    cursor: pointer;
    line-height: 1;
  }
  .trigger:hover { color: var(--text); }
  .trigger .ti { font-size: 1rem; }
  .bubble {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    width: max-content;
    max-width: 240px;
    padding: 0.5rem 0.65rem;
    border-radius: 0.5rem;
    background: var(--text);
    color: var(--surface);
    font-size: 0.75rem;
    line-height: 1.4;
    font-weight: 400;
    text-align: left;
    white-space: normal;
    box-shadow: 0 6px 20px -8px rgba(0, 0, 0, 0.4);
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.12s ease;
    z-index: 50;
  }
  .bubble::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-top-color: var(--text);
  }
  .infotip.open .bubble {
    opacity: 1;
    visibility: visible;
  }
</style>
