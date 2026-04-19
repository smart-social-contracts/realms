<script lang="ts">
  /**
   * Renders a small badge reflecting the verification status of a listing.
   * Statuses come from the backend: unverified | pending_audit | verified | rejected
   */
  export let status: string = 'unverified';
  export let size: 'sm' | 'md' = 'sm';

  $: meta = (() => {
    switch (status) {
      case 'verified':
        return { label: '✓ Verified', cls: 'verified' };
      case 'pending_audit':
        return { label: '⏳ Audit pending', cls: 'pending' };
      case 'rejected':
        return { label: '✗ Audit rejected', cls: 'rejected' };
      default:
        return { label: 'Unverified', cls: 'unverified' };
    }
  })();
</script>

<span class="badge {meta.cls} {size}">{meta.label}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 500;
    font-size: 0.7rem;
    line-height: 1;
    height: 22px;
    border: 1px solid transparent;
    white-space: nowrap;
  }
  .md { font-size: 0.8rem; height: 26px; padding: 4px 10px; }
  .verified { background: var(--verified-bg); color: var(--verified); border-color: var(--verified); }
  .pending { background: #FEF3C7; color: #92400E; border-color: #F59E0B; }
  .rejected { background: #FEE2E2; color: #991B1B; border-color: #DC2626; }
  .unverified { background: var(--surface-2); color: var(--text-muted); border-color: var(--border); }
</style>
