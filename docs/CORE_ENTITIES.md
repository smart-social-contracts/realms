# Core Entities Reference

Complete reference for all GGG (Generalized Global Governance) entities in the Realms platform.

---

## Entity Categories

### 👥 Users & Identity

#### **User**
Platform user with authentication and permissions.

```python
from ggg import User, UserProfile, Profiles

# Create user
user = User(
    id="alice_2024",
    profile_picture_url="https://..."
)

# Add profiles
user.profiles.add(UserProfile[Profiles.MEMBER["name"]])
```

**Fields:** `id`, `profile_picture_url`, `profiles` (relation), `balances` (relation)

#### **Citizen**
User with full citizenship rights and benefits.

```python
from ggg import Citizen, User

citizen = Citizen(
    user=User["alice_2024"],
    is_compliant=True,
    eligible_for_benefits=True,
    last_compliance_check="2024-11-20"
)
```

**Fields:** `user`, `is_compliant`, `eligible_for_benefits`, `last_compliance_check`

#### **Human**
Physical person identity with biometric/legal data.

```python
from ggg import Human, User

human = Human(
    first_name="Alice",
    last_name="Smith",
    date_of_birth="1990-05-15",
    user=User["alice_2024"]
)
```

**Fields:** `first_name`, `last_name`, `date_of_birth`, `user` (relation)

#### **Identity**
Authentication credential (Internet Identity, email, etc).

```python
from ggg import Identity

identity = Identity(
    type="internet_identity",
    metadata="2ibo7-dia"  # II principal
)
```

**Fields:** `type`, `metadata`

#### **Organization**
Companies, DAOs, government agencies.

```python
from ggg import Organization

org = Organization(
    name="Acme Corp",
    org_type="company",
    description="Widget manufacturer"
)
```

**Fields:** `name`, `org_type`, `description`

---

### 🏛️ Governance

#### **Proposal**
Governance proposals for community voting.

```python
from ggg import Proposal, User

proposal = Proposal(
    proposal_id="prop_001",
    title="Increase UBI to 1500",
    description="Raise universal basic income payment",
    proposer=User["admin"],
    status="voting",
    voting_deadline="2024-12-01T00:00:00",
    votes_yes=0.0,
    votes_no=0.0,
    required_threshold=0.51
)
```

**Fields:** `proposal_id`, `title`, `description`, `proposer`, `status`, `voting_deadline`, `votes_yes`, `votes_no`, `votes_abstain`, `total_voters`, `required_threshold`

#### **Vote**
Individual vote on a proposal.

```python
from ggg import Vote, Proposal, User

vote = Vote(
    proposal=Proposal["prop_001"],
    voter=User["alice_2024"],
    vote_choice="yes"  # 'yes', 'no', 'abstain'
)
```

**Fields:** `proposal`, `voter`, `vote_choice`, `metadata`

#### **Mandate**
Authority granted to perform governance actions.

```python
from ggg import Mandate

mandate = Mandate(
    name="tax_collection",
    metadata="Authorized to collect taxes"
)
```

**Fields:** `name`, `metadata`

#### **Codex**
Executable Python code for automation.

```python
from ggg import Codex

codex = Codex(
    name="tax_collection",
    code="""
from ggg import User, Transfer, Treasury

for user in User.instances():
    tax = calculate_tax(user)
    Transfer(from_user=user, to=Treasury["main"], amount=tax)
"""
)
```

**Fields:** `name`, `code`

---

### 💰 Finance

#### **Treasury**
Realm treasury managing funds.

```python
from ggg import Treasury, Realm

treasury = Treasury(
    name="Main Treasury",
    vault_principal_id="rrkah-fqaaa-...",
    realm=Realm["1"]
)
```

**Fields:** `name`, `vault_principal_id`, `realm`

#### **Instrument**
Financial instrument (token, currency).

```python
from ggg import Instrument

instrument = Instrument(
    name="Realm Token",
    symbol="RLM",
    instrument_type="token",
    total_supply=1000000
)
```

**Fields:** `name`, `symbol`, `instrument_type`, `total_supply`

#### **Balance**
User's balance for an instrument.

```python
from ggg import Balance, User

balance = Balance(
    id="alice_2024_RLM",
    user=User["alice_2024"],
    instrument="Realm Token",
    amount=5000
)
```

**Fields:** `id`, `user`, `instrument`, `amount`, `tag`

#### **Transfer**
Asset transfer between entities.

```python
from ggg import Transfer

transfer = Transfer(
    id="tx_001",
    principal_from="alice_2024",
    principal_to="treasury",
    instrument="Realm Token",
    amount=100,
    transfer_type="internal",  # or "external"
    status="completed"
)
```

**Fields:** `id`, `principal_from`, `principal_to`, `instrument`, `amount`, `transfer_type`, `status`

#### **Trade**
Completed trade transaction.

