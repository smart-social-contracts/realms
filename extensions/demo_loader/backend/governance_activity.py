"""
Governance Activity demo data loader
Creates realistic governance proposals, votes, and community engagement
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ggg import (
    Proposal,
    Vote,
    User,
)
from kybra_simple_logging import get_logger

from .config import NUM_PROPOSALS, NUM_VOTES_PER_PROPOSAL

logger = get_logger("demo_loader.governance_activity")

# Realistic governance proposal topics
PROPOSAL_TOPICS = [
    {
        "title": "Increase Universal Basic Income to 750 tokens/month",
        "description": "Proposal to increase monthly UBI payments from 500 to 750 tokens to better support citizens amid rising costs. This 50% increase would be funded through carbon credit revenue and innovation fund surplus.",
        "category": "economic_policy",
        "impact": "high"
    },
    {
        "title": "Implement Quadratic Voting for Major Decisions",
        "description": "Adopt quadratic voting mechanism for proposals with realm-wide impact. This would give more weight to passionate voters while preventing vote buying and ensuring minority voices are heard.",
        "category": "governance_reform",
        "impact": "high"
    },
    {
        "title": "Establish Digital Privacy Rights Charter",
        "description": "Create comprehensive privacy rights framework protecting citizen data, establishing right to digital anonymity, and limiting surveillance capabilities of realm infrastructure.",
        "category": "rights_and_freedoms",
        "impact": "high"
    },
    {
        "title": "Launch Community-Owned Renewable Energy Grid",
        "description": "Invest 50,000 tokens in distributed solar and wind infrastructure owned collectively by citizens. Revenue from energy sales would fund additional sustainability initiatives.",
        "category": "sustainability",
        "impact": "medium"
    },
    {
        "title": "Create Decentralized Education Platform",
        "description": "Build peer-to-peer learning platform where citizens can teach and learn skills, with token rewards for quality instruction and successful skill verification.",
        "category": "education",
        "impact": "medium"
    },
    {
        "title": "Establish Innovation Incubator Program",
        "description": "Allocate 25,000 tokens quarterly for citizen-led innovation projects. Projects would be selected through community voting and mentored by experienced entrepreneurs.",
        "category": "innovation",
        "impact": "medium"
    },
    {
        "title": "Implement Reputation-Based Governance Weights",
        "description": "Introduce reputation system where voting power is influenced by community contributions, expertise demonstration, and positive peer reviews.",
        "category": "governance_reform",
        "impact": "high"
    },
    {
        "title": "Create Mental Health Support Network",
        "description": "Establish peer-support mental health network with trained volunteers, crisis intervention protocols, and integration with existing health monitoring systems.",
        "category": "health_and_welfare",
        "impact": "medium"
    },
    {
        "title": "Launch Circular Economy Initiative",
        "description": "Implement waste reduction and resource sharing programs with token incentives for recycling, repair services, and sustainable consumption practices.",
        "category": "sustainability",
        "impact": "medium"
    },
    {
        "title": "Establish Conflict Resolution Council",
        "description": "Create elected council of trained mediators to handle disputes before they escalate to formal litigation, reducing justice system burden and improving community harmony.",
        "category": "justice_and_law",
        "impact": "medium"
    },
    {
        "title": "Implement Progressive Taxation on Large Holdings",
        "description": "Introduce graduated tax rates on digital asset holdings above 100,000 tokens to fund public services and reduce wealth inequality.",
        "category": "economic_policy",
        "impact": "high"
    },
    {
        "title": "Create Citizen Assembly for Constitutional Review",
        "description": "Establish randomly selected citizen assembly to review and propose updates to realm governance structures and fundamental rights.",
        "category": "governance_reform",
        "impact": "high"
    },
    {
        "title": "Launch Digital Art and Culture Fund",
        "description": "Allocate 15,000 tokens monthly to support digital artists, cultural events, and creative commons projects that enrich community life.",
        "category": "arts_and_culture",
        "impact": "low"
    },
    {
        "title": "Establish Emergency Response Protocol",
        "description": "Create rapid response system for realm emergencies including cyber attacks, natural disasters, and economic crises with pre-approved emergency powers.",
        "category": "security_and_safety",
        "impact": "high"
    },
    {
        "title": "Implement Transparent Budget Dashboard",
        "description": "Create real-time public dashboard showing all realm expenditures, revenue sources, and budget allocations with citizen comment and feedback systems.",
        "category": "transparency",
        "impact": "medium"
    },
    {
        "title": "Create Cross-Realm Diplomatic Relations",
        "description": "Establish formal diplomatic protocols for interacting with other digital realms including trade agreements, mutual aid pacts, and conflict resolution mechanisms.",
        "category": "foreign_relations",
        "impact": "medium"
    },
    {
        "title": "Launch Skills-Based Volunteering Platform",
        "description": "Build platform matching citizen skills with community needs, offering token rewards for volunteer work and skill-sharing contributions.",
        "category": "community_engagement",
        "impact": "low"
    },
    {
        "title": "Implement Carbon-Negative Commitment",
        "description": "Commit to achieving carbon-negative status within 2 years through renewable energy, carbon capture investments, and sustainable practice incentives.",
        "category": "sustainability",
        "impact": "high"
    },
    {
        "title": "Create Senior Citizen Support Program",
        "description": "Establish comprehensive support system for elderly citizens including increased UBI, health monitoring, social engagement programs, and technology assistance.",
        "category": "health_and_welfare",
        "impact": "medium"
    },
    {
        "title": "Launch Open Source Everything Initiative",
        "description": "Mandate that all realm-funded software, research, and innovations be released under open source licenses to benefit the broader digital community.",
        "category": "innovation",
        "impact": "medium"
    },
    {
        "title": "Establish Youth Leadership Development",
        "description": "Create mentorship and leadership training programs for citizens under 25, including governance internships and project leadership opportunities.",
        "category": "education",
        "impact": "low"
    },
    {
        "title": "Implement Algorithmic Transparency Requirements",
        "description": "Require all automated systems used in governance to be auditable and explainable, with public documentation of decision-making algorithms.",
        "category": "transparency",
        "impact": "high"
    },
    {
        "title": "Create Community Resilience Fund",
        "description": "Establish emergency fund equal to 6 months of realm operating expenses to ensure continuity during economic downturns or external shocks.",
        "category": "economic_policy",
        "impact": "high"
    },
    {
        "title": "Launch Intergenerational Equity Program",
        "description": "Implement policies ensuring current decisions consider long-term impacts on future generations, including sustainability metrics and youth representation requirements.",
        "category": "governance_reform",
        "impact": "medium"
    },
    {
        "title": "Establish Digital Rights Enforcement Agency",
        "description": "Create independent agency to investigate privacy violations, digital rights abuses, and ensure compliance with citizen protection laws.",
        "category": "rights_and_freedoms",
        "impact": "medium"
    }
]

# Vote outcomes with realistic distributions
VOTE_OUTCOMES = [
    {"choice": "strongly_support", "weight": 0.25},
    {"choice": "support", "weight": 0.35},
    {"choice": "neutral", "weight": 0.15},
    {"choice": "oppose", "weight": 0.20},
    {"choice": "strongly_oppose", "weight": 0.05}
]

def generate_realistic_votes(proposal_id: str, num_votes: int) -> List[Dict]:
    """Generate realistic voting patterns based on proposal impact and category"""
    votes = []
    
    # Create weighted random voting based on realistic patterns
    choices = []
    weights = []
    for outcome in VOTE_OUTCOMES:
        choices.append(outcome["choice"])
        weights.append(outcome["weight"])
    
    for i in range(num_votes):
        # Add some randomness to make it realistic
        vote_choice = random.choices(choices, weights=weights)[0]
        
        # Simulate voting timestamp over the past 30 days
        days_ago = random.randint(1, 30)
        vote_timestamp = datetime.now() - timedelta(days=days_ago)
        
        votes.append({
            "proposal_id": proposal_id,
            "choice": vote_choice,
            "timestamp": vote_timestamp.isoformat(),
            "voter_index": i
        })
    
    return votes

def run(batch=None):
    """Create governance activity including proposals and votes."""
    
    logger.info(f"Creating {NUM_PROPOSALS} governance proposals with {NUM_VOTES_PER_PROPOSAL} votes each")
    
    proposals = []
    all_votes = []
    
    # Create proposals
    for i in range(NUM_PROPOSALS):
        # Select a proposal topic
        topic = PROPOSAL_TOPICS[i % len(PROPOSAL_TOPICS)]
        
        # Create proposal with realistic timing (past 60 days)
        days_ago = random.randint(1, 60)
        created_date = datetime.now() - timedelta(days=days_ago)
        
        # Determine proposal status based on age
        if days_ago > 30:
            status = random.choice(["passed", "rejected", "implemented"])
        elif days_ago > 14:
            status = "voting"
        else:
            status = "active"
        
        proposal_metadata = {
            "description": topic["description"],
            "category": topic["category"],
            "impact_level": topic["impact"],
            "status": status,
            "created_date": created_date.isoformat(),
            "voting_deadline": (created_date + timedelta(days=14)).isoformat()
        }
        
        proposal = Proposal(
            name=topic["title"],
            metadata=json.dumps(proposal_metadata)
        )
        proposals.append(proposal)
        
        # Generate votes for this proposal
        proposal_votes = generate_realistic_votes(f"proposal_{i}", NUM_VOTES_PER_PROPOSAL)
        all_votes.extend(proposal_votes)
    
    logger.info(f"Created {len(proposals)} proposals and {len(all_votes)} votes")
    
    # Calculate engagement statistics
    total_possible_votes = NUM_PROPOSALS * 250  # Assuming 250 users
    actual_votes = len(all_votes)
    participation_rate = (actual_votes / total_possible_votes) * 100
    
    return f"Created {len(proposals)} governance proposals with {len(all_votes)} votes. Citizen participation rate: {participation_rate:.1f}%. Active democracy with diverse policy discussions across economic, social, and governance reforms."
