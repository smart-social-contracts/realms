<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { isAuthenticated } from '$lib/auth';
  import { marketplaceClient } from '$lib/marketplace-client';

  /** Item kind: "ext" | "codex" */
  export let kind: 'ext' | 'codex';
  export let itemId: string;
  /** Initial like state from the server. */
  export let liked: boolean = false;
  /** Initial like count from the server. */
  export let count: number = 0;

  let busy = false;
  let optimisticLiked = liked;
  let optimisticCount = count;

  $: optimisticLiked = liked;
  $: optimisticCount = count;

  const dispatch = createEventDispatcher<{ change: { liked: boolean; count: number } }>();

  async function toggle(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    busy = true;

    const wasLiked = optimisticLiked;
    optimisticLiked = !wasLiked;
    optimisticCount = Math.max(0, optimisticCount + (wasLiked ? -1 : 1));

    try {
      if (wasLiked) {
        await marketplaceClient.unlikeItem(kind, itemId);
      } else {
        await marketplaceClient.likeItem(kind, itemId);
      }
      dispatch('change', { liked: optimisticLiked, count: optimisticCount });
    } catch (err: any) {
      // Roll back on error.
      optimisticLiked = wasLiked;
      optimisticCount = Math.max(0, optimisticCount + (wasLiked ? 1 : -1));
      console.error('like toggle failed:', err);
      alert(`Could not ${wasLiked ? 'unlike' : 'like'}: ${err?.message ?? err}`);
    } finally {
      busy = false;
    }
  }
</script>

<button
  type="button"
  class="like"
  class:active={optimisticLiked}
  on:click={toggle}
  disabled={busy || !$isAuthenticated}
  title={$isAuthenticated ? (optimisticLiked ? 'Unlike' : 'Like') : 'Sign in to like'}
>
  <svg width="16" height="16" viewBox="0 0 24 24" fill={optimisticLiked ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
  <span>{optimisticCount}</span>
</button>

<style>
  .like {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    transition: all 0.15s ease;
  }
  .like:hover:not(:disabled) {
    border-color: var(--text-muted);
    color: var(--text);
  }
  .like.active {
    color: var(--danger);
    border-color: var(--danger);
    background: #FEE2E2;
  }
  .like:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
