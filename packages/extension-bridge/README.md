# @realms/extension-bridge

Isomorphic TypeScript bridge for sandboxed Realm extensions. Both the SvelteKit
host and the extension iframe bundle import this package to exchange messages
over `postMessage`.

## Install

```bash
npm install @realms/extension-bridge
```

In the Realms monorepo the host frontend depends on the local package via
`file:../../packages/extension-bridge`.

## Extension side (inside the sandbox iframe)

```ts
import { createExtensionClient } from '@realms/extension-bridge';

const ctx = await createExtensionClient();

console.log(ctx.extensionId, ctx.capabilities);

ctx.onStateChange((state) => {
  document.documentElement.dataset.theme = state.theme;
});

await ctx.callExtension('greet', { name: 'Ada' });
ctx.navigate('/extensions/other');
ctx.notify('success', 'Saved');

const { actionId } = await ctx.openModal({
  title: 'Confirm',
  body: 'Delete this item?',
  actions: [
    { id: 'cancel', label: 'Cancel', tone: 'secondary' },
    { id: 'delete', label: 'Delete', tone: 'danger' },
  ],
});

ctx.reportHeight(document.body.scrollHeight);
```

## Host side

```ts
import { createBridgeServer, type HostState } from '@realms/extension-bridge';

const iframe = document.querySelector('iframe')!;

const server = createBridgeServer(iframe, {
  extensionId: 'hello_sandboxed',
  requiredSdkVersion: '1',
  capabilities: ['call_extension', 'navigate', 'notify'],
  entryAccessFunctions: { greet: 'member' },
  getState: (): HostState => ({
    principal: 'aaaaa-aa',
    locale: 'en',
    theme: 'light',
    realmInfo: {
      name: 'My Realm',
      welcomeMessage: 'Welcome',
      manifesto: '',
      isQuarter: false,
      parentRealmCanisterId: '',
    },
  }),
  onCallExtension: async (fn, args) => {
    /* host RPC */
    return { ok: true };
  },
  onNavigate: (path) => {
    /* SvelteKit goto */
  },
  onNotify: (level, message) => {
    /* toast */
  },
  onOpenModal: async ({ title, body, actions }) => {
    /* render modal, return chosen action */
    return { actionId: 'cancel' };
  },
  onResize: (height) => {
    iframe.style.height = `${height}px`;
  },
});

// Push state when stores change
server.pushState(nextState);

// Cleanup
server.destroy();
```

See `docs/reference/EXTENSION_SANDBOXING.md` for the full protocol contract.

## Rate limiting

Fire-and-forget operations are silently dropped when they exceed a per-bridge
sliding-window limit (consistent with denied fire-and-forget semantics):

| Operation | Limit |
|-----------|-------|
| `notify` | 10 per 10s |
| `navigate` | 10 per 10s |
| `resize` | 30 per 10s |

Request/response operations (`call_extension`, `open_modal`) are not
rate-limited; they are gated by capability checks and (for `call_extension`)
the `entry_access.functions` allowlist.
