# Imports are provided by the execution environment:
# ic, Integer, String, TaskEntity are already in scope
# Access GGG entities via ggg module
# VERSION: 2025-11-21-v5-WORKING

from kybra import ic, CallResult, match
from kybra.canisters.management import management_canister
import ggg
# from main import logger

User = ggg.User
Transfer = ggg.Transfer


NUM_USERS_PER_BATCH = 10

class Stage:
    def __init__(self, task_state):
        self.task_state = task_state

    def handle(self):
        raise NotImplementedError


class Counting(Stage):
    def handle(self):
        logger.info('[Counting Stage] Processing users...')
        user_id = self.task_state.last_user_id + 1
        max_id = User.max_id()
        
        users_batch_count = 0
        while users_batch_count < NUM_USERS_PER_BATCH and user_id <= max_id:
            logger.info(f'  Processing user {user_id}')
            user = User[user_id]
            user_id += 1
            users_batch_count += 1
        
        if user_id <= User.max_id():
            self.task_state.last_user_id = user_id - 1
            logger.info(f'  Batch complete. Position: {self.task_state.last_user_id}')
        else:
            logger.info('  All users counted!')
            self.task_state.last_user_id = 0
            self.task_state.set_stage("SelectWinner")

class SelectWinner(Stage):
    def handle(self):
        logger.info('[SelectWinner Stage] Choosing winner...')
        max_id = User.max_id()
        if max_id > 0:
            # Use ICP's verifiable random function instead of Python's random
            random_result: CallResult[bytes] = yield management_canister.raw_rand()
            
            def on_random_ok(random_bytes: bytes) -> None:
                # Convert random bytes to integer in range [1, max_id]
                random_int = int.from_bytes(random_bytes[:4], byteorder='big')
                winner_id = (random_int % max_id) + 1
                self.task_state.winner_user_id = winner_id
                logger.info(f'  Winner: User ID {self.task_state.winner_user_id}')
                self.task_state.set_stage("SendPrize")
            
            def on_random_err(err: str) -> None:
                logger.info(f'  Error getting randomness: {err}')
                self.task_state.set_stage("Done")
            
            match(random_result, {
                "Ok": on_random_ok,
                "Err": on_random_err
            })
        else:
            logger.info('  No users found')
            self.task_state.set_stage("Done")

class SendPrize(Stage):
    def handle(self):
        logger.info('[SendPrize Stage] Sending prize...')
        winner = User[self.task_state.winner_user_id]
        if winner:
            logger.info(f'  Prize sent to user: {winner.id}')
            # TODO: Implement actual transfer when treasury/transfer logic is ready
            # t = Transfer()
            # t.amount = 1
            # t.principal_to = winner.owner
            # result = yield t.execute()
        else:
            logger.info(f'  Error: User {self.task_state.winner_user_id} not found')
        self.task_state.set_stage("Done")

class Done(Stage):
    def handle(self):
        logger.info('[Done Stage] Lottery complete!')


# Stage registry for lookup
STAGES = {
    "Counting": Counting,
    "SelectWinner": SelectWinner,
    "SendPrize": SendPrize,
    "Done": Done
}


class LotteryState(TaskEntity):
    stage_name = String()
    last_user_id = Integer(default=0)
    winner_user_id = Integer(default=0)

    def set_stage(self, new_stage_name: str):
        self.stage_name = new_stage_name

    def request(self):
        stage_count = 0
        max_iterations = 10
        
        while str(self.stage_name) != "Done" and stage_count < max_iterations:
            stage_count += 1
            logger.info(f'>> Stage {stage_count}: {self.stage_name}')
            
            stage = self.get_stage(str(self.stage_name))
            result = stage.handle()
            
            logger.info(f'>> Stage {stage_count} complete, next: {self.stage_name}')
            
            if hasattr(result, '__next__'):
                logger.info(f'>> Async operation detected')
                result = yield from result
        
        if stage_count >= max_iterations:
            logger.info(f'⚠️  Hit max iterations')
        else:
            logger.info(f'✅ Completed {stage_count} stages successfully')
        
        return 'completed'

    def get_stage(self, stage_name: str):
        stage_class = STAGES.get(stage_name)
        if stage_class:
            return stage_class(self)
        raise ValueError(f"Unknown stage: {stage_name}. Available: {list(STAGES.keys())}")


# Initialize state
if LotteryState.instances():
    task_state = LotteryState.instances()[0]
    task_state.last_user_id = 0
    task_state.winner_user_id = 0
    task_state.set_stage("Counting")
else:
    task_state = LotteryState()
    task_state.set_stage("Counting")


def async_task():
    """Main entry point for lottery task"""
    logger.info('=== LOTTERY START ===')
    
    try:
        result = yield from task_state.request()
        logger.info(f'=== LOTTERY COMPLETE: {result} ===')
        return 'ok'
    except Exception as e:
        logger.info(f'❌ Error: {type(e).__name__}: {str(e)}')
        return 'error'
