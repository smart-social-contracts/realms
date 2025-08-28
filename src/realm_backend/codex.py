
from ggg import Mandate, User
from kybra_simple_logging import get_logger

logger = get_logger("codex")


cursor = 1
num_users_per_call = 50

def mandate_1_tax_payment():
    # check if citizens have paid their taxes on time

    global cursor

    logger.info(f"mandate_1_tax_payment: User.count(): {User.count()}")

    num_users_processed = 0

    while num_users_processed < num_users_per_call:
        user = User[cursor]
        logger.info(f"user[{cursor}]: {user.to_dict()}")

        num_users_processed += 1
        cursor += 1
        if cursor > User.count():
            cursor = 1

def run():

    # TODO: Mandate1: check if citizens have paid their taxes on time
    # TODO: Mandate2: pay any pending subsidies to citizens
    # TODO: Mandate3: pay any pending bills to providers
    mandate_1_tax_payment()




    
