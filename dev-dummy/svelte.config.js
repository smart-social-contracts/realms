import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'dist',
      assets: 'dist',
      fallback: 'index.html',
      precompress: false,
      strict: true,
    }),
    prerender: {
      entries: [],
      handleHttpError: ({ path, referrer, message }) => {
        console.warn(`Error during prerendering of ${path}: ${message}`);
        return; 
      }
    }
  },
};

export default config;
