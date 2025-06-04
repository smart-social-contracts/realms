import { locale } from 'svelte-i18n';
import { browser } from '$app/environment';

// Subscribe to locale changes and update cookie
locale.subscribe((value) => {
  if (browser && value) {
    // Save locale preference in cookie (expires in 1 year)
    document.cookie = `locale=${value};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Strict`;
    
    // Update HTML lang attribute
    document.documentElement.lang = value;
  }
}); 