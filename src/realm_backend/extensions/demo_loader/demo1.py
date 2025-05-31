from kybra_simple_db import Entity, String, TimestampedMixin, Database
from kybra_simple_logging import get_logger

from ggg import User, Organization, Mandate, Codex, Task, TaskSchedule, Instrument, Trade, Dispute, License

logger = get_logger("demo_loader.demo1")


def run():
    """Get test data from this extension.

    The core module will handle the async wrapping for us.
    """
    logger.info("load_demo_data called")

    logger.info("Clearing database")
    Database.get_instance().clear()

    # Create basic users
    logger.info("Creating users")
    user1 = User(
        _id="user_1",
        metadata="{\"name\": \"Alice\", \"age\": 65}"
    )
    
    user2 = User(
        _id="user_2",
        metadata="{\"name\": \"Bob\", \"age\": 40}"
    )
    
    # Create an organization
    org = Organization(
        _id="org_1",
        name="City Council"
    )
    
    # Example 1: Retirement Pensions
    logger.info("Creating retirement pension example")
    
    # Mandate => Task + TaskSchedule => Instrument[ckBTC] => Trade => Certificate(Trade)
    pension_mandate = Mandate(
        _id="mandate_1",
        name="Retirement Pension",
        metadata="{\"description\": \"Citizens receive periodic payments upon reaching age 65\"}"
    )
    
    pension_codex = Codex(
        _id="codex_1",
        code="if user.age >= 65: return True"
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
    pension_task.schedules.add(pension_schedule)
    
    btc_instrument = Instrument(
        _id="instrument_1",
        metadata="{\"type\": \"cryptocurrency\", \"symbol\": \"ckBTC\", \"amount\": 500}"
    )
    
    pension_trade = Trade(
        _id="trade_1",
        metadata="{\"type\": \"pension_payment\", \"month\": \"January 2024\"}"
    )
    pension_trade.user_a = org  # From organization
    pension_trade.user_b = user1  # To pensioner
    pension_trade.instruments_b.add(btc_instrument)
    
    # Example 2: Land rental
    logger.info("Creating land rental example")
    
    # Mandate => Task + TaskSchedule => check if payment (Trade) received => if not => Dispute => Organization
    rental_mandate = Mandate(
        _id="mandate_2",
        name="Land Rental",
        metadata="{\"description\": \"Realm rents out land plot to organization\"}"
    )
    
    rental_codex = Codex(
        _id="codex_2",
        code="if payment_received: return True\nelse: create_dispute()"
    )
    
    rental_task = Task(
        _id="task_2",
        metadata="{\"description\": \"Check rental payment\", \"amount\": 1000, \"plot_id\": \"land_123\"}"
    )
    rental_task.codex = rental_codex
    
    rental_schedule = TaskSchedule(
        _id="schedule_2",
        cron_expression="0 0 1 * *"  # First day of each month
    )
    rental_schedule.tasks.add(rental_task)
    rental_task.schedules.add(rental_schedule)
    
    rental_dispute = Dispute(
        _id="dispute_1",
        status="OPEN",
        metadata="{\"reason\": \"Missed rental payment\", \"due_date\": \"2024-01-01\"}"
    )
    
    # Example 3: Driving license
    logger.info("Creating driving license example")
    
    # Payment => Task => License
    license_task = Task(
        _id="task_3",
        metadata="{\"description\": \"Process driving license issuance\", \"fee\": 200}"
    )
    
    driver_license = License(
        _id="license_1",
        metadata="{\"type\": \"driving\", \"class\": \"B\", \"valid_until\": \"2026-01-01\"}"
    )
    
    license_payment = Trade(
        _id="trade_2",
        metadata="{\"type\": \"license_fee\", \"receipt\": \"DL20240001\"}"
    )
    license_payment.user_a = user2  # From applicant
    license_payment.user_b = org  # To organization
    
    fee_instrument = Instrument(
        _id="instrument_2",
        metadata="{\"type\": \"currency\", \"amount\": 200}"
    )
    license_payment.instruments_a.add(fee_instrument)
    
    # Example 4: Tax collection
    logger.info("Creating tax collection example")
    
    # Task + TaskSchedule => Trades
    tax_codex = Codex(
        _id="codex_3",
        code="calculate_tax_for_user(user)"
    )
    
    tax_task = Task(
        _id="task_4",
        metadata="{\"description\": \"Collect annual taxes\", \"tax_year\": 2024}"
    )
    tax_task.codex = tax_codex
    
    tax_schedule = TaskSchedule(
        _id="schedule_3",
        cron_expression="0 0 15 4 *"  # April 15th yearly
    )
    tax_schedule.tasks.add(tax_task)
    tax_task.schedules.add(tax_schedule)
    
    tax_payment = Trade(
        _id="trade_3",
        metadata="{\"type\": \"tax_payment\", \"year\": 2024, \"status\": \"paid\"}"
    )
    tax_payment.user_a = user2  # From taxpayer
    tax_payment.user_b = org  # To government
    
    tax_instrument = Instrument(
        _id="instrument_3",
        metadata="{\"type\": \"currency\", \"amount\": 5000}"
    )
    tax_payment.instruments_a.add(tax_instrument)
    
    logger.info("Demo data created successfully")
    
    return "Demo data loaded successfully"

'''
PYTHONPATH=/home/user/dev/smart-social-contracts/public/realms2/src/realm_backend python src/realm_backend/extensions/demo_loader/demo1.py 
'''
if __name__ == "__main__":
    run()