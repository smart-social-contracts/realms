import { derived } from 'svelte/store';
import { _, isLoading } from 'svelte-i18n';

/**
 * A safe translation store that shows a simple spinner instead of raw translation keys
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
      
      // If loading or we got back the raw key (no translation), show spinner
      if ($isLoading || (result === key && !options?.default)) {
        return `<span class="inline-flex items-center">
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </span>`;
      }
      
      return result;
    };
  }
);
