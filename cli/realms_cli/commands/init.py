"""
Minimal init command module for test compatibility.

Note: The full init command was removed in commit f1a0adb to simplify CLI focus on deployment.
This module provides only the template functions needed by existing tests.
"""


def _get_dfx_json_template(realm_id: str) -> str:
    """Generate dfx.json template for a realm project."""
    return """{
  "version": 1,
  "canisters": {
    "realm_backend": {
      "type": "custom",
      "build": "python -m kybra realm_backend src/realm_backend/main.py",
      "root": "src/realm_backend",
      "ts": "src/realm_backend/realm_backend.did",
      "wasm": ".kybra/realm_backend/realm_backend.wasm.gz"
    },
    "realm_frontend": {
      "type": "assets",
      "source": ["src/realm_frontend/build"]
    }
  },
  "networks": {
    "local": {
      "bind": "127.0.0.1:8000",
      "type": "ephemeral"
    }
  }
}"""


def _get_readme_template(realm_name: str, realm_id: str) -> str:
    """Generate README.md template for a realm project."""
    return f"""# {realm_name}

A Realms governance platform project.

`{realm_id}`


1. Deploy the realm:
   ```bash
   realms realm deploy --file realm_config.json
   ```

2. Access your realm at the provided URL after deployment.


See `realm_config.json` for deployment configuration.


This realm includes the following extensions:
- Admin Dashboard
- Member Dashboard
- Voting System


For development and testing, use:
```bash
realms realm deploy --network local
```
"""


def init_command(*args, **kwargs):
    """Placeholder init command - functionality was removed in commit f1a0adb."""
    raise NotImplementedError(
        "The init command was removed to simplify CLI focus on deployment. "
        "Use 'realms realm create --random' for generating demo realms or manually create realm_config.json."
    )
