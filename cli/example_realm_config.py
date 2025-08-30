
from ggg import Codex, Task

print("Creating codex")

c = Codex()
c.name = "Subsidy Distribution System"
c.description = "Automated distribution of subsidies and benefits to eligible citizens"
c.url = "https://raw.githubusercontent.com/smart-social-contracts/realms/refs/heads/main/src/realm_backend/codex.py"
c.checksum = "sha256:e45a166550a08eb872e3c14f517dc5b200cae354ee44cc07779d250dbbf4e575"


print("Downloading code")
from main import download_code_from_url
(_, code) = download_code_from_url(c.url, c.checksum)

print("Setting code")
c.code = code
print("Code: " + c.code)

print("Creating task")

task = Task()
task.name = "Subsidy Distribution System"
task.description = "Automated distribution of subsidies and benefits to eligible citizens"
task.codex = c

print("Running task")
task.run()

print("Task completed")

