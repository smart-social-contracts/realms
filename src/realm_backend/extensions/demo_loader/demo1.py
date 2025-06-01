# Import all necessary ggg modules
from ggg import (
    Codex,
    Dispute,
    Human,
    Instrument,
    License,
    Mandate,
    Organization,
    Realm,
    Task,
    TaskSchedule,
    Trade,
    Transfer,
    Treasury,
    User,
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
        _id="realm_1",
        name="Digital Republic",
        description="A digital sovereign realm governing digital assets and relationships",
    )

    # Create a system user to represent the realm in transfers
    system_user = User(_id="system_user", name="System")

    # Create the Treasury
    treasury = Treasury(_id="treasury_1", vault_principal_id="abc123")

    # Create basic humans and users
    logger.info("Creating humans")
    human1 = Human(_id="human_1")

    user1 = User(_id="user_1", name="Alice")

    human2 = Human(_id="human_2")

    user2 = User(_id="user_2", name="Bob")

    # Create an organization
    org = Organization(_id="org_1", name="Financial Services Inc.")

    # Example 1: Retirement Pensions
    logger.info("Creating retirement pension example")

    pension_mandate = Mandate(
        _id="mandate_1",
        name="Retirement Pension",
        metadata='{"description": "Citizens receive periodic payments upon reaching age 65"}',
    )

    pension_codex = Codex(_id="codex_1", code="if human.age >= 65: return True")

    pension_task = Task(
        _id="task_1",
        metadata='{"description": "Process pension payments", "amount": 500}',
    )
    pension_task.codex = pension_codex

    pension_schedule = TaskSchedule(
        _id="schedule_1", cron_expression="0 0 1 * *"  # First day of each month
    )
    pension_schedule.tasks.add(pension_task)

    btc_instrument = Instrument(_id="instrument_1")

    # Create pension trade and transfer
    pension_trade = Trade(
        _id="trade_1", metadata='{"type": "pension_payment", "month": "January 2024"}'
    )

    # Add Transfer object for the pension payment
    pension_transfer = Transfer(
        _id="transfer_1",
        amount=500,
    )
    pension_transfer.from_user = system_user
    pension_transfer.to_user = user1
    pension_transfer.instrument = btc_instrument
    pension_trade.transfer_1 = pension_transfer

    # Example 2: Land rental
    logger.info("Creating land rental example")

    rental_mandate = Mandate(_id="mandate_2", name="Land Rental")

    rental_codex = Codex(
        _id="codex_2", code="if payment_received: return True\nelse: create_dispute()"
    )

    rental_task = Task(
        _id="task_2",
        metadata='{"description": "Check rental payment", "plot_id": "land_123"}',
    )
    rental_task.codex = rental_codex

    rental_schedule = TaskSchedule(
        _id="schedule_2", cron_expression="0 0 1 * *"  # First day of each month
    )
    rental_schedule.tasks.add(rental_task)

    rental_dispute = Dispute(_id="dispute_1", status="OPEN")

    # Create rental trade and transfer
    rental_trade = Trade(
        _id="trade_2", metadata='{"type": "rental_payment", "month": "February 2024"}'
    )

    # Add a rental payment transfer
    rental_transfer = Transfer(
        _id="transfer_2",
        amount=750,
    )
    rental_transfer.from_user = user2  # Tenant
    rental_transfer.to_user = user1    # Landlord
    rental_transfer.instrument = btc_instrument
    rental_trade.transfer_1 = rental_transfer

    # Example 3: Driving license
    logger.info("Creating driving license example")

    license_task = Task(_id="task_3")

    driver_license = License(_id="license_1")

    fee_instrument = Instrument(_id="instrument_2")

    # Create license trade and transfer
    license_trade = Trade(
        _id="trade_3", metadata='{"type": "license_fee", "receipt": "DL20240001"}'
    )

    # Add a license fee transfer
    license_transfer = Transfer(
        _id="transfer_3",
        amount=200,
    )
    license_transfer.from_user = user2
    license_transfer.to_user = system_user
    license_transfer.instrument = fee_instrument
    license_trade.transfer_1 = license_transfer

    # Example 4: Tax collection
    logger.info("Creating tax collection example")

    tax_codex = Codex(_id="codex_3", code="calculate_tax_for_user(user)")

    tax_task = Task(_id="task_4")
    tax_task.codex = tax_codex

    tax_schedule = TaskSchedule(
        _id="schedule_3", cron_expression="0 0 15 4 *"  # April 15th yearly
    )
    tax_schedule.tasks.add(tax_task)

    tax_instrument = Instrument(_id="instrument_3")

    # Create tax trade and transfer
    tax_trade = Trade(
        _id="trade_4",
        metadata='{"type": "tax_payment", "year": 2024, "status": "paid"}',
    )

    # Add a tax payment transfer
    tax_transfer = Transfer(
        _id="transfer_4",
        amount=1200,
    )
    tax_transfer.from_user = user2
    tax_transfer.to_user = system_user
    tax_transfer.instrument = tax_instrument
    tax_trade.transfer_1 = tax_transfer

    # Additional transfers without trades
    donation_transfer = Transfer(
        _id="transfer_5",
        amount=50,
    )
    donation_transfer.from_user = user1
    donation_transfer.to_user = user2
    donation_transfer.instrument = btc_instrument

    refund_transfer = Transfer(
        _id="transfer_6",
        amount=25,
    )
    refund_transfer.from_user = system_user
    refund_transfer.to_user = user1
    refund_transfer.instrument = fee_instrument

    logger.info("Demo data created successfully")

    logger.info(f"Database dump: {Database.get_instance().raw_dump_json(pretty=True)}")

    return "Demo data loaded successfully"


"""
PYTHONPATH=/home/user/dev/smart-social-contracts/public/realms2/src/realm_backend python src/realm_backend/extensions/demo_loader/demo1.py
"""
if __name__ == "__main__":
    run()
