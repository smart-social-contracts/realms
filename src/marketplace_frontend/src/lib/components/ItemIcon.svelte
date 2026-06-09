<script lang="ts">
  /**
   * Renders a listing's graphic. Extensions/codices declare their icon as a
   * Tabler icon name in their manifest (e.g. "gavel"); those render as the
   * real Tabler webfont glyph. Any other value (e.g. a legacy emoji) renders
   * as plain text. Size/colour are controlled by the parent container.
   */
  export let icon: string = '';
  export let kind: 'ext' | 'codex' | 'assistant' = 'ext';

  function defaultIconName(k: 'ext' | 'codex' | 'assistant'): string {
    if (k === 'codex') return 'file-code';
    if (k === 'assistant') return 'robot';
    return 'puzzle';
  }
  $: resolved = icon && icon.trim() ? icon.trim() : defaultIconName(kind);
  $: isName = /^[a-z][a-z0-9-]*$/.test(resolved);
</script>

{#if isName}
  <i class="ti ti-{resolved}" aria-hidden="true"></i>
{:else}
  {resolved}
{/if}
