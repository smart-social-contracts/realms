import { writable } from 'svelte/store';

export const page = writable({
  url: { pathname: '/' },
  params: {},
  route: { id: null }
});
