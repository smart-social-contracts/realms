<script lang="ts"></script>

<div class="skeleton" aria-hidden="true">
  <div class="row">
    <span class="box icon" />
    <div class="lines">
      <span class="box line lg" />
      <span class="box line sm" />
    </div>
  </div>
  <span class="box line full" />
  <span class="box line wide" />
  <div class="chips">
    <span class="box chip" />
    <span class="box chip" />
  </div>
  <div class="row foot">
    <span class="box line tiny" />
    <span class="box pill" />
  </div>
</div>

<style>
  .skeleton {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.85rem;
    padding: 1.1rem 1.2rem;
  }
  .row { display: flex; align-items: flex-start; gap: 0.75rem; }
  .lines { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
  .chips { display: flex; gap: 0.35rem; }
  .foot { align-items: center; justify-content: space-between; padding-top: 0.6rem; }

  .box {
    display: block;
    background: var(--surface-2);
    border-radius: 0.35rem;
    animation: pulse 1.3s ease-in-out infinite;
  }
  .icon { width: 44px; height: 44px; border-radius: 0.6rem; }
  .line { height: 0.7rem; }
  .line.lg { width: 60%; height: 0.9rem; }
  .line.sm { width: 40%; }
  .line.full { width: 100%; }
  .line.wide { width: 80%; }
  .line.tiny { width: 25%; }
  .chip { width: 64px; height: 1.1rem; border-radius: 0.35rem; }
  .pill { width: 64px; height: 1.8rem; border-radius: 999px; }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>
