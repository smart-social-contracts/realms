import json

IGNORE_TAG = '<IGNORE>'


def compare_json(expected, actual, route='/'):
    """
    Compares two JSON objects, ignoring fields with value IGNORE_TAG in the expected JSON.

    Args:
        expected (dict): The expected JSON object.
        actual (dict): The actual JSON object.

    Returns:
        bool: True if the objects match, False otherwise.
    """

    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, expected_value in expected.items():
            if key not in actual:
                print(f"[{route}] Key '{key}' missing in actual JSON")
                return False
            if expected_value == IGNORE_TAG:
                if actual.get(key) == None:
                    print(f"[{route}] Key '{key}' missing in actual JSON")
                    return False
                continue
            if not compare_json(expected_value, actual[key], route + '/%s' % key):
                print(f"[{route}] Mismatch found for key '{key}': Expected {expected_value}, got {actual[key]}")
                return False
        return True
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            print(f"[{route}] List length mismatch: Expected {len(expected)}, got {len(actual)}")
            return False
        for i, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            if not compare_json(expected_item, actual_item, route + '/%d' % i):
                print(f"[{route}] Mismatch found in list at index {i}: Expected {expected_item}, got {actual_item}")
                return False
        return True
    else:
        if expected == actual:
            return True
        else:
            print('Mismatch found: Expected %s, got %s' % (expected, actual))
            return False


def parse_dfx_answer(content: str) -> dict:
    content = content.strip()[2:-2].strip(",").strip().strip('"')
    content = content.replace('\\"', '"')
    content = content.replace('\\\\', '\\')
    content = content.replace("\\'", "'")
    return json.loads(content)
