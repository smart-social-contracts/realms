declare module 'svelte-i18n' {
  import type { Readable, Writable } from 'svelte/store';

  export function init(options: {
    fallbackLocale: string;
    initialLocale?: string | null;
    formats?: Record<string, Record<string, any>>;
    warnOnMissingMessages?: boolean;
  }): void | Promise<void>;

  export function register(
    locale: string,
    loader: () => Promise<Record<string, any>>
  ): void;

  export function getLocaleFromNavigator(): string | null;

  export function addMessages(
    locale: string,
    messages: Record<string, any>
  ): void;

  type MessageFormatter = (
    id: string | { id: string; default?: string; values?: Record<string, unknown> },
    options?: Record<string, unknown>
  ) => string;

  export const isLoading: Writable<boolean>;

  /** Current locale store; use `.set()` to change locale. */
  export const locale: Writable<string | null | undefined>;

  /** Translation formatter store; subscribe in templates via `$_()`. */
  export const _: Readable<MessageFormatter>;
}
