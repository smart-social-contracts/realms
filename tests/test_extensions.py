#!/usr/bin/env python3


from test_utils import assert_file_exists, assert_in, print_ok, run_command

EXTENSION_NAMES = ["test_bench", "vault_manager", "demo_loader"]


def test_extensions():
    list_after = run_command("./scripts/realm-extension-cli.py list")
    for name in EXTENSION_NAMES:
        assert_in(list_after, name)

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py package {name}")

    for name in EXTENSION_NAMES:
        assert_file_exists(f"{name}.zip")

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py uninstall {name}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py install {name}.zip")

    list_after_install = run_command("./scripts/realm-extension-cli.py list")
    for name in EXTENSION_NAMES:
        assert_in(list_after_install, name)

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py uninstall {name}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")

    print_ok("Tests OK")


if __name__ == "__main__":
    test_extensions()
