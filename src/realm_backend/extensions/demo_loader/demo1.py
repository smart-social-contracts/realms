from kybra_simple_db import Entity, String, TimestampedMixin, Database
from kybra_simple_logging import get_logger

# Import all necessary ggg modules
from ggg import User, Organization, Mandate, Codex, Task, TaskSchedule, Instrument, Trade
from ggg import Dispute, License, Realm, Treasury, Human

logger = get_logger("demo_loader.demo1")


def run():
    """Load demo data implementing the examples from the README."""
    logger.info("load_demo_data called")

    logger.info("Clearing database")
    Database.get_instance().clear()

    # Create the Realm as the top political entity
    realm = Realm(
        _id="realm_1",
        name="Digital Republic",
        description="A digital sovereign realm governing digital assets and relationships"
    )
    
    # Create a system user to represent the realm in transfers
    system_user = User(
        _id="system_user",
        name="System"
    )
    
    # Create the Treasury
    treasury = Treasury(
        _id="treasury_1",
        vault_principal_id="abc123"
    )
    
    # Create basic humans and users
    logger.info("Creating humans")
    human1 = Human(
        _id="human_1"
    )
    
    user1 = User(
        _id="user_1",
        name="Alice"
    )
    
    human2 = Human(
        _id="human_2"
    )
    
    user2 = User(
        _id="user_2",
        name="Bob"
    )
    
    # Create an organization
    org = Organization(
        _id="org_1",
        name="Financial Services Inc."
    )
    
    # Example 1: Retirement Pensions
    logger.info("Creating retirement pension example")
    
    pension_mandate = Mandate(
        _id="mandate_1",
        name="Retirement Pension",
        metadata="{\"description\": \"Citizens receive periodic payments upon reaching age 65\"}"
    )
    
    pension_codex = Codex(
        _id="codex_1",
        code="if human.age >= 65: return True"
    )
    
    pension_task = Task(
        _id="task_1",
        metadata="{\"description\": \"Process pension payments\", \"amount\": 500}"
    )
    pension_task.codex = pension_codex
    
    pension_schedule = TaskSchedule(
        _id="schedule_1",
        cron_expression="0 0 1 * *"  # First day of each month
    )
    pension_schedule.tasks.add(pension_task)
    
    btc_instrument = Instrument(
        _id="instrument_1"
    )
    
    # Since we can't use Transfer objects due to missing reverse relationships,
    # we'll use Trade objects instead which should have the proper relationships set up
    
    pension_trade = Trade(
        _id="trade_1",
        metadata="{\"type\": \"pension_payment\", \"month\": \"January 2024\"}"
    )
    pension_trade.user_a = system_user  # From system (representing realm)
    pension_trade.user_b = user1  # To pensioner
    pension_trade.instruments_b.add(btc_instrument)
    
    # Example 2: Land rental
    logger.info("Creating land rental example")
    
    rental_mandate = Mandate(
        _id="mandate_2",
        name="Land Rental"
    )
    
    rental_codex = Codex(
        _id="codex_2",
        code="if payment_received: return True\nelse: create_dispute()"
    )
    
    rental_task = Task(
        _id="task_2",
        metadata="{\"description\": \"Check rental payment\", \"plot_id\": \"land_123\"}"
    )
    rental_task.codex = rental_codex
    
    rental_schedule = TaskSchedule(
        _id="schedule_2",
        cron_expression="0 0 1 * *"  # First day of each month
    )
    rental_schedule.tasks.add(rental_task)
    
    rental_dispute = Dispute(
        _id="dispute_1",
        status="OPEN"
    )
    
    # Example 3: Driving license
    logger.info("Creating driving license example")
    
    license_task = Task(
        _id="task_3"
    )
    
    driver_license = License(
        _id="license_1"
    )
    
    fee_instrument = Instrument(
        _id="instrument_2"
    )
    
    license_payment = Trade(
        _id="trade_2",
        metadata="{\"type\": \"license_fee\", \"receipt\": \"DL20240001\"}"
    )
    license_payment.user_a = user2  # From applicant
    license_payment.user_b = system_user  # To system (representing realm)
    license_payment.instruments_a.add(fee_instrument)
    
    # Example 4: Tax collection
    logger.info("Creating tax collection example")
    
    tax_codex = Codex(
        _id="codex_3",
        code="calculate_tax_for_user(user)"
    )
    
    tax_task = Task(
        _id="task_4"
    )
    tax_task.codex = tax_codex
    
    tax_schedule = TaskSchedule(
        _id="schedule_3",
        cron_expression="0 0 15 4 *"  # April 15th yearly
    )
    tax_schedule.tasks.add(tax_task)
    
    tax_instrument = Instrument(
        _id="instrument_3"
    )
    
    tax_payment = Trade(
        _id="trade_3",
        metadata="{\"type\": \"tax_payment\", \"year\": 2024, \"status\": \"paid\"}"
    )
    tax_payment.user_a = user2  # From taxpayer
    tax_payment.user_b = system_user  # To system (representing realm)
    tax_payment.instruments_a.add(tax_instrument)
    
    logger.info("Demo data created successfully")

    logger.info(f"Database dump: {Database.get_instance().raw_dump_json(pretty=True)}")
    
    return "Demo data loaded successfully"

'''
PYTHONPATH=/home/user/dev/smart-social-contracts/public/realms2/src/realm_backend python src/realm_backend/extensions/demo_loader/demo1.py 
'''
if __name__ == "__main__":
    run()