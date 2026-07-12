<script>
  import { _ } from 'svelte-i18n';

  export let version = '';
  export let commitHash = '';
  export let commitDatetime = '';
  export let casalsUrl = '';
</script>

<footer class="registry-footer">
  <div class="footer-meta">
    <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" class="github-link" aria-label="GitHub">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
      </svg>
    </a>
    <span class="footer-separator">/</span>
    <a
      href={casalsUrl || 'https://mcqbx-hyaaa-aaaaj-qsarq-cai.icp0.io'}
      target="_blank"
      rel="noopener noreferrer"
      class="casals-link"
      aria-label={$_('footer.casals')}
      title={$_('footer.casals')}
    >
      <img src="/images/casals-logo.png" alt="Casals" width="18" height="18" class="casals-logo" />
    </a>
    <span class="footer-separator">/</span>
    <span class="footer-version">
      {$_('page_title')}
      {version}{commitHash && commitHash !== 'local' && commitHash !== 'dev' ? ` (${commitHash})` : ''}
      - {commitDatetime}
      {#if typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname.endsWith('.localhost'))}
        - {$_('footer.local_deployment')}
      {/if}
    </span>
  </div>

  <div class="footer-ic">
    <a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" class="ic-link">
      <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="20" height="20" class="ic-logo" />
      <span>{$_('footer.built_on_ic')}</span>
    </a>
  </div>
</footer>

<style>
  .registry-footer {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 1rem 0.75rem;
    font-family: var(--font-family);
    font-size: 0.6875rem;
    color: var(--text-faint);
    pointer-events: auto;
    text-align: center;
  }

  .footer-ic,
  .footer-meta {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .footer-version {
    color: var(--text-faint);
  }

  .ic-link {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    color: var(--text-faint);
    text-decoration: none;
  }

  .ic-link:hover {
    color: var(--text-tertiary);
  }

  .github-link,
  .casals-link {
    color: var(--text-faint);
    display: flex;
    align-items: center;
  }

  .github-link:hover {
    color: var(--text-tertiary);
  }

  .casals-link:hover {
    opacity: 0.75;
  }

  .casals-logo {
    display: block;
    border-radius: 4px;
  }

  .footer-separator {
    color: var(--border);
  }

  @media (max-width: 767px) {
    .registry-footer {
      display: none;
    }
  }
</style>
