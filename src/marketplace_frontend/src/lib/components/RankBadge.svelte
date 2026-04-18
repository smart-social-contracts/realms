<script lang="ts">
  /**
   * Small "#1 / #2 / #3" medal for the Top Charts list.
   * Falls back to a plain numeric badge for ranks ≥ 4.
   */
  export let rank: number;
</script>

<span class="rank rank-{Math.min(rank, 4)}">{rank <= 3 ? medalFor(rank) : `#${rank}`}</span>

<script lang="ts" context="module">
  function medalFor(r: number): string {
    if (r === 1) return '🥇';
    if (r === 2) return '🥈';
    if (r === 3) return '🥉';
    return `#${r}`;
  }
</script>

<style>
  .rank {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--surface-2);
    font-weight: 600;
    font-size: 0.85rem;
  }
  .rank-1 { background: #FEF3C7; }
  .rank-2 { background: #E5E7EB; }
  .rank-3 { background: #FED7AA; }
</style>