```python
from ggg import Trade

trade = Trade(
    trade_id="trade_001",
    buyer="alice_2024",
    seller="bob_2024",
    instrument="Realm Token",
    amount=50,
    price=2.5
)
```

**Fields:** `trade_id`, `buyer`, `seller`, `instrument`, `amount`, `price`

---

### ⚙️ Tasks & Automation

#### **Task**
Automated task with execution steps.

```python
from ggg import Task, TaskStep, Call, Codex

codex = Codex(name="daily_tax", code="...")
call = Call(codex=codex, is_async=False)
step = TaskStep(call=call)

task = Task(
    name="daily_tax_collection",
    steps=[step]
)
```

**Fields:** `name`, `steps` (relation)

#### **TaskSchedule**
Schedule for recurring tasks.

```python
from ggg import TaskSchedule, Task

schedule = TaskSchedule(
    name="daily_at_midnight",
    task=Task["daily_tax_collection"],
    repeat_every=86400,  # seconds
    run_after=0
)
```

**Fields:** `name`, `task`, `repeat_every`, `run_after`, `enabled`

#### **TaskEntity**
Task-scoped storage for batch processing.

```python
from kybra_simple_db import String, Integer

# Inside task codex - automatically available
class BatchState(TaskEntity):
    __alias__ = "key"
    key = String()
    position = Integer()

state = BatchState["main"]
if not state:
    state = BatchState(key="main", position=0)
```

→ [Full TaskEntity Documentation](./TASK_ENTITY.md)

---

### 🏢 Services & Registry

#### **Service**
Platform service offering.

```python
from ggg import Service

service = Service(
    name="Identity Verification",
    service_type="verification",
    description="Official ID verification service"
)
```

**Fields:** `name`, `service_type`, `description`

#### **License**
Permission to use a service or resource.

```python
from ggg import License, User

license = License(
    license_id="lic_001",
    holder=User["alice_2024"],
    license_type="business",
    expires_at="2025-12-31"
)
```

**Fields:** `license_id`, `holder`, `license_type`, `expires_at`, `status`

#### **Dispute**
Conflict resolution case.

```python
from ggg import Dispute, User

dispute = Dispute(
    case_id="dispute_001",
    plaintiff=User["alice_2024"],
    defendant=User["bob_2024"],
    dispute_type="contract",
    status="open",
    priority="medium"
)
```

**Fields:** `case_id`, `plaintiff`, `defendant`, `dispute_type`, `status`, `priority`, `description`

#### **Realm**
Realm instance configuration.

```python
from ggg import Realm

realm = Realm(
    name="Demo Governance Realm",
    description="A realm for digital governance",
    principal_id="rrkah-fqaaa-...",
    status="active",
    governance_type="democratic"
)
```

**Fields:** `name`, `description`, `principal_id`, `status`, `governance_type`, `population`, `organization_count`, `settings`

#### **Registry**
External registry entry.

```python
from ggg import Registry

registry = Registry(
    name="Central Realm Registry",
    registry_type="realm_registry",
    url="https://registry.realmsgos.org"
)
```

**Fields:** `name`, `registry_type`, `url`

---

### 📄 Additional Entities

#### **Permission**
Fine-grained access control.

```python
from ggg import Permission

permission = Permission(
    name="create_proposal",
    resource_type="governance",
    action="create"
)
```

**Fields:** `name`, `resource_type`, `action`

#### **UserProfile**
User role with permissions.

```python
from ggg import UserProfile

profile = UserProfile(
    name="member",
    allowed_to="read,vote,transfer",
    description="Standard member permissions"
)
```

**Fields:** `name`, `allowed_to`, `description`

#### **Notification**
User notification.

```python
from ggg import Notification, User

notification = Notification(
    user=User["alice_2024"],
    title="New Proposal",
    message="A new proposal requires your vote",
    notification_type="governance",
    is_read=False
)
```

**Fields:** `user`, `title`, `message`, `notification_type`, `is_read`

#### **Land**
Real estate/property record.

```python
from ggg import Land, LandType

land = Land(
    parcel_id="LOT-001",
    land_type=LandType.RESIDENTIAL,
    area=500.0,
    address="123 Main St",
    owner_id="alice_2024"
)
```

**Fields:** `parcel_id`, `land_type`, `area`, `address`, `owner_id`, `coordinates`

#### **Contract**
Legal contract record.

```python
from ggg import Contract

contract = Contract(
    contract_id="cont_001",
    contract_type="service",
    parties="alice_2024,bob_2024",
    terms="Service delivery agreement",
    status="active"
)
```

**Fields:** `contract_id`, `contract_type`, `parties`, `terms`, `status`

#### **TaxRecord**
Tax payment record.

```python
from ggg import TaxRecord, User

tax = TaxRecord(
    user=User["alice_2024"],
    tax_year=2024,
    amount_due=1000,
    amount_paid=1000,
    status="paid"
)
```

