# Governance Tutorial

Complete guide to implementing governance workflows with proposals, voting, and codexes.

---

## Overview

Realms governance enables:
- **Proposals** - Submit changes for community approval
- **Voting** - Democratic decision-making
- **Codexes** - Automated governance execution
- **Mandates** - Authority delegation

---

## Quick Start

### 1. Create a Proposal

```python
from ggg import Proposal, User
from datetime import datetime, timedelta

# Create proposal
proposal = Proposal(
    proposal_id="ubi_increase_2024",
    title="Increase UBI to 1500 Tokens",
    description="Proposal to raise monthly UBI from 1000 to 1500 tokens",
    proposer=User["admin"],
    status="voting",
    voting_deadline=(datetime.now() + timedelta(days=7)).isoformat(),
    votes_yes=0.0,
    votes_no=0.0,
    votes_abstain=0.0,
    total_voters=0.0,
    required_threshold=0.51  # 51% approval required
)
```

---

### 2. Members Vote

```python
from ggg import Vote, Proposal, User

# Alice votes yes
Vote(
    proposal=Proposal["ubi_increase_2024"],
    voter=User["alice_2024"],
    vote_choice="yes"
)

# Bob votes no
Vote(
    proposal=Proposal["ubi_increase_2024"],
    voter=User["bob_2024"],
    vote_choice="no"
)

# Carol abstains
Vote(
    proposal=Proposal["ubi_increase_2024"],
    voter=User["carol_2024"],
    vote_choice="abstain"
)
```

---

### 3. Tally Votes (Automated)

```python
from ggg import Proposal, Vote

def tally_votes(proposal_id: str):
    """Count votes and update proposal status"""
    proposal = Proposal[proposal_id]
    votes = list(proposal.votes)
    
    yes_count = sum(1 for v in votes if v.vote_choice == "yes")
    no_count = sum(1 for v in votes if v.vote_choice == "no")
    abstain_count = sum(1 for v in votes if v.vote_choice == "abstain")
    
    total = len(votes)
    
    # Update proposal
    proposal.votes_yes = float(yes_count)
    proposal.votes_no = float(no_count)
    proposal.votes_abstain = float(abstain_count)
    proposal.total_voters = float(total)
    
    # Check if passed
    if total > 0:
        yes_percent = yes_count / total
        if yes_percent >= proposal.required_threshold:
            proposal.status = "approved"
        elif datetime.now() > datetime.fromisoformat(proposal.voting_deadline):
            proposal.status = "rejected"
    
    return proposal
```

---

### 4. Execute Approved Proposal

```python
from ggg import Proposal, Codex, Task, TaskStep, Call, TaskSchedule

def execute_proposal(proposal_id: str):
    """Execute approved proposal via codex"""
    proposal = Proposal[proposal_id]
    
    if proposal.status != "approved":
        raise Exception("Proposal not approved")
    
    # Create execution codex
    codex = Codex(
        name=f"execute_{proposal_id}",
        code=f"""
from ggg import Realm

# Update UBI setting
realm = Realm["1"]
settings = eval(realm.settings)
settings["ubi_amount"] = 1500
realm.settings = str(settings)

ic.print("UBI updated to 1500")
"""
    )
    
    # Schedule execution
    call = Call(codex=codex, is_async=False)
    step = TaskStep(call=call)
    task = Task(name=f"execute_{proposal_id}", steps=[step])
    
    TaskSchedule(
        name=f"schedule_{proposal_id}",
        task=task,
        repeat_every=0,  # Run once
        run_after=0,
        enabled=True
    )
    
    proposal.status = "executed"
```

---

## Complete Governance Workflow

### Proposal Lifecycle

```
Submit → Voting → (Approved/Rejected) → Execution → Complete
```

### Implementation

**1. Proposal Submission**
```python
from ggg import Proposal, User, Codex

# User submits proposal
proposal = Proposal(
    proposal_id="tax_reform_2024",
    title="Reduce Tax Rate to 10%",
    description="Proposal to reduce realm tax rate from 15% to 10%",
    code_url="https://github.com/realm/proposals/tax_reform",
    code_checksum="sha256:abc123...",
    proposer=User["alice_2024"],
    status="pending_vote",
    voting_deadline=(datetime.now() + timedelta(days=14)).isoformat(),
    required_threshold=0.6
)

# Admin reviews and opens voting
proposal.status = "voting"
```

