#!/usr/bin/env python3


from test_utils import run_command, assert_in, assert_file_exists, print_ok

EXTENSION_NAME = "test_bench"

def test_extensions():
    list_before = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_before, "No extensions installed")

    run_command(f"./scripts/realm-extension-cli.py install extensions/{EXTENSION_NAME}.zip")

    list_after = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after, EXTENSION_NAME)

    run_command(f"./scripts/realm-extension-cli.py package {EXTENSION_NAME}")

    assert_file_exists(f"{EXTENSION_NAME}.zip")

    run_command(f"./scripts/realm-extension-cli.py uninstall {EXTENSION_NAME}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")


    run_command(f"./scripts/realm-extension-cli.py install {EXTENSION_NAME}.zip")

    list_after_install = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_install, EXTENSION_NAME)

    run_command(f"./scripts/realm-extension-cli.py uninstall {EXTENSION_NAME}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")

    print_ok("Tests OK")


if __name__ == "__main__":
    test_extensions()
