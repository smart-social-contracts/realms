# 🚧 Continue Mundus Multi-Realm Work

## Current Status

### ✅ What's Complete

1. **CLI Command Structure** - Commands properly organized:
   - `realms realm create` - Create single realm (supports flags OR manifest)
   - `realms mundus create` - Create multi-realm mundus (manifest-only)
   - Both support `--deploy` flag

2. **Manifest-Driven Architecture**:
   - Mundus manifest: `examples/demo/manifest.json` - Defines which realms to create
   - Realm manifests: `examples/demo/realm{N}/manifest.json` - Each has `options.random` for data generation
   - Flags override manifest values for `realms realm create`

3. **Unified dfx.json**: `mundus_generator.py` creates unified `dfx.json` at `.realms/mundus/` with all canisters

4. **Code Reuse**: `mundus_generator.py` calls `realms realm create` for each realm

### ❌ What's Missing

**CRITICAL BUG**: `realm_generator.py` only generates data files, NOT source code!

Currently creates:
```
.realms/mundus/realm1/
├── manifest.json         ✅ Created
└── realm_data.json       ✅ Created
```

Should create:
```
.realms/mundus/realm1/
├── src/
│   ├── realm_backend/    ❌ MISSING
│   └── realm_frontend/   ❌ MISSING
├── extensions/           ❌ MISSING
├── scripts/              ❌ MISSING
├── manifest.json         ✅ Created
└── realm_data.json       ✅ Created
```

---

## 🎯 Task: Fix Source Code Copying

### Problem

When `mundus_generator.py` calls `realms realm create`, which calls `realm_generator.py`, it should copy:
1. `src/realm_backend/` - Backend source
2. `src/realm_frontend/` - Frontend source  
3. `extensions/` - All extensions
4. `scripts/` - Deployment scripts

### Solution Options

**Option A: Fix `realm_generator.py` (RECOMMENDED)**

Update `scripts/realm_generator.py` to copy source folders:

```python
def create_realm(output_dir, realm_name, ...):
    # Existing data generation code...
    
    # ADD THIS: Copy source code
    repo_root = Path(__file__).parent.parent
    
    # Copy backend
    shutil.copytree(
        repo_root / "src" / "realm_backend",
        output_dir / "src" / "realm_backend",
        dirs_exist_ok=True
    )
    
    # Copy frontend
    shutil.copytree(
        repo_root / "src" / "realm_frontend", 
        output_dir / "src" / "realm_frontend",
        dirs_exist_ok=True
    )
    
    # Copy extensions
    shutil.copytree(
        repo_root / "extensions",
        output_dir / "extensions",
        dirs_exist_ok=True
    )
    
    # Copy scripts
    shutil.copytree(
        repo_root / "scripts",
        output_dir / "scripts",
        dirs_exist_ok=True
    )
```

**Option B: Fix in `mundus_generator.py`**

Copy source before calling `realms realm create` (less clean, more duplication).

---

## 🧪 Testing

### Test Single Realm Creation
```bash
rm -rf /tmp/test_realm
realms realm create \
  --output-dir /tmp/test_realm \
  --realm-name "Test Realm" \
  --manifest examples/demo/realm1/manifest.json

# Should have: src/, extensions/, scripts/, manifest.json, realm_data.json
ls -la /tmp/test_realm/
ls -la /tmp/test_realm/src/
```

### Test Mundus Creation
```bash
scripts/clean_dfx.sh && rm -rf .realms
realms mundus create

# Check each realm has source code
ls -la .realms/mundus/realm1/src/
ls -la .realms/mundus/realm2/src/
ls -la .realms/mundus/realm3/src/

# Verify unified dfx.json exists
cat .realms/mundus/dfx.json
```

### Test Full Deployment
```bash
scripts/clean_dfx.sh && rm -rf .realms
realms mundus create --deploy

# Should build all realms and registry
# Should deploy all 8 canisters (3 realms × 2 + 2 registry)
```