**2. Voting Period**
```python
from ggg import Vote, Proposal, User

# Members cast votes
def cast_vote(voter_id: str, proposal_id: str, choice: str):
    """Cast a vote with validation"""
    voter = User[voter_id]
    proposal = Proposal[proposal_id]
    
    # Validate
    if proposal.status != "voting":
        raise Exception("Proposal not open for voting")
    
    # Check if already voted
    existing = [v for v in proposal.votes if v.voter == voter]
    if existing:
        raise Exception("Already voted")
    
    # Cast vote
    Vote(
        proposal=proposal,
        voter=voter,
        vote_choice=choice,  # 'yes', 'no', 'abstain'
        metadata=datetime.now().isoformat()
    )
```

**3. Automated Vote Tallying**
```python
# Create codex for automated tallying
vote_tally_codex = Codex(
    name="vote_tally",
    code="""
from ggg import Proposal, Vote
from datetime import datetime

def tally_open_proposals():
    for proposal in Proposal.instances():
        if proposal.status != "voting":
            continue
        
        # Check if deadline passed
        deadline = datetime.fromisoformat(proposal.voting_deadline)
        if datetime.now() < deadline:
            continue
        
        # Count votes
        votes = list(proposal.votes)
        total = len(votes)
        yes = sum(1 for v in votes if v.vote_choice == "yes")
        
        # Update status
        if total > 0 and (yes / total) >= proposal.required_threshold:
            proposal.status = "approved"
            ic.print(f"✅ Proposal {proposal.proposal_id} approved")
        else:
            proposal.status = "rejected"
            ic.print(f"❌ Proposal {proposal.proposal_id} rejected")

tally_open_proposals()
"""
)

# Schedule daily tallying
from ggg import Task, TaskStep, Call, TaskSchedule

call = Call(codex=vote_tally_codex, is_async=False)
step = TaskStep(call=call)
task = Task(name="daily_vote_tally", steps=[step])

TaskSchedule(
    name="daily_tally_schedule",
    task=task,
    repeat_every=86400,  # Daily
    run_after=3600,
    enabled=True
)
```

**4. Proposal Execution**
```python
# Automated execution of approved proposals
execution_codex = Codex(
    name="execute_proposals",
    code="""
from ggg import Proposal, Realm

def execute_approved_proposals():
    for proposal in Proposal.instances():
        if proposal.status != "approved":
            continue
        
        # Execute based on proposal type
        if "tax" in proposal.title.lower():
            # Update tax rate
            realm = Realm["1"]
            settings = eval(realm.settings)
            settings["tax_rate"] = 0.10  # From proposal
            realm.settings = str(settings)
            ic.print(f"✅ Executed: {proposal.title}")
        
        elif "ubi" in proposal.title.lower():
            # Update UBI amount
            realm = Realm["1"]
            settings = eval(realm.settings)
            settings["ubi_amount"] = 1500  # From proposal
            realm.settings = str(settings)
            ic.print(f"✅ Executed: {proposal.title}")
        
        # Mark as executed
        proposal.status = "executed"

execute_approved_proposals()
"""
)
```

---

## Advanced Patterns

### Weighted Voting

```python
from ggg import Vote, Proposal, User, Balance

def cast_weighted_vote(voter_id: str, proposal_id: str, choice: str):
    """Vote weight based on token holdings"""
    voter = User[voter_id]
    proposal = Proposal[proposal_id]
    
    # Get voter's token balance
    balance = Balance[f"{voter_id}_RealmToken"]
    weight = balance.amount if balance else 1.0
    
    # Cast vote with weight in metadata
    Vote(
        proposal=proposal,
        voter=voter,
        vote_choice=choice,
        metadata=f"weight:{weight}"
    )

# Tally with weights
def tally_weighted_votes(proposal_id: str):
    proposal = Proposal[proposal_id]
    votes = list(proposal.votes)
    
    yes_weight = sum(
        float(v.metadata.split(":")[1]) 
        for v in votes 
        if v.vote_choice == "yes" and "weight:" in v.metadata
    )
    
    total_weight = sum(
        float(v.metadata.split(":")[1])
        for v in votes
        if "weight:" in v.metadata
    )
    
    if total_weight > 0 and (yes_weight / total_weight) >= proposal.required_threshold:
        proposal.status = "approved"
```

---

### Quadratic Voting

```python
import math

def cast_quadratic_vote(voter_id: str, proposal_id: str, tokens: int, choice: str):
    """Quadratic voting: cost = votes²"""
    voter = User[voter_id]
    proposal = Proposal[proposal_id]
    
    # Calculate vote power
    votes = int(math.sqrt(tokens))
    cost = votes * votes
    
    # Deduct tokens
    balance = Balance[f"{voter_id}_VoteToken"]
    if balance.amount < cost:
        raise Exception("Insufficient vote tokens")
    
    balance.amount -= cost
    
    # Cast vote
    Vote(
        proposal=proposal,
        voter=voter,
        vote_choice=choice,
        metadata=f"votes:{votes},cost:{cost}"
    )
```

