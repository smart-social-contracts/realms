"""
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
