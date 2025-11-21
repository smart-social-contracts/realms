# Troubleshooting Guide

Common issues and solutions for Realms platform.

---

## Installation Issues

### `dfx` Command Not Found

**Problem:** Shell can't find dfx command.

**Solution:**
```bash
# Install DFX
sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"

# Add to PATH
echo 'export PATH="$PATH:$HOME/bin"' >> ~/.bashrc
source ~/.bashrc

# Verify
dfx --version
```

---

### Python Version Mismatch

**Problem:** `realms` requires Python 3.10+.

**Solution:**
```bash
# Check version
python --version

# Install Python 3.10+ (Ubuntu/Debian)
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# Use specific version
python3.10 -m pip install -e cli/
```

---

### CLI Installation Fails

**Problem:** `pip install` errors.

**Solution:**
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate

# Install with verbose output
pip install -e cli/ -v

# If permission issues
pip install --user -e cli/
```

---

## Deployment Issues

### Replica Won't Start

**Problem:** `dfx start` fails or hangs.

**Solution:**
```bash
# Stop any running instances
dfx stop

# Clean state
rm -rf .dfx/

# Start fresh
dfx start --clean --background

# Check logs
tail -f .dfx/replica-configuration/replica-1.log
```

---

### Canister Creation Fails

**Problem:** "Out of cycles" or creation timeout.

**Solution:**
```bash
# Check cycles balance
dfx wallet balance

# Get more cycles
dfx ledger account-id
# Send ICP to this address
dfx cycles convert 10

# Create with explicit cycles
dfx canister create realm_backend --with-cycles 5000000000000
```

---

### Build Fails

**Problem:** Kybra build errors.

**Solution:**
```bash
# Clear build cache
rm -rf .kybra/
dfx cache clean

# Install dependencies
pip install -r requirements.txt

# Build with verbose output
dfx build --check
```

---

### Frontend Not Loading

**Problem:** Blank page or 404 errors.

**Solution:**
```bash
# Rebuild frontend
cd src/realm_frontend
rm -rf node_modules .svelte-kit
npm install
npm run build

# Redeploy
cd ../..
dfx deploy realm_frontend
```

---

## Runtime Issues

### Authentication Fails

**Problem:** Internet Identity login doesn't work.

**Solution:**
```bash
# Check II canister
dfx canister id internet_identity

# Update config
II_ID=$(dfx canister id internet_identity --network local)
echo "export const II_CANISTER = '$II_ID';" > src/realm_frontend/src/lib/config.js

# Clear browser cache
# Restart replica
dfx restart
```

---

### Extension Not Loading

**Problem:** Extension doesn't appear or fails to load.

**Solution:**
```bash
# Check installation
realms extension list

# Reinstall
./scripts/install_extensions.sh

# Check manifest
cat extensions/my_ext/manifest.json

# View logs
dfx canister logs realm_backend

# Verify backend call
dfx canister call realm_backend get_extensions
```

---

### Backend Call Fails

**Problem:** API calls timeout or error.

**Solution:**
```bash
# Test backend
dfx canister call realm_backend status

# Check cycles
dfx canister status realm_backend

# View logs
dfx canister logs realm_backend

# Increase timeout
dfx canister call realm_backend my_method --timeout 120
```

---

### Task Not Running

**Problem:** Scheduled task doesn't execute.

**Solution:**
```bash
# List tasks
realms ps ls

# Check logs
realms ps logs <task_id> --tail 50

# Verify schedule
dfx canister call realm_backend list_scheduled_tasks

# Manual run
realms run --file my_task.py
```

---

## Data Issues

### Import Fails

**Problem:** `realms import` fails with errors.

**Solution:**
```bash
# Check JSON syntax
python -m json.tool realm_data.json

# Use smaller batches
realms import data.json --batch-size 10

# Dry run first
realms import data.json --dry-run

# Check backend logs
dfx canister logs realm_backend
```

---

### Entity Not Found

**Problem:** Can't load entity by ID.

**Solution:**
```python
from ggg import User

# Check if exists
user = User["alice_2024"]
if not user:
    print("User not found")

# List all
users = list(User.instances())
print(f"Total users: {len(users)}")

# Check by different methods
count = User.count()
user = User.load_by_id(5)  # By internal ID
```

---

### Database Full

**Problem:** "Storage limit exceeded" errors.

**Solution:**
```bash
# Export data
realms export --output-dir backup

# Reinstall canister (wipes data!)
dfx deploy realm_backend --mode reinstall

# Initialize
dfx canister call realm_backend initialize

# Re-import essential data only
realms import critical_data.json
```

---

## Performance Issues

### Slow API Responses

**Problem:** Backend calls take too long.

**Solution:**
```python
# Use pagination
response = callBackend('get_objects_paginated', [
    'User', 0, 100, 'asc'  # Smaller page size
])

# Cache responses
let cache = {};
if (cache[key]) return cache[key];
const data = await callBackend(...);
cache[key] = data;
```

---

### Task Timeout

**Problem:** Task exceeds cycle limit.

**Solution:**
```python
# Use TaskEntity for batch processing
from kybra_simple_db import String, Integer

class BatchState(TaskEntity):
    __alias__ = "key"
    key = String()
    position = Integer()

BATCH_SIZE = 100  # Process in smaller batches

state = BatchState["main"] or BatchState(key="main", position=0)
users = list(User.instances())
batch = users[state.position:state.position + BATCH_SIZE]

# Process batch...