---

### Delegated Voting

```python
from ggg import User, Vote, Proposal

class VoteDelegate:
    """Delegate voting power to another user"""
    delegator = ManyToOne("User", "delegations_out")
    delegate = ManyToOne("User", "delegations_in")
    scope = String()  # 'all' or specific category

def vote_with_delegations(voter_id: str, proposal_id: str, choice: str):
    """Vote on behalf of self + delegators"""
    voter = User[voter_id]
    proposal = Proposal[proposal_id]
    
    # Count direct vote + delegated votes
    delegators = list(voter.delegations_in)
    vote_power = 1 + len(delegators)
    
    Vote(
        proposal=proposal,
        voter=voter,
        vote_choice=choice,
        metadata=f"power:{vote_power},delegates:{len(delegators)}"
    )
```

---

## Governance Codex Examples

### Tax Collection
```python
tax_codex = Codex(
    name="progressive_tax",
    code="""
from ggg import User, Balance, Transfer, Treasury

def collect_taxes():
    treasury = Treasury["main"]
    
    for user in User.instances():
        balance = Balance[f"{user.id}_RealmToken"]
        if not balance:
            continue
        
        # Progressive tax
        if balance.amount < 1000:
            tax_rate = 0.05
        elif balance.amount < 10000:
            tax_rate = 0.10
        else:
            tax_rate = 0.15
        
        tax = int(balance.amount * tax_rate)
        
        Transfer(
            id=f"tax_{user.id}_{datetime.now().timestamp()}",
            principal_from=user.id,
            principal_to="treasury",
            instrument="Realm Token",
            amount=tax,
            transfer_type="internal",
            status="completed"
        )
        
        balance.amount -= tax
        ic.print(f"Collected {tax} from {user.id}")

collect_taxes()
"""
)
```

### UBI Distribution
```python
ubi_codex = Codex(
    name="ubi_distribution",
    code="""
from ggg import Member, Balance, Transfer, Realm

def distribute_ubi():
    realm = Realm["1"]
    settings = eval(realm.settings)
    ubi_amount = settings.get("ubi_amount", 1000)
    
    for member in Member.instances():
        if not member.eligible_for_benefits:
            continue
        
        user = citizen.user
        balance = Balance[f"{user.id}_RealmToken"]
        
        if not balance:
            balance = Balance(
                id=f"{user.id}_RealmToken",
                user=user,
                instrument="Realm Token",
                amount=0
            )
        
        # Add UBI
        balance.amount += ubi_amount
        
        Transfer(
            id=f"ubi_{user.id}_{datetime.now().timestamp()}",
            principal_from="treasury",
            principal_to=user.id,
            instrument="Realm Token",
            amount=ubi_amount,
            transfer_type="internal",
            status="completed"
        )
        
        ic.print(f"Paid {ubi_amount} UBI to {user.id}")

distribute_ubi()
"""
)
```

---

## Complete Example: Tax Reform Proposal

```python
# 1. Submit proposal
proposal = Proposal(
    proposal_id="tax_reform_2024",
    title="Reduce Tax Rate to 10%",
    description="Lower tax burden to stimulate economic activity",
    proposer=User["alice_2024"],
    status="voting",
    voting_deadline=(datetime.now() + timedelta(days=7)).isoformat(),
    required_threshold=0.60
)

# 2. Members vote
Vote(proposal=proposal, voter=User["alice_2024"], vote_choice="yes")
Vote(proposal=proposal, voter=User["bob_2024"], vote_choice="yes")
Vote(proposal=proposal, voter=User["carol_2024"], vote_choice="no")

# 3. Automated tallying (scheduled task)
# Runs daily, checks deadline, updates status

# 4. Execution (if approved)
execution_code = """
from ggg import Realm

realm = Realm["1"]
settings = eval(realm.settings)
settings["tax_rate"] = 0.10
realm.settings = str(settings)

ic.print("✅ Tax rate updated to 10%")
"""
```

---

## CLI Integration

```bash
# Submit proposal from file
realms run --file submit_proposal.py

# Schedule vote tallying
realms run --file tally_votes.py --every 86400

# Monitor proposals
realms shell --file list_proposals.py
```

---

## See Also

- [Core Entities](./CORE_ENTITIES.md) - Proposal, Vote, Mandate entities
- [Task System](./TASK_ENTITY.md) - Automated governance
- [Multi-Step Tasks](./MULTI_STEP_TASKS_IMPLEMENTATION.md) - Complex workflows
- [API Reference](./API_REFERENCE.md) - Governance endpoints
