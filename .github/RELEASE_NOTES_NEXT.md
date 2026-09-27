## Summary

- A new realm resolves its fleet file-registry and the Realms treasury ledger from `gos_environment`, read from the Realms repository.
- The setup wizard requires a treasury token (Realms, ckBTC, ckUSDC, or a custom ICRC-1 ledger) and runs initialization in the background. Launch returns immediately and the page shows each phase until the user opens the public dashboard.
- Host defaults (monetary tokens, the demo notice, and quarter capacity) follow `gos_environment`. `realm.network` stays the replica name (`ic`).
