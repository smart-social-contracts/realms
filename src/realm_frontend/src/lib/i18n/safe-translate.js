import { derived } from 'svelte/store';
import { _, isLoading } from 'svelte-i18n';

/**
 * A safe translation store that indicates loading state instead of showing raw translation keys
 * when translations are loading or not available.
 * 
 * Usage in components:
 * import { safeTranslate } from '$lib/i18n/safe-translate.js';
 * $: title = $safeTranslate('extensions.justice_litigation.title');
 * Then use: {title}
 */
export const safeTranslate = derived(
  [_, isLoading],
  ([$translate, $isLoading]) => {
    // Return a function that can be called with translation keys
    return (key, options = {}) => {
      const result = $translate(key, options);
      
      // If loading or we got back the raw key (no translation), return special loading indicator
      if ($isLoading || (result === key && !options?.default)) {
        return '__LOADING__';
      }
      
      return result;
    };
  }
);

/**
 * Check if a translation result indicates loading state
 */
export function isTranslationLoading(value) {
  return value === '__LOADING__';
}
