# Instructions for AI-powered developers and agents

1. Do not commit unless you are told to do so.

2. Use `venv`. To set it up:
```bash
python -m venv venv
source venv/bin/active
pip install -r requirements.txt -r requirements-dev.txt
```

3. Use `realms` CLI tool to deploy locally.
To set it up:
```bash
pip install -e cli
```
To deploy locally `realms realm create --deploy` or `realms mundus create --deploy`.

4. Use `scripts/deploy_local_dev.sh` to quickly re-deploy and test your local changes.
