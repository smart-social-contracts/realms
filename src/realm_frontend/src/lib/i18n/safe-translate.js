import { derived } from 'svelte/store';
import { _, isLoading } from 'svelte-i18n';

/**
 * A safe translation store that shows "•••" instead of raw translation keys
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
      
      // If loading or we got back the raw key (no translation), show dots
      if ($isLoading || (result === key && !options?.default)) {
        return '•••';
      }
      
      return result;
    };
  }
);
