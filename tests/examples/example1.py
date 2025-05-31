from ggg import Mandate, Task, User, TaskSchedule, Codex
import os

user_old = User(name="John Doe")
user_young = User(name="Jane Doe")

mandate = Mandate(name="pensions")


ts = TaskSchedule(_id="end_of_month", cron_expression="0 0 L * *")  # every end of month
# Use the directory of the current file to locate tax_codex.py
current_dir = os.path.dirname(os.path.abspath(__file__))
codex_path = os.path.join(current_dir, "tax_codex.py")
task = Task(
    _id="pay_pensions", schedules=[ts], codex=Codex(code=open(codex_path).read())
)

task.run()
