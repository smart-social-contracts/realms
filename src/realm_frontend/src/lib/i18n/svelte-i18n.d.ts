declare module 'svelte-i18n' {
  import type { Readable } from 'svelte/store';

  export function init(options: {
    fallbackLocale: string;
    initialLocale?: string;
    formats?: Record<string, Record<string, any>>;
    warnOnMissingMessages?: boolean;
  }): void;

  export function register(
    locale: string,
    loader: () => Promise<Record<string, any>>
  ): void;

  export function getLocaleFromNavigator(): string;

  export function addMessages(
    locale: string,
    messages: Record<string, any>
  ): void;
  
  export const isLoading: Readable<boolean>;

  export function locale(): Readable<string>;
  export function locale(newLocale: string): Promise<void>;

  export function _(...args: any[]): Readable<string>;
}
