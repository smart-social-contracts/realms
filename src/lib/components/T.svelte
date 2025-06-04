<script>
  import { _ } from 'svelte-i18n';
  import { browser } from '$app/environment';

  /**
   * Translation key path
   * @type {string}
   */
  export let key;

  /**
   * Values to interpolate into the translation
   * @type {Record<string, any>}
   */
  export let values = {};

  /**
   * Default text to show if translation is not found
   * @type {string}
   */
  export let default_text = '';
</script>

{#if browser && $_}
  {#if $_(key, { values, default: default_text }) !== key}
    {$_(key, { values, default: default_text })}
  {:else if default_text}
    {default_text}
  {:else}
    {key}
  {/if}
{:else}
  {default_text || key}
{/if} 