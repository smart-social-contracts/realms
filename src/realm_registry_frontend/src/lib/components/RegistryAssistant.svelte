<!--
  Registry-level AI assistant (issue #233).

  This is the USER-SCOPED assistant surface that lives on the registry (the
  canonical II origin). Because it runs outside any realm it talks to Geister in
  GENERAL mode: it sends no `context_realm`, so the backend skips realm status /
  codex / proposal enrichment and realm-scoped tools, and answers cross-realm
  questions ("which realm should I join?", platform help, etc.).

  It deliberately does NOT consult any realm's `ai_assistant_enabled` flag — a
  realm cannot disable the user's global assistant. When the user is signed in
  with Internet Identity (canonical principal), conversations persist via the
  same Geister endpoints used inside realms, so history follows the user between
  the registry and every realm.

  Svelte 4 (the registry frontend is Svelte 4, so this does not reuse the
  Svelte 5 `LlmChat.svelte` extension component).
-->
<script>
  import { onMount, tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { CONFIG } from '$lib/config.js';

  const PRODUCTION_API_HOST = 'https://geister-api.realmsgos.dev/';
  const API_URL = `${PRODUCTION_API_HOST}api/ask`;
  const CHAT_REQUEST_TIMEOUT_MS = 360_000;

  // Geister network: reuse the registry's deploy-queue network mapping.
  const GEISTER_NETWORK = CONFIG.default_deploy_queue_network || 'staging';

  let open = false;
  /** @type {{ text: string, isUser: boolean }[]} */
  let messages = [];
  let newMessage = '';
  let isLoading = false;
  let loadingStatus = '';
  let error = '';
  let userPrincipal = '';
  /** @type {HTMLElement | undefined} */
  let messagesContainer;
  // Capture the scroll container via an action (preferred over bind:this).
  function scrollRegion(node) {
    messagesContainer = node;
    return { destroy() { messagesContainer = undefined; } };
  }

  onMount(async () => {
    try {
      const { isAuthenticated, getPrincipal } = await import('$lib/auth.js');
      if (await isAuthenticated()) {
        const p = await getPrincipal();
        userPrincipal = p ? p.toText() : '';
      }
    } catch (e) {
      // Anonymous use is allowed (no persistence); ignore auth errors.
    }
  });

  async function scrollToBottom() {
    await tick();
    if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function upsertAssistant(text) {
    const last = messages[messages.length - 1];
    if (!last || last.isUser) {
      messages = [...messages, { text, isUser: false }];
    } else {
      messages = messages.map((m, i) => (i === messages.length - 1 ? { ...m, text } : m));
    }
    void scrollToBottom();
  }

  function handleStreamEvent(parsed, state) {
    const eventType = typeof parsed.type === 'string' ? parsed.type : parsed.text ? 'text' : '';
    const chunk = typeof parsed.text === 'string' ? parsed.text : '';
    if (eventType === 'status' && chunk) {
      loadingStatus = chunk;
      return;
    }
    if (eventType === 'thinking') {
      // Registry surface keeps it simple: no separate thinking pane.
      return;
    }
    if (chunk) {
      state.text += chunk;
      loadingStatus = '';
      upsertAssistant(state.text);
    }
  }

  async function send() {
    const question = newMessage.trim();
    if (!question || isLoading) return;
    error = '';
    messages = [...messages, { text: question, isUser: true }];
    newMessage = '';
    isLoading = true;
    loadingStatus = $_('assistant.thinking', { default: 'Thinking…' });
    void scrollToBottom();

    try {
      // GENERAL MODE: no context_realm — cross-realm / platform-level help.
      const payload = {
        question,
        user_principal: userPrincipal,
        stream: true,
        verbosity: 1,
        persona: 'ashoka',
        network: GEISTER_NETWORK,
      };

      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(CHAT_REQUEST_TIMEOUT_MS),
      });

      if (!response.ok) {
        let detail = '';
        try {
          const body = await response.json();
          detail = typeof body?.error === 'string' ? body.error : '';
        } catch (e) { /* ignore non-JSON */ }
        throw new Error(detail || `HTTP error! Status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Response body is not readable');
      const decoder = new TextDecoder();
      const state = { text: '' };
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split('\n')) {
            if (line.startsWith('data: ')) {
              const pl = line.slice(6);
              if (pl === '[DONE]') continue;
              try {
                handleStreamEvent(JSON.parse(pl), state);
              } catch (e) {
                state.text += pl;
                upsertAssistant(state.text);
              }
            } else if (line.trim() && !line.startsWith(':')) {
              state.text += line;
              upsertAssistant(state.text);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      if (!state.text.trim()) {
        upsertAssistant($_('assistant.no_response', { default: 'No response from the assistant.' }));
      }
    } catch (err) {
      console.error('Registry assistant error:', err);
      error =
        err?.name === 'TimeoutError'
          ? $_('assistant.timeout', { default: 'The assistant took too long to respond. Please try again.' })
          : $_('assistant.offline', { default: 'The AI assistant is temporarily unavailable. Please try again shortly.' });
      // Drop the empty assistant bubble if nothing streamed.
      if (messages.length && !messages[messages.length - 1].isUser && !messages[messages.length - 1].text) {
        messages = messages.slice(0, -1);
      }
    } finally {
      isLoading = false;
      loadingStatus = '';
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<button
  class="assistant-fab"
  class:open
  on:click={() => (open = !open)}
  aria-label={$_('assistant.toggle', { default: 'AI Assistant' })}
  title={$_('assistant.toggle', { default: 'AI Assistant' })}
>
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
  </svg>
</button>

{#if open}
  <section class="assistant-panel" aria-label={$_('assistant.title', { default: 'Realms Assistant' })}>
    <header class="assistant-header">
      <span class="assistant-title">{$_('assistant.title', { default: 'Realms Assistant' })}</span>
      <button class="assistant-close" on:click={() => (open = false)} aria-label="Close">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
      </button>
    </header>

    <div class="assistant-messages" use:scrollRegion>
      {#if messages.length === 0}
        <div class="assistant-empty">
          {$_('assistant.empty', { default: 'Ask me anything about the realms in the registry — which to join, how to create one, or how Realms works.' })}
        </div>
      {/if}
      {#each messages as m, i (i)}
        <div class="assistant-msg" class:user={m.isUser}>
          <div class="assistant-bubble">{m.text}</div>
        </div>
      {/each}
      {#if isLoading && loadingStatus}
        <div class="assistant-status">{loadingStatus}</div>
      {/if}
      {#if error}
        <div class="assistant-error">{error}</div>
      {/if}
    </div>

    <div class="assistant-input">
      <textarea
        bind:value={newMessage}
        on:keydown={onKeydown}
        rows="1"
        placeholder={$_('assistant.placeholder', { default: 'Type your message…' })}
        disabled={isLoading}
      ></textarea>
      <button class="assistant-send" on:click={send} disabled={isLoading || !newMessage.trim()}>
        {$_('assistant.send', { default: 'Send' })}
      </button>
    </div>
  </section>
{/if}

<style>
  .assistant-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: #111;
    color: #fff;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
    z-index: 1000;
    transition: transform 0.15s ease;
  }
  .assistant-fab:hover { transform: scale(1.05); }
  .assistant-fab.open { background: #333; }

  .assistant-panel {
    position: fixed;
    bottom: 88px;
    right: 24px;
    width: min(380px, calc(100vw - 48px));
    height: min(560px, calc(100vh - 130px));
    background: #fff;
    border: 1px solid #e5e5e5;
    border-radius: 14px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    z-index: 1000;
  }

  .assistant-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-bottom: 1px solid #eee;
  }
  .assistant-title { font-weight: 600; font-size: 0.95rem; color: #111; }
  .assistant-close { background: none; border: none; cursor: pointer; color: #666; padding: 4px; }

  .assistant-messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .assistant-empty { color: #888; font-size: 0.88rem; line-height: 1.5; }

  .assistant-msg { display: flex; }
  .assistant-msg.user { justify-content: flex-end; }
  .assistant-bubble {
    max-width: 85%;
    padding: 8px 12px;
    border-radius: 12px;
    font-size: 0.9rem;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
    background: #f3f3f3;
    color: #111;
  }
  .assistant-msg.user .assistant-bubble { background: #111; color: #fff; }

  .assistant-status { color: #888; font-size: 0.82rem; font-style: italic; }
  .assistant-error { color: #b00020; font-size: 0.85rem; }

  .assistant-input {
    display: flex;
    gap: 8px;
    padding: 10px;
    border-top: 1px solid #eee;
  }
  .assistant-input textarea {
    flex: 1;
    resize: none;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 10px;
    font: inherit;
    font-size: 0.9rem;
    max-height: 120px;
  }
  .assistant-send {
    background: #111;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0 14px;
    font-size: 0.88rem;
    cursor: pointer;
  }
  .assistant-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
