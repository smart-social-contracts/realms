# Fresh lottery codex with fixed async flow
# VERSION: 2025-11-21-v5-FRESH

from kybra import ic, CallResult, match
from kybra.canisters.management import management_canister
import ggg

User = ggg.User

NUM_USERS_PER_BATCH = 10

class Stage:
    def __init__(self, task_state):
        self.task_state = task_state
    
    def handle(self):
        raise NotImplementedError


class Counting(Stage):
    def handle(self):
        ic.print('[Counting Stage] Processing users...')
        user_id = self.task_state.last_user_id + 1
        max_id = User.max_id()
        
        users_batch_count = 0
        while users_batch_count < NUM_USERS_PER_BATCH and user_id <= max_id:
            ic.print(f'  Processing user {user_id}')
            user = User[user_id]
            user_id += 1
            users_batch_count += 1
        
        if user_id <= User.max_id():
            self.task_state.last_user_id = user_id - 1
            ic.print(f'  Batch complete. Position: {self.task_state.last_user_id}')
        else:
            ic.print('  All users counted!')
            self.task_state.last_user_id = 0
            self.task_state.set_stage("SelectWinner")


class SelectWinner(Stage):
    def handle(self):
        ic.print('[SelectWinner Stage] Choosing winner...')
        max_id = User.max_id()
        if max_id > 0:
            # Use ICP's verifiable random function instead of Python's random
            random_result: CallResult[bytes] = yield management_canister.raw_rand()
            
            def on_random_ok(random_bytes: bytes) -> None:
                # Convert random bytes to integer in range [1, max_id]
                random_int = int.from_bytes(random_bytes[:4], byteorder='big')
                winner_id = (random_int % max_id) + 1
                self.task_state.winner_user_id = winner_id
                ic.print(f'  Winner: User ID {self.task_state.winner_user_id}')
                self.task_state.set_stage("SendPrize")
            
            def on_random_err(err: str) -> None:
                ic.print(f'  Error getting randomness: {err}')
                self.task_state.set_stage("Done")
            
            match(random_result, {
                "Ok": on_random_ok,
                "Err": on_random_err
            })
        else:
            ic.print('  No users found')
            self.task_state.set_stage("Done")


class SendPrize(Stage):
    def handle(self):
        ic.print('[SendPrize Stage] Sending prize...')
        winner = User[self.task_state.winner_user_id]
        if winner:
            ic.print(f'  Prize sent to user: {winner.id}')
        else:
            ic.print(f'  Error: User {self.task_state.winner_user_id} not found')
        self.task_state.set_stage("Done")


class Done(Stage):
    def handle(self):
        ic.print('[Done Stage] Lottery complete!')


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
            ic.print(f'>> Stage {stage_count}: {self.stage_name}')
            
            stage = self.get_stage(str(self.stage_name))
            result = stage.handle()
            
            ic.print(f'>> Stage {stage_count} complete, next: {self.stage_name}')
            
            if hasattr(result, '__next__'):
                ic.print(f'>> Async operation detected')
                result = yield from result
        
        if stage_count >= max_iterations:
            ic.print(f'⚠️  Hit max iterations')
        else:
            ic.print(f'✅ Completed {stage_count} stages successfully')
        
        return 'completed'
    
    def get_stage(self, stage_name: str):
        stage_class = globals().get(stage_name)
        if stage_class and isinstance(stage_class, type) and issubclass(stage_class, Stage):
            return stage_class(self)
        raise ValueError(f"Unknown stage: {stage_name}")


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
    ic.print('=== LOTTERY V2 START ===')
    
    try:
        result = yield from task_state.request()
        ic.print(f'=== LOTTERY V2 COMPLETE: {result} ===')
        return 'ok'
    except Exception as e:
        ic.print(f'❌ Error: {type(e).__name__}: {str(e)}')
        return 'error'
