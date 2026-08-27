import { locale } from 'svelte-i18n';

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
  // Host chrome has no language switcher. SSR starts at English; the client
  // applies user override → realm primary → en after realm + settings load.
  const lang = 'en';
  
  // Set default locale
  locale.set(lang);
  
  // Replace %lang% in app.html with actual language
  const response = await resolve(event, {
    transformPageChunk: ({ html }) => html.replace('%lang%', lang)
  });
  
  return response;
} 