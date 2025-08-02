<script>
  import LoadingSpinner from './LoadingSpinner.svelte';
  import { safeTranslate, isTranslationLoading } from '$lib/i18n/safe-translate.js';
  
  export let key = '';
  export let options = {};
  export let spinnerSize = 'sm';
  export let spinnerColor = 'gray';
  
  $: translatedText = $safeTranslate(key, options);
  $: isLoading = isTranslationLoading(translatedText);
</script>

{#if isLoading}
  <LoadingSpinner size={spinnerSize} color={spinnerColor} />
{:else}
  {translatedText}
{/if}
