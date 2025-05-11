import json

from core.utils import running_on_ic


def log(text: str):
    print(text)


if running_on_ic():
    from kybra import ic

    def log(text: str):
        ic.print(text)


def json_dumps(data):
    return json.dumps(data, sort_keys=True)
