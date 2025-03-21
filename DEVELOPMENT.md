
## Core development

1. **Installation**
   ```bash
   git clone <repository-url>
   cd app
   ./setup.sh
   ```

## Development

If you want to contribute on this repo, this may be useful. You can run the code in the following ways:

with/without docker
with/without IC

without docker, you need to install all dependencies on your workstation
without IC, it is faster to launch and easier to debug

In practice, I work in one of these modes:

a. without docker without IC - For development on non-IC functionality
   ./scripts/install_kybra_simple_db.sh
   TEST_LOCAL=1 ./run_tests.sh   (+server to not running tests)
   yarn start

b. without docker with IC - For specific troubleshooting/development on the IC side
   ./scripts/install_kybra_simple_db.sh
   ./setup.sh
   pytest

c. with docker with IC - For final full test running
   ./scripts/install_kybra_simple_db.sh
   ./run_tests.sh


3. **CLI Tool**
   ```bash
   # Create symbolic link for convenient CLI access
   sudo ln -s $PWD/app/src/canister_main/cli.py /usr/local/bin/ggg
   ```

   Example of use:


   Get all objects in the backend:
   ```
   ggg parse_dfx <(dfx canister call canister_main get_universe) > get_universe_output.json
   ```
   
4. **Testing**
   ```bash
   ./run_tests.sh
   ```
