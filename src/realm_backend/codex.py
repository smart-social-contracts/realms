print("inside the codex")

from ggg import Mandate, User
from kybra_simple_logging import get_logger

logger = get_logger("codex")

cursor = 1
num_users_per_call = 50


def mandate_1_tax_payment():
    # check if citizens have paid their taxes on time
    global cursor

    user_count = User.count()
    logger.info("mandate_1_tax_payment: User.count()" + str(user_count))

    if user_count == 0:
        logger.info("No users found, skipping tax payment processing")
        return

    num_users_processed = 0

    while num_users_processed < num_users_per_call:
        user = User[cursor]
        if user is None:
            logger.info("user[" + str(cursor) + "]: None (user not found)")
            cursor += 1
            if cursor > user_count:
                cursor = 1
            continue

        logger.info("user[" + str(cursor) + "]: " + str(user.serialize()))

        num_users_processed += 1
        cursor += 1
        if cursor > user_count:
            cursor = 1


def run():
    logger.info("run inside codex")

    # TODO: Mandate1: check if citizens have paid their taxes on time
    # TODO: Mandate2: pay any pending subsidies to citizens
    # TODO: Mandate3: pay any pending bills to providers
    mandate_1_tax_payment()


# Execute the main logic
result = "OK"
try:
    run()
except Exception as e:
    result = str(e)

logger.info("codex result: " + result)
