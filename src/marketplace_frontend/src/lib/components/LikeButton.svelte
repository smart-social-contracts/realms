<script lang="ts">import { createEventDispatcher } from "svelte";
import { _ } from "svelte-i18n";
import { isAuthenticated } from "$lib/auth";
import { marketplaceClient } from "$lib/marketplace-client";
export let kind;
export let itemId;
export let liked = false;
export let count = 0;
let busy = false;
let optimisticLiked = liked;
let optimisticCount = count;
$: optimisticLiked = liked;
$: optimisticCount = count;
const dispatch = createEventDispatcher();
async function toggle(e) {
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
    dispatch("change", { liked: optimisticLiked, count: optimisticCount });
  } catch (err) {
    optimisticLiked = wasLiked;
    optimisticCount = Math.max(0, optimisticCount + (wasLiked ? 1 : -1));
    console.error("like toggle failed:", err);
    alert(`Could not ${wasLiked ? "unlike" : "like"}: ${err?.message ?? err}`);
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
  aria-pressed={optimisticLiked}
  aria-label={optimisticLiked ? $_('card.unlike') : $_('card.like')}
  title={$isAuthenticated ? (optimisticLiked ? $_('card.unlike') : $_('card.like')) : $_('card.sign_in_to_like')}
>
  <i class="ti ti-heart" aria-hidden="true"></i>
  {#if optimisticCount > 0}
    <span class="count">{optimisticCount}</span>
  {/if}
</button>

<style>
  .like {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    font-size: 0.8rem;
    transition: all 0.15s ease;
  }
  .like:hover:not(:disabled) {
    border-color: var(--text-muted);
    color: var(--text);
  }
  .like.active {
    color: #fff;
    border-color: var(--primary);
    background: var(--primary);
  }
  .like .ti { font-size: 1rem; line-height: 1; }
  .like .count {
    font-variant-numeric: tabular-nums;
    opacity: 0.85;
  }
  .like:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
