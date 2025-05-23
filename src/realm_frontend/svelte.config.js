import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
    // If your environment is not supported or you settled on a specific environment, switch out the adapter.
    // See https://kit.svelte.dev/docs/adapters for more information about adapters.
    adapter: adapter({
      pages: 'dist',
      assets: 'dist',
      fallback: 'index.html',
      precompress: false,
      strict: true,
    }),
    prerender: {
      // Instead of using enabled: false, let's use an empty entries array to disable prerendering
      entries: [],
      handleHttpError: ({ path, referrer, message }) => {
        console.warn(`Error during prerendering of ${path}: ${message}`);
        return; 
      }
    }
  },
};

export default config;
