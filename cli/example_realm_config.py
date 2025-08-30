from ggg import Codex, Task
from main import download_code_from_url

print("Creating codex")

c = Codex()
c.name = "Subsidy Distribution System"
c.description = "Automated distribution of subsidies and benefits to eligible citizens"
c.url = "https://raw.githubusercontent.com/smart-social-contracts/realms/refs/heads/main/src/realm_backend/codex.py"
c.checksum = "sha256:e45a166550a08eb872e3c14f517dc5b200cae354ee44cc07779d250dbbf4e575"

print("Downloading code")

# The async function returns a generator in the execution environment
download_generator = download_code_from_url(c.url, c.checksum)

try:
    # Try to get the result from the generator
    success, result = next(download_generator)
    
    if success:
        print("Setting code")
        c.code = result
        print("Code downloaded successfully")
    else:
        print("Error downloading code: " + result)
        
except Exception as e:
    print(f"Error during download: {str(e)}")
    success = False

if success:
    print("Creating task")
    task = Task()
    task.name = "Subsidy Distribution System"
    task.description = "Automated distribution of subsidies and benefits to eligible citizens"
    task.codex = c
    
    print("Running task")
    task.run()
    print("Task completed")
else:
    print("Failed to download code, skipping task execution")