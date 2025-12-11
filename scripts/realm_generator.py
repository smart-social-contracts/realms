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
from typing import Dict, List, Any, Optional
import hashlib
import sys
import os
import shutil

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src/realm_backend'))

# Add the CLI directory to the Python path to access constants
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'cli'))

from realms.cli.constants import REALM_FOLDER
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
        self.logo = ""  # Logo path/URL for the realm
        
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
        # Note: Name must match the codex file name (without .py) for import to update it
        codex = Codex(
            name="satoshi_transfer_codex",
            description="Sends 1 satoshi every 60 seconds",
            code=""  # Will be populated when codex file is imported
        )
        
        # Create Task that references the codex
        task = Task(
            name="Satoshi Transfer Task",
            metadata=json.dumps({
                "description": "Automated satoshi transfer every 60 seconds",
                "codex_name": "satoshi_transfer_codex",
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
        # Note: manifest_data field removed from Realm to avoid Candid parsing issues during import
        # The manifest can be uploaded separately after deployment if needed
        manifest = self.get_codex_overrides_manifest()
        
        # Logo path - if set, points to /images/{logo_filename} served from frontend static folder
        logo_path = f"/images/{self.logo}" if self.logo else ""
        
        realm = Realm(
            id=self.realm_id,
            name=realm_name,
            description=f"Generated demo realm with {members} members and {organizations} organizations",
            logo=logo_path,
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
            }
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
    
    def generate_codex_files(self, output_dir: Path, demo_folder: Optional[str] = None) -> List[str]:
        """Copy Python codex files from examples/demo/realm_common folder"""
        codex_files = []
        
        # Get the path to the examples/demo/realm_common folder
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        
        # Always use realm_common for shared codex files
        examples_common_dir = repo_root / "examples" / "demo" / "realm_common"
        
        # List of codex files to copy (shared across all realms)
        demo_codex_files = [
            "adjustments.py",
            "tax_collection_codex.py",
            "social_benefits_codex.py",
            "governance_automation_codex.py",
            "user_registration_hook_codex.py",
            "satoshi_transfer_codex.py"
        ]
        
        # Copy each codex file from realm_common to output directory
        for codex_filename in demo_codex_files:
            source_file = examples_common_dir / codex_filename
            
            if source_file.exists():
                dest_file = output_dir / codex_filename
                shutil.copy2(source_file, dest_file)
                codex_files.append(str(dest_file))
                print(f"  Copied {codex_filename} from realm_common/")
            else:
                print(f"  Warning: {codex_filename} not found in {examples_common_dir}")
        
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
    parser.add_argument("--demo-folder", type=str, default=None, help="Demo folder name (e.g., realm1, realm2)")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate data
    generator = RealmGenerator(args.seed)
    
    # Define repo_root for later use
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Check if manifest already exists in output_dir (copied by create_command)
    output_manifest = output_dir / "manifest.json"
    
    if output_manifest.exists():
        # Manifest was already copied by create_command - just read it
        with open(output_manifest, 'r') as f:
            manifest_data = json.load(f)
        print(f"Using existing manifest from output directory")
        
        # Set logo on generator if specified in manifest
        logo_filename = manifest_data.get("logo", "")
        if logo_filename:
            logo_file = output_dir / logo_filename
            if logo_file.exists():
                generator.logo = logo_filename
                print(f"Using logo: {logo_filename}")
            else:
                print(f"Warning: Logo file {logo_filename} not found in output directory")
    else:
        # Fallback: Copy manifest from examples/demo (for backwards compatibility)
        if args.demo_folder:
            demo_base_dir = repo_root / "examples" / "demo" / args.demo_folder
        else:
            demo_base_dir = repo_root / "examples" / "demo"
        
        demo_manifest = demo_base_dir / "manifest.json"
        
        if demo_manifest.exists():
            with open(demo_manifest, 'r') as f:
                manifest_data = json.load(f)
            
            manifest_data["name"] = args.realm_name
            
            with open(output_manifest, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            print(f"Copied manifest from {demo_base_dir}")
            
            # Copy logo if it exists
            logo_filename = manifest_data.get("logo", "")
            if logo_filename:
                logo_source = demo_base_dir / logo_filename
                if logo_source.exists():
                    shutil.copy2(logo_source, output_dir / logo_filename)
                    generator.logo = logo_filename
                    print(f"Copied logo: {logo_filename}")
        else:
            # Generate minimal manifest
            manifest_data = generator.get_codex_overrides_manifest()
            manifest_data["name"] = args.realm_name
            with open(output_manifest, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            print(f"Generated manifest saved to: {output_manifest}")
    
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
    codex_files = generator.generate_codex_files(output_dir, args.demo_folder)
    print(f"\nGenerated {len(codex_files)} codex files:")
    for file in codex_files:
        print(f"- {file}")
    
    print(f"\nSeed used: {generator.seed} (use this seed to reproduce the same data)")
    
    # Copy source code folders to output directory
    print("\nCopying source code folders...")
    
    # Define folders to copy
    folders_to_copy = [
        ("src/realm_backend", "src/realm_backend"),
        ("src/realm_frontend", "src/realm_frontend"),
        ("extensions", "extensions"),
        ("scripts", "scripts"),
    ]
    
    for src_rel, dest_rel in folders_to_copy:
        src_folder = repo_root / src_rel
        dest_folder = output_dir / dest_rel
        
        if src_folder.exists():
            # Create parent directories if needed
            dest_folder.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the folder
            if dest_folder.exists():
                shutil.rmtree(dest_folder)
            shutil.copytree(src_folder, dest_folder)
            print(f"  Copied {src_rel} -> {dest_rel}")
        else:
            print(f"  Warning: Source folder {src_rel} not found at {src_folder}")
    
    print("\nSource code copying complete!")

if __name__ == "__main__":
    main()
