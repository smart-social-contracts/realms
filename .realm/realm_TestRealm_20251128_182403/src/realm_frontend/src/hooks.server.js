import { locale } from 'svelte-i18n';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
  // Get locale from cookie or default to 'en'
  const lang = event.cookies.get('locale') || 'en';
  
  // Set default locale
  locale.set(lang);
  
  // Replace %lang% in app.html with actual language
  const response = await resolve(event, {
    transformPageChunk: ({ html }) => html.replace('%lang%', lang)
  });
  
  return response;
} 