state.position += BATCH_SIZE
```

→ [TaskEntity Documentation](./TASK_ENTITY.md)

---

### Memory Issues

**Problem:** "Out of memory" errors.

**Solution:**
```bash
# Check memory usage
dfx canister status realm_backend

# Optimize queries
# Use load_some() instead of instances()
users = User.load_some(from_id=1, count=100)

# Clear old data
# Implement data archiving strategy
```

---

## Network Issues

### Can't Connect to IC

**Problem:** Network calls fail on IC mainnet.

**Solution:**
```bash
# Check network connectivity
dfx ping --network ic

# Verify canister IDs
dfx canister id realm_backend --network ic

# Check identity
dfx identity whoami
dfx identity get-principal

# Try different replica
# Edit networks.json
```

---

### CORS Errors

**Problem:** Frontend can't call backend (local dev).

**Solution:**
```javascript
// Check canister URL
const canisterId = process.env.CANISTER_ID_REALM_BACKEND;
const host = 'http://localhost:8000';

// Verify Internet Identity
const II_URL = `http://${II_CANISTER_ID}.localhost:8000`;
```

---

## Extension Development

### Extension Not Installing

**Problem:** Installation script fails.

**Solution:**
```bash
# Check manifest
cat extensions/my_ext/manifest.json | python -m json.tool

# Check extension ID (no hyphens!)
# BAD: my-ext
# GOOD: my_ext

# Manual install
cd scripts
python realm-extension-cli.py install --package-path ../extensions/my_ext.zip

# Check logs
tail -f install.log
```

---

### Frontend Component Not Rendering

**Problem:** Extension page is blank.

**Solution:**
```bash
# Check route exists
ls -la src/realm_frontend/src/routes/\(sidebar\)/extensions/my_ext/

# Check component
ls -la src/realm_frontend/src/lib/extensions/my_ext/

# Rebuild frontend
cd src/realm_frontend
npm run build

# Check browser console for errors
```

---

### Translation Keys Not Working

**Problem:** Shows literal keys instead of translations.

**Solution:**
```bash
# Check i18n files
ls -la src/realm_frontend/src/lib/i18n/locales/extensions/my_ext/

# Verify key structure
cat extensions/my_ext/frontend/i18n/en.json

# Check import in component
# Should be: $_('extensions.my_ext.key')
```

---

## Security Issues

### Unauthorized Access

**Problem:** Users accessing restricted features.

**Solution:**
```python
# Backend validation
from kybra import ic

def admin_only_function(args: str):
    # Check caller
    caller = ic.caller().to_str()
    
    # Verify admin profile
    from ggg import User
    user = User[caller]
    if not user or 'admin' not in [p.name for p in user.profiles]:
        raise Exception("Unauthorized")
    
    # Continue...
```

---

### Session Expired

**Problem:** User logged out unexpectedly.

**Solution:**
```typescript
// Check session expiry
const authClient = await AuthClient.create();
const isAuthenticated = await authClient.isAuthenticated();

if (!isAuthenticated) {
    // Redirect to login
    goto('/login');
}

// Set longer session
await authClient.login({
    maxTimeToLive: BigInt(7 * 24 * 60 * 60 * 1000 * 1000 * 1000) // 7 days
});
```

---

## Common Error Messages

### "Canister not found"
```bash
# Solution: Deploy canister first
dfx deploy realm_backend
```

### "Principal not found"
```bash
# Solution: Register user
dfx canister call realm_backend join_realm '("member")'
```

### "Method not found"
```bash
# Solution: Check method name spelling
dfx canister call realm_backend status  # Correct
```

### "Insufficient cycles"
```bash
# Solution: Top up cycles
dfx canister deposit-cycles 1000000000000 realm_backend
```

### "Storage full"
```bash
# Solution: Export and reinstall
realms export
dfx deploy --mode reinstall
```

---

## Debugging Techniques

### Enable Verbose Logging

```python
# In codex/backend code
from kybra import ic

ic.print("Debug message")
ic.print(f"Variable value: {my_var}")
```

### Check Logs

```bash
# Backend logs
dfx canister logs realm_backend

# Frontend dev logs
npm run dev  # Watch console

# Task logs
realms ps logs <task_id>
```

### Test in Shell

```bash
# Interactive testing
realms shell --file test.py

# Or direct call
dfx canister call realm_backend execute_code '("print(User.count())")'
```

### Inspect State

```bash
# Use DB explorer
realms db

# Or query directly
dfx canister call realm_backend get_objects_paginated '("User", 0, 10, "desc")'
```

---

## Getting Help

### 1. Check Documentation
- [API Reference](./API_REFERENCE.md)
- [Core Entities](./CORE_ENTITIES.md)
- [CLI Reference](./CLI_REFERENCE.md)

### 2. Check Examples
```bash
ls examples/
# Review similar implementations
```

### 3. Check Logs
```bash
dfx canister logs realm_backend
realms ps logs <task_id>
```

### 4. Community Support
- GitHub Issues
- Developer Forum
- Discord Community

---

## Prevention Tips

### Development Best Practices
- Test locally before IC deployment
- Use version control
- Regular backups (`realms export`)
- Monitor cycles balance
- Keep dependencies updated

### Deployment Checklist
- [ ] Build succeeds
- [ ] Tests pass
- [ ] Cycles sufficient
- [ ] Backup created
- [ ] Network configured
- [ ] Identity set
- [ ] Monitoring enabled

---

## See Also

- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Deployment process
- [API Reference](./API_REFERENCE.md) - API documentation
- [CLI Reference](./CLI_REFERENCE.md) - Command reference
