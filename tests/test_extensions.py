#!/usr/bin/env python3


import os

from test_utils import assert_file_exists, assert_in, print_ok, run_command

EXTENSION_NAMES = [
    "vault_manager",
    "demo_loader",
    "citizen_dashboard",
    "llm_chat",
    "passport_verification",
    "land_registry",
    "justice_litigation",
    "notifications",
]


def test_extensions():
    list_after = run_command("./scripts/realm-extension-cli.py list")
    for name in EXTENSION_NAMES:
        assert_in(list_after, name)

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py package --extension-id {name}")

    for name in EXTENSION_NAMES:
        assert_file_exists(f"{name}.zip")

    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py uninstall --extension-id {name}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")

    for name in EXTENSION_NAMES:
        run_command(
            f"./scripts/realm-extension-cli.py install --package-path {name}.zip"
        )
        # Verify files exist in the new extension_packages directory
        assert_file_exists(f"src/realm_backend/extension_packages/{name}/entry.py")
        assert_file_exists(f"src/realm_backend/extension_packages/{name}/manifest.json")

    list_after_install = run_command("./scripts/realm-extension-cli.py list")
    for name in EXTENSION_NAMES:
        assert_in(list_after_install, name)

    # Verify extension_imports.py was updated correctly
    with open("src/realm_backend/extension_packages/extension_imports.py", "r") as f:
        imports_content = f.read()

    for name in EXTENSION_NAMES:
        assert_in(imports_content, f"import extension_packages.{name}.entry")

    # Test uninstalling again
    for name in EXTENSION_NAMES:
        run_command(f"./scripts/realm-extension-cli.py uninstall --extension-id {name}")

    list_after_uninstall = run_command("./scripts/realm-extension-cli.py list")
    assert_in(list_after_uninstall, "No extensions installed")

    print_ok("Tests OK")


if __name__ == "__main__":
    test_extensions()
