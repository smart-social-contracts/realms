#!/usr/bin/env python3
"""
Realm Generator Script

Generates realistic demo data for Realms including:
- JSON files with entity data (users, organizations, transfers, etc.)
- Python codex files with governance automation scripts

Usage:
    python realm_generator.py --citizens 100 --organizations 10 --transactions 500 --seed 12345
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import hashlib

# Import GGG entities
try:
    from src.realm_backend.ggg.user_profile import UserProfile, Profiles
    from src.realm_backend.ggg.user import User
    from src.realm_backend.ggg.treasury import Treasury
except ImportError:
    # Fallback for when running outside the main project
    UserProfile = None
    Profiles = None
    User = None
    Treasury = None

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
    def __init__(self, seed: int = None):
        self.seed = seed or random.randint(1, 1000000)
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
    
    def generate_users(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic user data"""
        users = []
        
        # Always create system user first
        system_user = {
            "class": "User",
            "data": {
                "id": "system",
                "profile_picture_url": ""
            }
        }
        users.append(system_user)
        
        for i in range(count):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            
            user = {
                "class": "User",
                "data": {
                    "id": f"{first_name.lower()}_{last_name.lower()}_{i:03d}",
                    "profile_picture_url": f"https://api.dicebear.com/7.x/personas/svg?seed={first_name}{last_name}"
                }
            }
            users.append(user)
            
        return users
    
    def generate_humans(self, users: List[Dict]) -> List[Dict[str, Any]]:
        """Generate human data linked to users"""
        humans = []
        
        for user in users[1:]:  # Skip system user
            print(user)
            first_name = user["data"]["id"].split("_")[0].title()
            last_name = user["data"]["id"].split("_")[1].title()
            
            human = {
                "class": "Human",
                "data": {
                    "name": f"{first_name} {last_name}",
                    "date_of_birth": (datetime.now() - timedelta(days=random.randint(18*365, 80*365))).strftime("%Y-%m-%d"),
                    "user_id": user["data"]["id"]
                }
            }
            humans.append(human)
            
        return humans
    
    def generate_citizens(self, humans: List[Dict]) -> List[Dict[str, Any]]:
        """Generate citizen data linked to humans"""
        citizens = []
        
        for human in humans:
            citizen = {
                "class": "Citizen",
                "data": {
                    "id": self.generate_id("cit_"),
                    "user_id": human["data"]["user_id"],    
                    "residence_permit": random.choice(["valid", "expired", "pending"]),
                    "tax_compliance": random.choice(["compliant", "delinquent", "under_review"]),
                    "identity_verification": random.choice(["verified", "pending", "rejected"]),
                    "voting_eligibility": random.choice(["eligible", "ineligible", "suspended"]),
                    "public_benefits_eligibility": random.choice(["eligible", "ineligible", "conditional"]),
                    "criminal_record": random.choice(["clean", "minor_offenses", "major_offenses"]) 
                }
            }
            citizens.append(citizen)
            
        return citizens
    
    def generate_organizations(self, count: int) -> List[Dict[str, Any]]:
        """Generate organization data"""
        organizations = []
        
        for i in range(count):
            org_name = random.choice(ORGANIZATIONS)
            org = {
                "class": "Organization",
                "data": {
                    "name": f"{org_name} #{i+1:03d}"
                }
            }
            organizations.append(org)
            
        return organizations
    
    def generate_instruments(self) -> List[Dict[str, Any]]:
        """Generate financial instruments"""
        instruments = []
        
        for instrument in INSTRUMENTS:
            inst = {
                "class": "Instrument",
                "data": {
                    "name": instrument["name"],
                    "principal_id": self.generate_principal_id()
                }
            }
            instruments.append(inst)
            
        return instruments
    
    def generate_transfers(self, users: List[Dict], instruments: List[Dict], count: int) -> List[Dict[str, Any]]:
        """Generate transfer transactions"""
        transfers = []
        
        for i in range(count):
            from_user = random.choice(users)
            print('from_user', from_user)

            print('users', users)

            to_user = random.choice([u for u in users if u["data"]["id"] != from_user["data"]["id"]])
            instrument = random.choice(instruments)
            
            transfer = {
                "class": "Transfer",
                "data": {
                    "from_user": from_user["data"]["id"],
                    "to_user": to_user["data"]["id"],
                    "instrument": instrument["data"]["name"],
                    "amount": random.randint(1, 10000)
                }
            }
            transfers.append(transfer)
            
        return transfers
    
    def generate_disputes(self, count: int) -> List[Dict[str, Any]]:
        """Generate dispute cases"""
        disputes = []
        statuses = ["open", "investigating", "resolved", "closed", "appealed"]
        
        for i in range(count):
            dispute = {
                "class": "Dispute",
                "data": {
                    "status": random.choice(statuses)
                }
            }
            disputes.append(dispute)
            
        return disputes
    
    def generate_mandates(self) -> List[Dict[str, Any]]:
        """Generate government mandates"""
        mandates = []
        
        for mandate_type in MANDATE_TYPES:
            mandate = {
                "class": "Mandate",
                "data": {
                    "name": mandate_type["name"]
                }
            }
            mandates.append(mandate)
            
        return mandates
    
    def generate_treasury_data(self, realm_name: str) -> Dict[str, Any]:
        """Generate treasury data matching Treasury entity schema"""
        # Match the Treasury entity structure exactly:
        # - name: String(min_length=2, max_length=256) 
        # - vault_principal_id: String(max_length=64)
        # - realm: OneToOne("Realm", "treasury")
        # - TimestampedMixin adds created_at, updated_at
        
        treasury_data = {
            "class": "Treasury",
            "data": {
                "name": f"{realm_name} Treasury",
                "vault_principal_id": None,  # Will be set during deployment after vault canister creation
                "realm": "0",  # Reference to current realm (realm[0] by default)
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }
        
        return treasury_data

    def generate_realm_metadata(self, realm_name: str, citizens: int, organizations: int) -> Dict[str, Any]:
        """Generate realm metadata"""
        realm_data = {
            "id": self.realm_id,
            "name": realm_name,
            "description": f"Generated demo realm with {citizens} citizens and {organizations} organizations",
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "governance_type": "democratic",
            "population": citizens,
            "organization_count": organizations,
            "settings": {
                "voting_period_days": 7,
                "proposal_threshold": 0.1,
                "quorum_percentage": 0.3,
                "tax_rate": 0.15,
                "ubi_amount": 1000
            }
        }
        
        return {
            "class": "Realm",
            "data": realm_data
        }

    def generate_realm_data(self, **params) -> Dict[str, Any]:
        """Generate complete realm data"""
        print(f"Generating realm data with seed: {self.seed}")
        
        # Generate entities
        users = self.generate_users(params.get('citizens', 50))
        humans = self.generate_humans(users)
        citizens = self.generate_citizens(humans)
        organizations = self.generate_organizations(params.get('organizations', 5))
        instruments = self.generate_instruments()
        transfers = self.generate_transfers(users, instruments, params.get('transactions', 100))
        disputes = self.generate_disputes(params.get('disputes', 10))
        mandates = self.generate_mandates()
        
        # Create user profiles (with fallback for when GGG classes unavailable)
        if UserProfile and Profiles:
            user_profile_admin = UserProfile(
                name=Profiles.ADMIN[0],
                allowed_to=",".join(Profiles.ADMIN[1]),
                description="Admin user profile",
            )

            user_profile_member = UserProfile(
                name=Profiles.MEMBER[0],
                allowed_to=",".join(Profiles.MEMBER[1]),
                description="Member user profile",
            )
            
            user_profiles = [user_profile_admin, user_profile_member]
        else:
            # Fallback data structure when GGG classes aren't available
            user_profiles = [
                {
                    "class": "UserProfile",
                    "data": {
                        "name": "admin",
                        "allowed_to": "all",
                        "description": "Admin user profile"
                    }
                },
                {
                    "class": "UserProfile",
                    "data": {
                        "name": "member", 
                        "allowed_to": "",
                        "description": "Member user profile"
                    }
                }
            ]

        # Create a system user to represent the realm in transfers
        if User and user_profiles:
            system_user = {
                "class": "User",
                "data": {
                    "name": "system",
                    "profiles": [user_profiles[0]]
                }
            }
        else:
            system_user = {
                "class": "User",
                "data": {
                    "name": "system",
                    "profiles": ["admin"]
                }
            }

        # Create realm metadata
        realm = self.generate_realm_metadata(params.get('realm_name', 'Generated Demo Realm'), len(users), len(organizations))
        
        # Create the Treasury
        treasury = self.generate_treasury_data(params.get('realm_name', 'Generated Demo Realm'))
        
        ret = []
        ret += [realm] 
        ret += [treasury]
        ret += user_profiles 
        ret += [system_user]
        ret += users
        ret += humans
        ret += citizens
        ret += organizations
        ret += instruments
        ret += transfers
        ret += disputes
        ret += mandates
        return ret
    
    def generate_codex_files(self, output_dir: Path) -> List[str]:
        """Generate Python codex files"""
        codex_files = []
        
        # Tax Collection Codex
        tax_codex = '''"""
Tax Collection Automation Codex
Automatically calculates and processes tax payments for citizens
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
Automatically distributes social benefits to eligible citizens
"""

from ggg import User, Citizen, Transfer, Treasury, Instrument
from datetime import datetime
import json

def check_benefit_eligibility(citizen_id: str) -> dict:
    """Check if a citizen is eligible for social benefits"""
    citizen = Citizen.get(citizen_id)
    if not citizen:
        return {"eligible": False, "reason": "Citizen not found"}
    
    # Eligibility criteria
    criteria = {
        "residence_permit": citizen.residence_permit == "valid",
        "tax_compliance": citizen.tax_compliance in ["compliant", "under_review"],
        "identity_verification": citizen.identity_verification == "verified",
        "benefits_eligibility": citizen.public_benefits_eligibility == "eligible"
    }
    
    eligible = all(criteria.values())
    
    return {
        "citizen_id": citizen_id,
        "eligible": eligible,
        "criteria_met": criteria,
        "checked_at": datetime.now().isoformat()
    }

def calculate_benefit_amount(citizen_id: str) -> int:
    """Calculate benefit amount based on citizen status"""
    citizen = Citizen.get(citizen_id)
    if not citizen:
        return 0
    
    # Base benefit amount
    base_amount = 500
    
    # Adjustments based on status
    if citizen.criminal_record == "clean":
        base_amount += 100
    
    if citizen.voting_eligibility == "eligible":
        base_amount += 50
    
    return base_amount

def distribute_social_benefits():
    """Main social benefits distribution process"""
    results = []
    
    # Get all citizens
    citizens = Citizen.get_all()
    
    for citizen in citizens:
        eligibility = check_benefit_eligibility(citizen.id)
        
        if eligibility["eligible"]:
            benefit_amount = calculate_benefit_amount(citizen.id)
            
            # Create benefit transfer
            benefit_instrument = Instrument.get_by_name("Service Credit")
            system_user = User.get("system")
            
            if benefit_instrument and system_user and citizen.user:
                transfer = Transfer(
                    from_user=system_user,
                    to_user=citizen.user,
                    instrument=benefit_instrument,
                    amount=benefit_amount
                )
                
                results.append({
                    "citizen_id": citizen.id,
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
            "description": "Proposal to increase monthly social benefits for all eligible citizens by 10% to account for inflation."
        },
        {
            "title": "Implement Green Energy Tax Credits",
            "description": "Provide tax credits for citizens and organizations investing in renewable energy infrastructure."
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
        
        return codex_files

def main():
    parser = argparse.ArgumentParser(description="Generate realistic realm demo data")
    parser.add_argument("--citizens", type=int, default=50, help="Number of citizens to generate")
    parser.add_argument("--organizations", type=int, default=5, help="Number of organizations to generate")
    parser.add_argument("--transactions", type=int, default=100, help="Number of transactions to generate")
    parser.add_argument("--disputes", type=int, default=10, help="Number of disputes to generate")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible generation")
    parser.add_argument("--output-dir", type=str, default="generated_realm", help="Output directory")
    parser.add_argument("--realm-name", type=str, default="Generated Demo Realm", help="Name of the realm")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate data
    generator = RealmGenerator(args.seed)
    realm_data = generator.generate_realm_data(
        citizens=args.citizens,
        organizations=args.organizations,
        transactions=args.transactions,
        disputes=args.disputes,
        realm_name=args.realm_name
    )
    
    # Generate separate treasury and realm data
    treasury_data = generator.generate_treasury_data(args.realm_name)
    realm_metadata = generator.generate_realm_metadata(args.realm_name, args.citizens, args.organizations)
    
    # Save main realm data JSON

    json_file = output_dir / "realm_data.json"
    with open(json_file, 'w') as f:
        json.dump(realm_data, f, indent=2)

    # # Save treasury JSON
    # treasury_file = output_dir / "treasury.json"
    # with open(treasury_file, 'w') as f:
    #     json.dump(treasury_data, f, indent=2)
    
    # # Save realm metadata JSON
    # realms_file = output_dir / "realms.json"
    # with open(realms_file, 'w') as f:
    #     json.dump(realm_metadata, f, indent=2)
    
    print(f"Generated realm data saved to: {json_file}")
    
    # Generate codex files
    codex_files = generator.generate_codex_files(output_dir)
    print(f"\nGenerated {len(codex_files)} codex files:")
    for file in codex_files:
        print(f"- {file}")
   
    print(f"Seed used: {generator.seed} (use this seed to reproduce the same data)")

if __name__ == "__main__":
    main()