# @realmsgos/create-extension

Scaffold a sandboxed [Realms](https://github.com/smart-social-contracts/realms) extension project.

## Usage

```bash
npm create @realmsgos/extension my-extension
```

This downloads `@realmsgos/create-extension` and runs `create-realms-extension`.

### Non-interactive flags

```bash
npm create @realmsgos/extension my-extension -- \
  --id my_extension \
  --name "My Extension" \
  --description "Does something useful"
```

| Flag | Description |
|------|-------------|
| `--id` | Extension identifier (`snake_case`, 3–32 chars, `^[a-z][a-z0-9_]{2,31}$`) |
| `--name` | Display name (sidebar label, page title) |
| `--description` | Manifest description (defaults to `"<name> — a sandboxed Realms extension"`) |

The target directory must not exist or must be empty.

## Generated project

- `manifest.json` with `runtime: "sandboxed"` and bridge capabilities
- `frontend/` — Svelte 5 + Vite app using `@realmsgos/extension-bridge` and `@realmsgos/extension-ui` from npm
- `backend/entry.py` — minimal Python stub with a `greet` example

After scaffolding:

```bash
cd my-extension/frontend
npm install
npm run build
```

## Documentation

Extension authoring guide:
https://github.com/smart-social-contracts/realms/blob/main/docs/guide/extension-authoring.md

Bridge protocol reference:
https://github.com/smart-social-contracts/realms/blob/main/docs/reference/EXTENSION_SANDBOXING.md

## License

MIT