**Fields:** `user`, `tax_year`, `amount_due`, `amount_paid`, `status`

---

## Entity Relationships

### Common Patterns

**One-to-Many:**
```python
# User has many Balances
user = User["alice_2024"]
balances = user.balances  # All balances for this user
```

**Many-to-One:**
```python
# Balance belongs to User
balance = Balance["alice_2024_RLM"]
user = balance.user  # The user who owns this balance
```

**Many-to-Many:**
```python
# User has many Profiles
user = User["alice_2024"]
user.profiles.add(UserProfile["member"])
user.profiles.add(UserProfile["admin"])
```

### Key Relationships

```
User
├─ has many: Balances, Votes, Proposals, Notifications
├─ belongs to: Citizen, Human
└─ has many-to-many: UserProfiles

Proposal
├─ belongs to: User (proposer)
└─ has many: Votes

Treasury
├─ belongs to: Realm
└─ related to: Transfers

Task
├─ has many: TaskSteps
└─ belongs to: TaskSchedule
```

---

## Usage Examples

### Create Complete User Identity
```python
from ggg import User, Human, Citizen, Identity, UserProfile, Profiles

# 1. Create user account
user = User(id="alice_2024", profile_picture_url="https://...")

# 2. Add profile permissions
user.profiles.add(UserProfile[Profiles.MEMBER["name"]])

# 3. Link to human identity
human = Human(
    first_name="Alice",
    last_name="Smith",
    date_of_birth="1990-05-15",
    user=user
)

# 4. Grant citizenship
citizen = Citizen(
    user=user,
    is_compliant=True,
    eligible_for_benefits=True
)

# 5. Link authentication
identity = Identity(type="internet_identity", metadata="ii-principal")
```

### Governance Workflow
```python
from ggg import Proposal, Vote, User

# 1. Create proposal
proposal = Proposal(
    proposal_id="prop_ubi",
    title="Increase UBI",
    proposer=User["admin"],
    status="voting",
    required_threshold=0.51
)

# 2. Users vote
Vote(proposal=proposal, voter=User["alice_2024"], vote_choice="yes")
Vote(proposal=proposal, voter=User["bob_2024"], vote_choice="no")

# 3. Tally votes (in codex)
total = Proposal["prop_ubi"].total_voters
yes_pct = Proposal["prop_ubi"].votes_yes / total
if yes_pct >= 0.51:
    proposal.status = "approved"
```

### Financial Operations
```python
from ggg import Balance, Transfer, Treasury, User

# 1. Check balance
balance = Balance["alice_2024_RLM"]
print(f"Balance: {balance.amount}")

# 2. Create transfer
transfer = Transfer(
    id="tx_tax_001",
    principal_from="alice_2024",
    principal_to="treasury",
    instrument="Realm Token",
    amount=100,
    transfer_type="internal",
    status="completed"
)

# 3. Update balances (typically done automatically)
balance.amount -= 100
```

### Scheduled Tasks
```python
from ggg import Task, TaskSchedule, TaskStep, Call, Codex

# 1. Create codex
codex = Codex(name="daily_tax", code=tax_collection_code)

# 2. Create task
call = Call(codex=codex, is_async=False)
step = TaskStep(call=call)
task = Task(name="tax_collection", steps=[step])

# 3. Schedule
schedule = TaskSchedule(
    name="daily_tax_schedule",
    task=task,
    repeat_every=86400,  # 24 hours
    enabled=True
)
```

---

## Database Operations

### Query Patterns
```python
from ggg import User, Citizen

# Get all instances
users = list(User.instances())

# Get by ID
user = User["alice_2024"]

# Get by alias
user = User["alice_2024"]  # if __alias__ = "id"

# Count
count = User.count()

# Load paginated
users = User.load_some(from_id=1, count=100)
```

### Relationships
```python
# Access related entities
user = User["alice_2024"]
balances = list(user.balances)  # OneToMany

balance = Balance["alice_2024_RLM"]
owner = balance.user  # ManyToOne

# Many-to-many
user.profiles.add(profile)
user.profiles.remove(profile)
all_profiles = list(user.profiles)
```

---

## Entity Mixins

All entities inherit from `TimestampedMixin`:

```python
entity.timestamp_created  # ISO datetime
entity.timestamp_updated  # ISO datetime
entity.creator           # User ID who created
entity.updater           # User ID who last updated
entity.owner             # User ID who owns
```

---

## See Also

- [API Reference](./API_REFERENCE.md) - Backend endpoints for entity operations
- [Task System](./TASK_ENTITY.md) - TaskEntity for batch processing
- [Method Overrides](./METHOD_OVERRIDE_SYSTEM.md) - Extending entity methods
- [CLI Reference](./CLI_REFERENCE.md) - Entity import/export commands
