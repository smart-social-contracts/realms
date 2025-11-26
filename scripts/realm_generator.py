#!/usr/bin/env python3
"""
Realm Generator Script

Generates realistic demo data for Realms including:
- JSON files with entity data (users, organizations, transfers, etc.)
- Python codex files with governance automation scripts

Usage:
    python realm_generator.py --members 100 --organizations 10 --transactions 500 --seed 12345
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import hashlib
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src/realm_backend'))

# Add the CLI directory to the Python path to access constants
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))

from realms_cli.constants import REALM_FOLDER
from ggg import (
    UserProfile,
    Profiles,
    User,
    Treasury,
    Realm,
    Instrument,
    Transfer,
    Organization,
    Member,
    Human,
    Dispute,
    Mandate,
    Identity,
    Proposal,
    Codex,
    Task,
    TaskSchedule
)


# Realistic data pools
FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Helen",
    "Ivan", "Julia", "Kevin", "Laura", "Michael", "Nina", "Oliver", "Patricia",
    "Quinn", "Rachel", "Samuel", "Tina", "Ulrich", "Victoria", "William", "Xara",
    "Yuki", "Zoe", "Adrian", "Bella", "Carlos", "Delia", "Erik", "Fatima"
]

LAST_NAMES = [
    "Anderson", "Brown", "Clark", "Davis", "Evans", "Fisher", "Garcia", "Harris",
    "Johnson", "King", "Lee", "Miller", "Nelson", "O'Connor", "Parker", "Quinn",
    "Rodriguez", "Smith", "Taylor", "Underwood", "Valdez", "Wilson", "Xavier",
    "Young", "Zhang", "Adams", "Baker", "Cooper", "Duncan", "Ellis", "Foster"
]

ORGANIZATIONS = [
    "Digital Services Corp", "Green Energy Solutions", "Healthcare Partners",
    "Education Foundation", "Transport Authority", "Housing Development Co",
    "Financial Services Inc", "Technology Innovations", "Agricultural Cooperative",
    "Environmental Protection Agency", "Cultural Heritage Foundation",
    "Community Development Trust", "Infrastructure Management", "Social Services Org"
]

INSTRUMENTS = [
    {"name": "Bitcoin", "symbol": "BTC"},
    {"name": "Ethereum", "symbol": "ETH"},
    {"name": "Realm Token", "symbol": "RLM"},
    {"name": "Governance Token", "symbol": "GOV"},
    {"name": "Utility Token", "symbol": "UTL"},
    {"name": "Service Credit", "symbol": "SVC"}
]

MANDATE_TYPES = [
    {"name": "Tax Collection", "description": "Automated tax assessment and collection"},
    {"name": "Social Benefits", "description": "Distribution of social welfare benefits"},
    {"name": "License Management", "description": "Processing and renewal of licenses"},
    {"name": "Land Registry", "description": "Property registration and transfers"},
    {"name": "Voting System", "description": "Democratic voting and governance"},
    {"name": "Healthcare Services", "description": "Public healthcare administration"}
]

class RealmGenerator:
    def __init__(self, seed: int = random.randint(1, 1000000)):
        self.seed = seed
        random.seed(self.seed)
        self.generated_data = {}
        self.realm_id = "0"
        
    def generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID with optional prefix"""
        return f"{prefix}{uuid.uuid4().hex[:8]}"
    
    def generate_principal_id(self) -> str:
        """Generate a realistic principal ID"""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return ''.join(random.choices(chars, k=27)) + "-cai"
    
    def generate_users(self, count: int) -> List[User]:
        """Generate realistic user data"""
        users = []
        
        # Always create system user first
        system_user = User(
            id="system",
            user_profile=Profiles.ADMIN["name"]
        )
        
        users.append(system_user)
        
        for i in range(count):
            
            user = User(
                id=f"user_{i:03d}",
                profile_picture_url=f"https://api.dicebear.com/7.x/personas/svg?seed={random.randint(1, 1000000)}",
                user_profile=Profiles.MEMBER["name"]
            )   
            users.append(user)
            
        return users
    
    def generate_humans(self, users: List[User]) -> List[Human]:
        """Generate human data linked to users"""
        humans = []
        
        for user in users[1:]:  # Skip system user
            human = Human(
                name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                date_of_birth=(datetime.now() - timedelta(days=random.randint(18*365, 80*365))).strftime("%Y-%m-%d"),
                user_id=user.id
            )
            
            humans.append(human)
        
        return humans

    def generate_identities(self, users: List[User]) -> List[Identity]:
        """Generate identity data linked to users"""
        identities = []
        
        for user in users:
            identity = Identity(
                user_id=user.id,
                metadata=f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:8]}"
            )
            
            identities.append(identity)
        
        return identities
    
    def generate_members(self, users: List[User]) -> List[Member]:
        """Generate member data linked to users"""
        members = []
        
        for user in users:
            member = Member(
                id=self.generate_id("mem_"),
                user=user,    
                residence_permit=random.choice(["valid", "expired", "pending"]),
                tax_compliance=random.choice(["compliant", "delinquent", "under_review"]),
                identity_verification=random.choice(["verified", "pending", "rejected"]),
                voting_eligibility=random.choice(["eligible", "ineligible", "suspended"]),
                public_benefits_eligibility=random.choice(["eligible", "ineligible", "conditional"]),
                criminal_record=random.choice(["clean", "minor_offenses", "major_offenses"]) 
            )
            members.append(member)
            
        return members
    
    def generate_organizations(self, count: int) -> List[Organization]:
        """Generate organization data"""
        organizations = []
        
        for i in range(count):
            org_name = random.choice(ORGANIZATIONS)
            org = Organization(
                name=f"{org_name} #{i+1:03d}"
            )
            organizations.append(org)
            
        return organizations
    
    def generate_instruments(self) -> List[Instrument]:
        """Generate financial instruments"""
        instruments = []
        
        for instrument in INSTRUMENTS:
            inst = Instrument(
                name=instrument["name"],
                principal_id=self.generate_principal_id()
            )
            instruments.append(inst)
            
        return instruments
    
    def generate_transfers(self, users: List[User], instruments: List[Instrument], count: int) -> List[Transfer]:
        """Generate transfer transactions"""
        transfers = []
        
        for i in range(count):
            from_user = random.choice(users)
            print('from_user', from_user)

            print('users', users)

            to_user = random.choice([u for u in users if u.id != from_user.id])
            instrument = random.choice(instruments)
            
            transfer = Transfer(
                id=self.generate_id("tr_"),
                principal_from=from_user.id,
                principal_to=to_user.id,
                instrument=instrument.name,
                amount=random.randint(1, 10000),
                timestamp=datetime.now().isoformat(),
                transfer_type="internal",
                status="completed"
            )
            transfers.append(transfer)
            
        return transfers
    
    def generate_disputes(self, count: int) -> List[Dispute]:
        """Generate dispute cases"""
        disputes = []
        statuses = ["open", "investigating", "resolved", "closed", "appealed"]
        
        for i in range(count):
            dispute = Dispute(
                status=random.choice(statuses)
            )
            disputes.append(dispute)
            
        return disputes
    
    def generate_mandates(self) -> List[Mandate]:
        """Generate government mandates"""
        mandates = []
        
        for mandate_type in MANDATE_TYPES:
            mandate = Mandate(
                name=mandate_type["name"]
            )
            mandates.append(mandate)
            
        return mandates
    
    def generate_user_registration_hook_codex(self) -> Codex:
        """Generate a codex for user registration hook
        
        Returns: Codex entity
        Note: Codex code will be loaded from the generated file during upload
        Note: entity_method_overrides configuration is stored separately in a Storage entry
        """
        codex = Codex(
            name="user_registration_hook_codex",
            description="Custom user registration hook",
            code=""  # Will be populated when codex file is imported
        )
        return codex
    
    def get_codex_overrides_manifest(self) -> dict:
        """Get entity method overrides configuration for Realm manifest
        
        Returns: Dict containing entity_method_overrides
        """
        return {
            "entity_method_overrides": [
                {
                    "entity": "User",
                    "method": "user_register_posthook",
                    "type": "staticmethod",
                    "implementation": "Codex.user_registration_hook_codex.user_register_posthook",
                    "description": "Custom post-registration hook for new users"
                }
            ]
        }
    
    def generate_scheduled_task(self) -> tuple:
        """Generate a scheduled task for the satoshi transfer codex
        
        Returns tuple of (codex, task, task_schedule)
        Note: Codex code will be loaded from the generated file during upload
        """
        import json
        from datetime import datetime
        
        # Create Codex entity (code will be set during import)
        codex = Codex(
            name="Satoshi Transfer",
            description="Sends 1 satoshi every 60 seconds",
            code=""  # Will be populated when codex file is imported
        )
        
        # Create Task that references the codex
        task = Task(
            name="Satoshi Transfer Task",
            metadata=json.dumps({
                "description": "Automated satoshi transfer every 60 seconds",
                "codex_name": "Satoshi Transfer",
                "target_principal": "64fpo-jgpms-fpewi-hrskb-f3n6u-3z5fy-bv25f-zxjzg-q5m55-xmfpq-hqe",
                "amount": 1
            })
        )
        
        # Create TaskSchedule to run every 60 seconds
        task_schedule = TaskSchedule(
            name="Satoshi Transfer Schedule",
            task=task,
            repeat_every=60,  # Run every 60 seconds
            run_at=0,  # Start immediately
            last_run_at=0,  # Not run yet
            disabled=False  # Enabled by default
        )
        
        return (codex, task, task_schedule)
    
    def generate_treasury_data(self, realm: Realm) -> Treasury:
        """Generate treasury data matching Treasury entity schema"""
        # Match the Treasury entity structure exactly:
        # - name: String(min_length=2, max_length=256) 
        # - vault_principal_id: String(max_length=64)
        # - realm: OneToOne("Realm", "treasury")
        # - TimestampedMixin adds created_at, updated_at

        print("Realm:", type(realm))
        
        treasury_data = Treasury(
            name=f"{realm.name} Treasury",
            vault_principal_id=None,  # Will be set during deployment after vault canister creation
            realm=realm,  # Reference to current realm (realm[0] by default)
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        return treasury_data

    def generate_realm_metadata(self, realm_name: str, members: int, organizations: int) -> Realm:
        """Generate realm metadata"""
        import json
        
        # Get entity method overrides configuration
        manifest = self.get_codex_overrides_manifest()
        
        realm = Realm(
            id=self.realm_id,
            name=realm_name,
            description=f"Generated demo realm with {members} members and {organizations} organizations",
            created_at=datetime.now().isoformat(),
            status="active",
            governance_type="democratic",
            population=members,
            organization_count=organizations,
            settings={
                "voting_period_days": 7,    
                "proposal_threshold": 0.1,
                "quorum_percentage": 0.3,
                "tax_rate": 0.15,
                "ubi_amount": 1000
            },
            manifest_data=json.dumps(manifest)
        )
        
        return realm

    def generate_minimal_realm_data(self, realm_name: str = "Generated Demo Realm") -> List:
        """Generate minimal realm data.
        
        Note: Foundational objects (Realm, Treasury, UserProfiles, System User, Identity)
        are now auto-created by the backend during canister initialization.
        This returns an empty list for backwards compatibility.
        """
        print(f"Minimal realm data generation...")
        print("Note: Foundational objects are auto-created by the backend canister.")
        print("No additional data needed for minimal realm.")
        
        # Return empty list - foundational objects are created by backend
        return []
    
    def generate_realm_data(self, **params) -> List:
        """Generate additional realm data (users, organizations, etc.).
        
        Includes Realm with manifest_data containing entity method overrides.
        Other foundational objects (Treasury, UserProfiles, System User, Identity)
        are auto-created by the backend during canister initialization.
        """
        print(f"Generating additional realm data with seed: {self.seed}")
        print("Note: Some foundational objects (Treasury, UserProfiles, System User) are auto-created by backend.")
        
        # Generate realm with manifest_data
        realm = self.generate_realm_metadata(
            realm_name=params.get('realm_name', 'Generated Demo Realm'),
            members=params.get('members', 50),
            organizations=params.get('organizations', 5)
        )
        
        # Generate additional entities
        users = self.generate_users(params.get('members', 50))
        humans = self.generate_humans(users)
        identities = self.generate_identities(users)
        members = self.generate_members(users)
        organizations = self.generate_organizations(params.get('organizations', 5))
        instruments = self.generate_instruments()
        transfers = self.generate_transfers(users, instruments, params.get('transactions', 100))
        disputes = self.generate_disputes(params.get('disputes', 10))
        mandates = self.generate_mandates()
        
        # Generate scheduled task for satoshi transfer
        codex, task, task_schedule = self.generate_scheduled_task()
        
        # Generate user registration hook codex
        user_reg_hook_codex = self.generate_user_registration_hook_codex()
        
        # Return Realm first, then additional data
        ret = [realm]
        ret += users
        ret += identities
        ret += humans
        ret += members
        ret += organizations
        ret += instruments
        ret += transfers
        ret += disputes
        ret += mandates
        ret.append(codex)
        ret.append(task)
        ret.append(task_schedule)
        ret.append(user_reg_hook_codex)
        return ret
    
    def generate_codex_files(self, output_dir: Path) -> List[str]:
        """Generate Python codex files"""
        codex_files = []
        
        # Tax Collection Codex
        tax_codex = '''"""
Tax Collection Automation Codex
Automatically calculates and processes tax payments for members
"""

from ggg import User, Transfer, Treasury, Instrument
from datetime import datetime, timedelta
import json

def calculate_tax_for_user(user_id: str, tax_year: int = None) -> dict:
    """Calculate tax owed by a user for a given year"""
    if tax_year is None:
        tax_year = datetime.now().year
    
    # Get user's transfers for the tax year
    user = User.get(user_id)
    if not user:
        return {"error": "User not found"}
    
    # Calculate income from transfers received
    income_transfers = [t for t in user.transfers_to if 
                       datetime.fromisoformat(t.created_at).year == tax_year]
    
    total_income = sum(t.amount for t in income_transfers)
    
    # Progressive tax calculation
    if total_income <= 10000:
        tax_rate = 0.10
    elif total_income <= 50000:
        tax_rate = 0.20
    else:
        tax_rate = 0.30
    
    tax_owed = int(total_income * tax_rate)
    
    return {
        "user_id": user_id,
        "tax_year": tax_year,
        "total_income": total_income,
        "tax_rate": tax_rate,
        "tax_owed": tax_owed,
        "calculated_at": datetime.now().isoformat()
    }

def process_tax_collection():
    """Main tax collection process"""
    results = []
    
    # Get all users
    users = User.get_all()
    
    for user in users:
        if user.id == "system":
            continue
            
        tax_info = calculate_tax_for_user(user.id)
        
        if "error" not in tax_info and tax_info["tax_owed"] > 0:
            # Create tax payment transfer
            tax_instrument = Instrument.get_by_name("Realm Token")
            if tax_instrument:
                transfer = Transfer(
                    from_user=user,
                    to_user=User.get("system"),
                    instrument=tax_instrument,
                    amount=tax_info["tax_owed"]
                )
                results.append({
                    "user_id": user.id,
                    "tax_collected": tax_info["tax_owed"],
                    "status": "collected"
                })
    
    return results

# Main execution
if __name__ == "__main__":
    results = process_tax_collection()
    print(f"Tax collection completed: {len(results)} payments processed")
'''
        
        tax_file = output_dir / "tax_collection_codex.py"
        tax_file.write_text(tax_codex)
        codex_files.append(str(tax_file))
        
        # Social Benefits Codex
        benefits_codex = '''"""
Social Benefits Distribution Codex
Automatically distributes social benefits to eligible members
"""

from ggg import User, Member, Transfer, Treasury, Instrument
from datetime import datetime
import json

def check_benefit_eligibility(member_id: str) -> dict:
    """Check if a member is eligible for social benefits"""
    member = Member.get(member_id)
    if not member:
        return {"eligible": False, "reason": "Member not found"}
    
    # Eligibility criteria
    criteria = {
        "residence_permit": member.residence_permit == "valid",
        "tax_compliance": member.tax_compliance in ["compliant", "under_review"],
        "identity_verification": member.identity_verification == "verified",
        "benefits_eligibility": member.public_benefits_eligibility == "eligible"
    }
    
    eligible = all(criteria.values())
    
    return {
        "member_id": member_id,
        "eligible": eligible,
        "criteria_met": criteria,
        "checked_at": datetime.now().isoformat()
    }

def calculate_benefit_amount(member_id: str) -> int:
    """Calculate benefit amount based on member status"""
    member = Member.get(member_id)
    if not member:
        return 0
    
    # Base benefit amount
    base_amount = 500
    
    # Adjustments based on status
    if member.criminal_record == "clean":
        base_amount += 100
    
    if member.voting_eligibility == "eligible":
        base_amount += 50
    
    return base_amount

def distribute_social_benefits():
    """Main social benefits distribution process"""
    results = []
    
    # Get all members
    members = Member.get_all()
    
    for member in members:
        eligibility = check_benefit_eligibility(member.id)
        
        if eligibility["eligible"]:
            benefit_amount = calculate_benefit_amount(member.id)
            
            # Create benefit transfer
            benefit_instrument = Instrument.get_by_name("Service Credit")
            system_user = User.get("system")
            
            if benefit_instrument and system_user and member.user:
                transfer = Transfer(
                    from_user=system_user,
                    to_user=member.user,
                    instrument=benefit_instrument,
                    amount=benefit_amount
                )
                
                results.append({
                    "member_id": member.id,
                    "benefit_amount": benefit_amount,
                    "status": "distributed"
                })
    
    return results

# Main execution
if __name__ == "__main__":
    results = distribute_social_benefits()
    print(f"Benefits distribution completed: {len(results)} payments processed")
'''
        
        benefits_file = output_dir / "social_benefits_codex.py"
        benefits_file.write_text(benefits_codex)
        codex_files.append(str(benefits_file))
        
        # Governance Automation Codex
        governance_codex = '''"""
Governance Automation Codex
Processes proposals and votes for democratic governance
"""

from ggg import Proposal, Vote, User
from datetime import datetime, timedelta
import json

def create_sample_proposal(title: str, description: str) -> str:
    """Create a new governance proposal"""
    proposal = Proposal(
        metadata=json.dumps({
            "title": title,
            "description": description,
            "status": "active",
            "created_by": "system",
            "voting_deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "votes_for": 0,
            "votes_against": 0,
            "total_votes": 0
        })
    )
    
    return proposal.id

def process_votes():
    """Process all active proposals and tally votes"""
    results = []
    
    # Get all proposals
    proposals = Proposal.get_all()
    
    for proposal in proposals:
        metadata = json.loads(proposal.metadata)
        
        if metadata.get("status") == "active":
            # Check if voting deadline has passed
            deadline = datetime.fromisoformat(metadata["voting_deadline"])
            
            if datetime.now() > deadline:
                # Tally votes and close proposal
                votes_for = metadata.get("votes_for", 0)
                votes_against = metadata.get("votes_against", 0)
                total_votes = votes_for + votes_against
                
                # Determine outcome
                if total_votes > 0:
                    if votes_for > votes_against:
                        status = "passed"
                    else:
                        status = "rejected"
                else:
                    status = "no_votes"
                
                # Update proposal
                metadata["status"] = status
                metadata["final_tally"] = {
                    "votes_for": votes_for,
                    "votes_against": votes_against,
                    "total_votes": total_votes,
                    "closed_at": datetime.now().isoformat()
                }
                
                proposal.metadata = json.dumps(metadata)
                
                results.append({
                    "proposal_id": proposal.id,
                    "title": metadata["title"],
                    "status": status,
                    "votes_for": votes_for,
                    "votes_against": votes_against
                })
    
    return results

def create_sample_proposals():
    """Create sample governance proposals"""
    proposals = [
        {
            "title": "Increase Social Benefits by 10%",
            "description": "Proposal to increase monthly social benefits for all eligible members by 10% to account for inflation."
        },
        {
            "title": "Implement Green Energy Tax Credits",
            "description": "Provide tax credits for members and organizations investing in renewable energy infrastructure."
        },
        {
            "title": "Digital Identity Verification System",
            "description": "Implement a new digital identity verification system to streamline government services."
        }
    ]
    
    created_proposals = []
    for proposal in proposals:
        proposal_id = create_sample_proposal(proposal["title"], proposal["description"])
        created_proposals.append(proposal_id)
    
    return created_proposals

# Main execution
if __name__ == "__main__":
    # Create sample proposals
    proposals = create_sample_proposals()
    print(f"Created {len(proposals)} sample proposals")
    
    # Process votes
    results = process_votes()
    print(f"Processed {len(results)} proposals")
'''
        
        governance_file = output_dir / "governance_automation_codex.py"
        governance_file.write_text(governance_codex)
        codex_files.append(str(governance_file))
        
        # User Registration Hook Codex
        registration_codex = '''"""
User Registration Hook Codex
Overrides user_register_posthook to add custom logic after user registration.
Creates a 1 ckBTC invoice expiring in 5 minutes for new users.
"""

from kybra import ic
from ggg import Invoice
from datetime import datetime, timedelta

def user_register_posthook(user):
    """Custom user registration hook - creates welcome invoice."""
    try:
        # Calculate expiry time (5 minutes from now)
        expiry_time = datetime.now() + timedelta(minutes=5)
        due_date = expiry_time.isoformat()
        
        # Create 1 ckBTC invoice for the new user
        # Invoice ID is auto-generated and used to derive a unique subaccount
        invoice = Invoice(
            amount=1.0,  # 1 ckBTC
            currency="ckBTC",
            due_date=due_date,
            status="Pending",
            user=user,
            metadata="Welcome bonus - 1 ckBTC invoice"
        )
        
        # Get the deposit address info
        vault_principal = ic.id().to_str()
        subaccount_hex = invoice.get_subaccount_hex()
        
        ic.print(f"✅ Created welcome invoice {invoice.id} for user {user.id}")
        ic.print(f"   Deposit to: {vault_principal} (subaccount: {subaccount_hex[:16]}...)")
        ic.print(f"   Amount: 1 ckBTC, expires in 5 minutes")
        
    except Exception as e:
        ic.print(f"❌ Error creating invoice: {e}")
    
    return
'''
        
        registration_file = output_dir / "user_registration_hook_codex.py"
        registration_file.write_text(registration_codex)
        codex_files.append(str(registration_file))
        
        return codex_files

def main():
    parser = argparse.ArgumentParser(description="Generate realistic realm demo data")
    parser.add_argument("--members", type=int, default=50, help="Number of members to generate")
    parser.add_argument("--organizations", type=int, default=5, help="Number of organizations to generate")
    parser.add_argument("--transactions", type=int, default=100, help="Number of transactions to generate")
    parser.add_argument("--disputes", type=int, default=10, help="Number of disputes to generate")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible generation")
    parser.add_argument("--output-dir", type=str, default=REALM_FOLDER, help="Output directory")
    parser.add_argument("--realm-name", type=str, default="Generated Demo Realm", help="Name of the realm")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate data
    generator = RealmGenerator(args.seed)
    
    # Generate and write manifest.json with entity method overrides
    manifest_data = generator.get_codex_overrides_manifest()
    manifest_data["name"] = args.realm_name
    
    manifest_file = output_dir / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Generated realm manifest saved to: {manifest_file}")
    
    realm_data = generator.generate_realm_data(
        members=args.members,
        organizations=args.organizations,
        transactions=args.transactions,
        disputes=args.disputes,
        realm_name=args.realm_name
    )
    
    # Save main realm data JSON

    json_file = output_dir / "realm_data.json"

    # print('realm_data', realm_data)
    # for obj in realm_data:
    #     print(obj.serialize())
    #     print(obj.__dict__)
    
    realm_data = [obj.serialize() for obj in realm_data]
    
    with open(json_file, 'w') as f:
        json.dump(realm_data, f, indent=2)
    
    print(f"Generated realm data saved to: {json_file}")
    
    # Generate codex files only for full realm generation
    codex_files = generator.generate_codex_files(output_dir)
    print(f"\nGenerated {len(codex_files)} codex files:")
    for file in codex_files:
        print(f"- {file}")
    
    print(f"\nSeed used: {generator.seed} (use this seed to reproduce the same data)")

if __name__ == "__main__":
    main()