---

## 📁 Key Files

### Core Implementation Files
- `cli/realms_cli/main.py` - CLI command definitions
- `cli/realms_cli/commands/create.py` - Realm create logic (calls realm_generator.py)
- `cli/realms_cli/commands/mundus.py` - Mundus create/deploy logic
- `scripts/mundus_generator.py` - Mundus generator (calls `realms realm create`)
- `scripts/realm_generator.py` - **THIS IS WHERE TO ADD SOURCE COPYING**

### Manifest Files
- `examples/demo/manifest.json` - Mundus manifest (lists realms)
- `examples/demo/realm1/manifest.json` - Realm 1 config (50 members, seed 1)
- `examples/demo/realm2/manifest.json` - Realm 2 config (30 members, seed 2)
- `examples/demo/realm3/manifest.json` - Realm 3 config (20 members, seed 3)

---

## 🔍 Understanding the Architecture

### Data Flow

```
User runs: realms mundus create
    ↓
mundus_generator.py reads examples/demo/manifest.json
    ↓
For each realm in manifest (realm1, realm2, realm3):
    ↓
Calls: realms realm create --manifest examples/demo/realm{N}/manifest.json
    ↓
create_command() in cli/realms_cli/commands/create.py
    ↓
Calls: realm_generator.py (with manifest options)
    ↓
realm_generator.py generates data → ⚠️ ADD SOURCE COPYING HERE
```

### Manifest Structure

**Mundus Manifest** (`examples/demo/manifest.json`):
```json
{
  "type": "mundus",
  "name": "Demo Mundus",
  "realms": ["realm1", "realm2", "realm3"],
  "registries": ["registry"]
}
```

**Realm Manifest** (`examples/demo/realm1/manifest.json`):
```json
{
  "type": "realm",
  "name": "Realm 1",
  "options": {
    "random": {
      "members": 50,
      "organizations": 5,
      "transactions": 100,
      "disputes": 10,
      "seed": 1
    }
  }
}
```

---

## 🚀 Next Steps After Fix

Once source copying works:

1. **Test complete workflow**:
   ```bash
   realms mundus create --deploy
   ```

2. **Verify deployed realms**:
   - All 3 realm frontends load
   - All 3 realm backends respond
   - Registry lists all 3 realms
   - Extensions work in each realm

3. **Document usage** in main README

4. **Consider adding**:
   - `realms mundus list` - Show created munduses
   - `realms mundus destroy` - Clean up mundus
   - Per-realm customization (different logos, themes)

---

## 🐛 Known Issues

1. **Lint errors in create.py**: Dead code in `_old_script_generation()` function - safe to ignore or delete
2. **Import lint in main.py line 98**: Type mismatch for `entity_type` - doesn't affect functionality

---

## 💡 Architecture Decisions

### Why Manifest-Driven?

- **Single Realm**: Supports both flags AND manifest (flexibility)
  - Use flags: `realms realm create --members 100 --seed 42`
  - Use manifest: `realms realm create --manifest path/to/manifest.json`
  - Mix: Flags override manifest values

- **Mundus**: Manifest-only (consistency)
  - Realm-specific flags don't make sense at mundus level
  - Each realm's manifest defines its configuration
  - Easy to add realm4, realm5, etc. by updating mundus manifest

### Why Unified dfx.json?

- Deploy all realms at once with single `dfx deploy`
- Simplified canister ID management
- Better for development workflow
- All canisters visible in one place

### Why Reuse `realms realm create`?

- DRY principle - don't duplicate realm creation logic
- Ensures consistency between single realm and mundus realms
- Easier to maintain - fix bugs in one place
- Clear separation of concerns

---

## 📞 Questions?

If stuck, check:
1. Recent git commits for context
2. Run with verbose: `realms mundus create 2>&1 | tee debug.log`
3. Check `.realms/mundus/` directory structure after creation

Good luck! 🚀
