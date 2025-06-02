# Import all necessary ggg modules
import json

from ggg import (
    Codex,
    Dispute,
    Human,
    Instrument,
    License,
    Mandate,
    Organization,
    Proposal,
    Realm,
    Task,
    TaskSchedule,
    Trade,
    Transfer,
    Treasury,
    User,
    Vote,
)
from kybra_simple_db import Database, Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.demo1")


def run():
    """Load demo data implementing the examples from the README."""
    logger.info("load_demo_data called")

    logger.info("Clearing database")
    Database.get_instance().clear()

    # Create the Realm as the top political entity
    realm = Realm(
        _id="realm_nova",
        name="Nova Republic",
        description="A progressive digital sovereign realm pioneering governance of digital assets, identity, and social contracts",
    )

    # Create a system user to represent the realm in transfers
    system_user = User(_id="treasury_admin", name="Nova Treasury Authority")

    # Create the Treasury
    treasury = Treasury(
        _id="nova_treasury", vault_principal_id="treasury_vault_9876543210"
    )

    # Create instruments - NovaCoin and ckBTC
    novacoin = Instrument(
        _id="instrument_novacoin",
        metadata=json.dumps(
            {
                "type": "cryptocurrency",
                "symbol": "NVC",
                "decimal_places": 8,
                "total_supply": 21000000,
                "description": "Nova Republic's native digital currency",
                "treasury_balance": 15750000,  # Treasury holds 75% of total supply
            }
        ),
    )

    ckbtc = Instrument(
        _id="instrument_ckbtc",
        metadata=json.dumps(
            {
                "type": "wrapped_cryptocurrency",
                "symbol": "ckBTC",
                "decimal_places": 8,
                "description": "Wrapped Bitcoin on Nova Republic blockchain",
                "backing_asset": "Bitcoin",
                "treasury_balance": 12550000000,  # 125.5 ckBTC in satoshis (125.5 * 100,000,000)
                "current_exchange_rate": "1 ckBTC = 45,000 NVC",
            }
        ),
    )

    fee_instrument = Instrument(
        _id="instrument_nova_credit",
        metadata=json.dumps(
            {
                "type": "digital_credit",
                "symbol": "NVC",
                "usage": "government_fees",
                "issuer": "Nova Republic Treasury",
                "treasury_balance": 2500000,
            }
        ),
    )

    tax_instrument = Instrument(
        _id="instrument_tax_credit",
        metadata=json.dumps(
            {
                "type": "tax_payment",
                "symbol": "NVTX",
                "usage": "tax_obligations",
                "fiscal_year": 2024,
                "treasury_balance": 8750000,
            }
        ),
    )

    # Create basic humans and users with more realistic profiles
    logger.info("Creating humans")

    # Citizens
    human1 = Human(_id="human_elena")
    user1 = User(_id="citizen_elena", name="Elena Rodriguez")

    human2 = Human(_id="human_michael")
    user2 = User(_id="citizen_michael", name="Michael Chen")

    human3 = Human(_id="human_aisha")
    user3 = User(_id="citizen_aisha", name="Aisha Okoye")

    human4 = Human(_id="human_sven")
    user4 = User(_id="citizen_sven", name="Sven Johansson")

    # Create organizations
    nova_bank = Organization(_id="org_nova_bank", name="Nova Republic Central Bank")
    nova_housing = Organization(_id="org_nova_housing", name="Nova Housing Authority")
    nova_transport = Organization(
        _id="org_nova_transport", name="Nova Transportation Department"
    )
    nova_health = Organization(_id="org_nova_health", name="Nova Healthcare System")

    # Example 1: Universal Basic Income Program
    logger.info("Creating UBI example")

    ubi_mandate = Mandate(
        _id="mandate_ubi",
        name="Universal Basic Income Program",
        metadata=json.dumps(
            {
                "description": "All verified citizens receive a monthly basic income to ensure financial stability",
                "established_date": "2024-01-01",
                "authority": "Nova Economic Council",
                "legal_reference": "Economic Stability Act of 2024, Section 3",
            }
        ),
    )

    ubi_codex = Codex(
        _id="codex_ubi",
        code="""
# Check if user is a verified citizen with active status
if user.verification_status == 'VERIFIED' and user.status == 'ACTIVE':
    # Check if user has already received payment this month
    if not has_received_payment(user, current_month()):
        return True
return False
""",
    )

    ubi_task = Task(
        _id="task_ubi_payment",
        metadata=json.dumps(
            {
                "description": "Process monthly UBI payments to citizens",
                "amount": 1200,
                "currency": "NovaCoin",
                "department": "Economic Welfare",
                "priority": "HIGH",
            }
        ),
    )
    ubi_task.codex = ubi_codex

    ubi_schedule = TaskSchedule(
        _id="schedule_ubi", cron_expression="0 0 1 * *"  # First day of each month
    )
    ubi_schedule.tasks.add(ubi_task)

    # Create UBI trade and transfer
    ubi_trade = Trade(
        _id="trade_ubi_march2024",
        metadata=json.dumps(
            {
                "type": "ubi_payment",
                "period": "March 2024",
                "transaction_hash": "0x7a9b65e3d4f8c102938476a8c72e425fb7b2ecf4",
            }
        ),
    )

    # Add Transfer object for the UBI payment
    ubi_transfer = Transfer(
        _id="transfer_ubi_elena_march2024",
        amount=1200,
    )
    ubi_transfer.from_user = system_user
    ubi_transfer.to_user = user1
    ubi_transfer.instrument = novacoin
    ubi_trade.transfer_1 = ubi_transfer

    # Example 2: Community Housing Program
    logger.info("Creating community housing example")

    housing_mandate = Mandate(
        _id="mandate_housing",
        name="Community Housing Program",
        metadata=json.dumps(
            {
                "description": "Affordable housing system with transparent rules and fair distribution",
                "established_date": "2024-02-15",
                "authority": "Nova Housing Council",
                "legal_reference": "Housing Access Act of 2024",
            }
        ),
    )

    housing_codex = Codex(
        _id="codex_housing",
        code="""
# Check if rent payment is received on time
if payment_received and payment_date <= due_date:
    update_tenant_status(tenant_id, 'GOOD_STANDING')
    return True
elif payment_received and payment_date <= (due_date + grace_period):
    update_tenant_status(tenant_id, 'LATE_PAYMENT')
    assess_late_fee(tenant_id, amount=50)
    return True
else:
    update_tenant_status(tenant_id, 'PAYMENT_MISSING')
    create_dispute(tenant_id, reason="Missing housing payment")
    return False
""",
    )

    housing_task = Task(
        _id="task_housing_payment_check",
        metadata=json.dumps(
            {
                "description": "Verify monthly housing payments and update tenant status",
                "property_id": "nova_heights_304",
                "unit_size": "2BR",
                "monthly_rent": 750,
                "due_date": 1,  # 1st of month
                "grace_period_days": 5,
            }
        ),
    )
    housing_task.codex = housing_codex

    housing_schedule = TaskSchedule(
        _id="schedule_housing_payments",
        cron_expression="0 0 2 * *",  # 2nd day of each month (checks for 1st day payments)
    )
    housing_schedule.tasks.add(housing_task)

    housing_dispute = Dispute(
        _id="dispute_housing_michael_april",
        status="OPEN",
        metadata="Tenant: Michael Chen; Property: Nova Heights, Unit 304; Issue: Missed April 2024 payment; Date: 2024-04-02",
    )

    # Create rental trade and transfer
    housing_trade = Trade(
        _id="trade_housing_michael_march2024",
        metadata=json.dumps(
            {
                "type": "housing_payment",
                "month": "March 2024",
                "property": "Nova Heights, Unit 304",
                "transaction_hash": "0x3e7b91d5c8f9a0e265842f1c8b7e45f69c1a2e47",
            }
        ),
    )

    # Add a rental payment transfer
    housing_transfer = Transfer(
        _id="transfer_housing_michael_march2024",
        amount=750,
    )
    housing_transfer.from_user = user2  # Tenant (Michael)
    housing_transfer.to_user = (
        user3  # Property manager (Aisha represents housing authority)
    )
    housing_transfer.instrument = novacoin
    housing_trade.transfer_1 = housing_transfer

    # Example 3: Autonomous Vehicle License
    logger.info("Creating autonomous vehicle license example")

    transport_mandate = Mandate(
        _id="mandate_transport",
        name="Autonomous Vehicle Licensing",
        metadata=json.dumps(
            {
                "description": "Regulation of autonomous vehicles within Nova Republic",
                "established_date": "2024-01-30",
                "authority": "Nova Transportation Department",
                "legal_reference": "Autonomous Transport Act of 2024",
            }
        ),
    )

    vehicle_license_codex = Codex(
        _id="codex_av_license",
        code="""
# Verify applicant meets requirements
if not user.has_passed_test('av_operation'):
    return False

# Verify vehicle meets safety standards
if not vehicle.safety_rating >= 4.5:
    return False
    
# Check for previous violations
if user.violation_count > 2:
    return False
    
# All requirements met
issue_license(user.id, 'AUTONOMOUS_VEHICLE', validity_years=2)
return True
""",
    )

    license_task = Task(
        _id="task_av_license_issuance",
        metadata=json.dumps(
            {
                "description": "Process autonomous vehicle license applications",
                "fee": 350,
                "validity_period": "2 years",
                "required_documents": [
                    "identity_verification",
                    "av_test_results",
                    "vehicle_registration",
                ],
            }
        ),
    )
    license_task.codex = vehicle_license_codex

    av_license = License(
        _id="license_av_sven",
        metadata=json.dumps(
            {
                "holder": "Sven Johansson",
                "type": "AUTONOMOUS_VEHICLE_OPERATION",
                "vehicle_id": "AV-XE-2045",
                "issued_date": "2024-03-15",
                "expiry_date": "2026-03-15",
                "restrictions": "Urban areas only",
                "license_number": "AV-24-9087",
            }
        ),
    )

    # Create license trade and transfer
    license_trade = Trade(
        _id="trade_av_license_sven",
        metadata=json.dumps(
            {
                "type": "license_fee",
                "license_type": "Autonomous Vehicle Operation",
                "receipt": "AVL-2024-0387",
                "transaction_hash": "0x5f2a71e8b94c102a3847d69c7e45b1e78a9c1235",
            }
        ),
    )

    # Add a license fee transfer
    license_transfer = Transfer(
        _id="transfer_av_license_fee_sven",
        amount=350,
    )
    license_transfer.from_user = user4  # Sven
    license_transfer.to_user = system_user
    license_transfer.instrument = fee_instrument
    license_trade.transfer_1 = license_transfer

    # Example 4: Progressive Tax System
    logger.info("Creating progressive tax system example")

    tax_mandate = Mandate(
        _id="mandate_tax",
        name="Progressive Digital Economy Taxation",
        metadata=json.dumps(
            {
                "description": "Fair taxation system for digital assets and income",
                "established_date": "2024-01-01",
                "authority": "Nova Treasury Department",
                "legal_reference": "Digital Economy Taxation Act of 2024",
            }
        ),
    )

    tax_codex = Codex(
        _id="codex_tax",
        code="""
# Progressive tax calculation
def calculate_tax_for_user(user):
    annual_income = get_user_annual_income(user.id)
    
    # Progressive tax brackets
    if annual_income < 20000:
        tax_rate = 0.05  # 5%
    elif annual_income < 50000:
        tax_rate = 0.12  # 12%
    elif annual_income < 100000:
        tax_rate = 0.20  # 20%
    else:
        tax_rate = 0.28  # 28%
    
    # Calculate basic tax
    tax_amount = annual_income * tax_rate
    
    # Apply deductions
    deductions = calculate_user_deductions(user.id)
    final_tax = max(0, tax_amount - deductions)
    
    # Record calculation
    record_tax_assessment(user.id, tax_year, final_tax)
    
    return final_tax
""",
    )

    tax_task = Task(
        _id="task_annual_tax_assessment",
        metadata=json.dumps(
            {
                "description": "Calculate and assess annual taxes for citizens",
                "tax_year": 2024,
                "filing_deadline": "2024-04-15",
                "department": "Nova Treasury",
                "tax_code_version": "2024.1.3",
            }
        ),
    )
    tax_task.codex = tax_codex

    tax_schedule = TaskSchedule(
        _id="schedule_tax_assessment",
        cron_expression="0 0 1 3 *",  # March 1st yearly (tax preparation season)
    )
    tax_schedule.tasks.add(tax_task)

    # Create tax trade and transfer
    tax_trade = Trade(
        _id="trade_tax_elena_2024",
        metadata=json.dumps(
            {
                "type": "annual_tax_payment",
                "year": 2024,
                "status": "paid",
                "filing_method": "digital_submission",
                "assessment_id": "TX-2024-E-78934",
                "transaction_hash": "0x9e4f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
            }
        ),
    )

    # Add a tax payment transfer
    tax_transfer = Transfer(
        _id="transfer_tax_elena_2024",
        amount=3450,
    )
    tax_transfer.from_user = user1  # Elena
    tax_transfer.to_user = system_user
    tax_transfer.instrument = tax_instrument
    tax_trade.transfer_1 = tax_transfer

    # Example 5: Healthcare Contribution System
    logger.info("Creating healthcare contribution example")

    healthcare_mandate = Mandate(
        _id="mandate_healthcare",
        name="Universal Healthcare System",
        metadata=json.dumps(
            {
                "description": "Comprehensive healthcare coverage for all citizens",
                "established_date": "2024-01-01",
                "authority": "Nova Health Council",
                "legal_reference": "Healthcare Access Act of 2024",
            }
        ),
    )

    healthcare_codex = Codex(
        _id="codex_healthcare",
        code="""
# Calculate monthly healthcare contribution
def calculate_healthcare_contribution(user):
    monthly_income = get_user_monthly_income(user.id)
    
    # Basic contribution is 3% of income
    base_contribution = monthly_income * 0.03
    
    # Cap at 300 NovaCoins
    contribution = min(base_contribution, 300)
    
    # Apply discounts for preventative care
    if user.has_completed_annual_checkup:
        contribution *= 0.9  # 10% discount
    
    return contribution
""",
    )

    healthcare_task = Task(
        _id="task_healthcare_contribution",
        metadata=json.dumps(
            {
                "description": "Process monthly healthcare contributions",
                "department": "Nova Health",
                "contribution_model": "income-based",
                "coverage_level": "comprehensive",
            }
        ),
    )
    healthcare_task.codex = healthcare_codex

    healthcare_schedule = TaskSchedule(
        _id="schedule_healthcare", cron_expression="0 0 15 * *"  # 15th of each month
    )
    healthcare_schedule.tasks.add(healthcare_task)

    # Create healthcare contribution trade and transfer
    healthcare_trade = Trade(
        _id="trade_healthcare_michael_march2024",
        metadata=json.dumps(
            {
                "type": "healthcare_contribution",
                "month": "March 2024",
                "coverage_period": "April 2024",
                "member_id": "NHC-24-5678",
                "transaction_hash": "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            }
        ),
    )

    # Add healthcare contribution transfer
    healthcare_transfer = Transfer(
        _id="transfer_healthcare_michael_march2024",
        amount=180,
    )
    healthcare_transfer.from_user = user2  # Michael
    healthcare_transfer.to_user = system_user
    healthcare_transfer.instrument = novacoin
    healthcare_trade.transfer_1 = healthcare_transfer

    # Example 6: Governance Proposals and Voting
    logger.info("Creating governance proposals and voting examples")

    # Proposal 1: Increase UBI to 1500 NovaCoins
    ubi_increase_proposal = Proposal(
        _id="proposal_ubi_increase_2024",
        metadata=json.dumps(
            {
                "title": "Increase UBI to 1,500 NVC",
                "proposer": "Elena Rodriguez",
                "status": "active",
                "category": "economic_policy",
            }
        ),
    )

    # Proposal 2: Green Energy Infrastructure Initiative
    green_energy_proposal = Proposal(
        _id="proposal_green_energy_2024",
        metadata=json.dumps(
            {
                "title": "Green Energy Infrastructure Initiative",
                "proposer": "Nova Environmental Council",
                "status": "active",
                "budget": "50M NVC",
            }
        ),
    )

    # Proposal 3: Autonomous Vehicle Safety Standards Update
    av_safety_proposal = Proposal(
        _id="proposal_av_safety_update_2024",
        metadata=json.dumps(
            {
                "title": "Enhanced AV Safety Standards",
                "proposer": "Sven Johansson",
                "status": "active",
                "category": "transportation",
            }
        ),
    )

    # Votes on UBI Increase Proposal
    elena_ubi_vote = Vote(
        _id="vote_elena_ubi_increase",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_ubi_increase_2024",
                "voter": "Elena Rodriguez",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    michael_ubi_vote = Vote(
        _id="vote_michael_ubi_increase",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_ubi_increase_2024",
                "voter": "Michael Chen",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    aisha_ubi_vote = Vote(
        _id="vote_aisha_ubi_increase",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_ubi_increase_2024",
                "voter": "Aisha Okoye",
                "vote": "abstain",
                "verified": True,
            }
        ),
    )

    sven_ubi_vote = Vote(
        _id="vote_sven_ubi_increase",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_ubi_increase_2024",
                "voter": "Sven Johansson",
                "vote": "no",
                "verified": True,
            }
        ),
    )

    # Votes on Green Energy Proposal
    elena_green_vote = Vote(
        _id="vote_elena_green_energy",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_green_energy_2024",
                "voter": "Elena Rodriguez",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    michael_green_vote = Vote(
        _id="vote_michael_green_energy",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_green_energy_2024",
                "voter": "Michael Chen",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    aisha_green_vote = Vote(
        _id="vote_aisha_green_energy",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_green_energy_2024",
                "voter": "Aisha Okoye",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    # Votes on AV Safety Proposal
    sven_av_vote = Vote(
        _id="vote_sven_av_safety",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_av_safety_update_2024",
                "voter": "Sven Johansson",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    michael_av_vote = Vote(
        _id="vote_michael_av_safety",
        metadata=json.dumps(
            {
                "proposal_id": "proposal_av_safety_update_2024",
                "voter": "Michael Chen",
                "vote": "yes",
                "verified": True,
            }
        ),
    )

    # Additional transfers with more context
    donation_transfer = Transfer(
        _id="transfer_donation_elena_community_garden",
        amount=250,
        metadata=json.dumps(
            {
                "purpose": "Community Garden Project Donation",
                "project": "Nova Heights Rooftop Garden",
                "donor_message": "To help create green spaces in our community",
            }
        ),
    )
    donation_transfer.from_user = user1  # Elena
    donation_transfer.to_user = user3  # Aisha (community project leader)
    donation_transfer.instrument = novacoin

    grant_transfer = Transfer(
        _id="transfer_innovation_grant_sven",
        amount=5000,
        metadata=json.dumps(
            {
                "grant_id": "IG-2024-042",
                "purpose": "Autonomous Vehicle Safety Research",
                "institution": "Nova Innovation Fund",
                "deliverables": "Research paper and open-source safety protocol",
            }
        ),
    )
    grant_transfer.from_user = system_user
    grant_transfer.to_user = user4  # Sven
    grant_transfer.instrument = novacoin

    refund_transfer = Transfer(
        _id="transfer_tax_refund_elena",
        amount=125,
        metadata=json.dumps(
            {
                "reason": "Overpayment on 2023 taxes",
                "reference": "TR-2024-E-1234",
                "processing_date": "2024-03-20",
            }
        ),
    )
    refund_transfer.from_user = system_user
    refund_transfer.to_user = user1  # Elena
    refund_transfer.instrument = tax_instrument

    # ckBTC-related transfers
    btc_purchase_transfer = Transfer(
        _id="transfer_btc_purchase_michael",
        amount=50000000,  # 0.5 ckBTC in satoshis (0.5 * 100,000,000)
        metadata=json.dumps(
            {
                "purpose": "Personal investment in ckBTC",
                "exchange_rate": "45,000 NVC per ckBTC",
                "transaction_fee": "25 NVC",
                "exchange": "Nova Digital Exchange",
                "settlement_time": "2024-06-01T14:30:00Z",
            }
        ),
    )
    btc_purchase_transfer.from_user = system_user  # Treasury
    btc_purchase_transfer.to_user = user2  # Michael
    btc_purchase_transfer.instrument = ckbtc

    btc_payment_transfer = Transfer(
        _id="transfer_btc_payment_aisha_elena",
        amount=10000000,  # 0.1 ckBTC in satoshis (0.1 * 100,000,000)
        metadata=json.dumps(
            {
                "purpose": "Payment for consulting services",
                "service": "Housing policy advisory",
                "contract_ref": "HPA-2024-078",
                "payment_date": "2024-06-02",
            }
        ),
    )
    btc_payment_transfer.from_user = user3  # Aisha
    btc_payment_transfer.to_user = user1  # Elena
    btc_payment_transfer.instrument = ckbtc

    treasury_rebalance_transfer = Transfer(
        _id="transfer_treasury_rebalance_btc",
        amount=2500000000,  # 25 ckBTC in satoshis (25 * 100,000,000)
        metadata=json.dumps(
            {
                "purpose": "Treasury portfolio rebalancing",
                "strategy": "Diversification into digital assets",
                "approval": "Treasury Board Resolution #2024-Q2-15",
                "market_conditions": "Strategic accumulation during market stability",
                "allocation_target": "10% of treasury in ckBTC",
            }
        ),
    )
    treasury_rebalance_transfer.from_user = system_user  # External acquisition
    treasury_rebalance_transfer.to_user = system_user  # Treasury
    treasury_rebalance_transfer.instrument = ckbtc

    logger.info("Demo data created successfully")

    logger.info(f"Database dump: {Database.get_instance().raw_dump_json(pretty=True)}")

    return "Enhanced demo data loaded successfully"


"""
PYTHONPATH=/home/user/dev/smart-social-contracts/public/realms2/src/realm_backend python src/realm_backend/extensions/demo_loader/demo1.py
"""
if __name__ == "__main__":
    run()
