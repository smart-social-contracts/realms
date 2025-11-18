#!/usr/bin/env python3


import os

from test_utils import assert_file_exists, assert_in, print_ok, run_command


def get_extension_names():
    """Discover all extensions from the extensions directory"""
    extensions_dir = "extensions"
    if not os.path.exists(extensions_dir):
        return []

    return [
        name
        for name in os.listdir(extensions_dir)
        if os.path.isdir(os.path.join(extensions_dir, name))
        and not name.startswith(".")
        and not name.startswith("__")
        and os.path.exists(os.path.join(extensions_dir, name, "manifest.json"))
    ]


def test_extensions():
    EXTENSION_NAMES = get_extension_names()

    if not EXTENSION_NAMES:
        raise RuntimeError("No extensions found in extensions/ directory")

    print(
        f"Found {len(EXTENSION_NAMES)} extensions: {', '.join(sorted(EXTENSION_NAMES))}"
    )

    # Get absolute path to extensions directory
    extensions_dir = os.path.abspath("extensions")

    for name in EXTENSION_NAMES:
        run_command(f"realms extension uninstall --extension-id {name} || true")

    current_list = run_command("realms extension list")
    if "No extensions installed" not in current_list:
        lines = current_list.strip().split("\n")
        for line in lines[2:]:  # Skip header lines
            if line.strip() and not line.startswith("-"):
                extension_id = line.split()[0]
                if extension_id and extension_id != "ID":
                    run_command(
                        f"realms extension uninstall --extension-id {extension_id} || true"
                    )

    run_command(f"realms extension install-from-source --source-dir {extensions_dir}")

    list_after = run_command("realms extension list")
    for name in EXTENSION_NAMES:
        assert_in(list_after, name)

    for name in EXTENSION_NAMES:
        ext_source = os.path.join(extensions_dir, name)
        output_path = os.path.abspath(f"{name}.zip")
        run_command(
            f"realms extension package --extension-id {name} --source-dir {ext_source} --package-path {output_path}"
        )

    for name in EXTENSION_NAMES:
        assert_file_exists(f"{name}.zip")

    for name in EXTENSION_NAMES:
        run_command(f"realms extension uninstall --extension-id {name}")

    list_after_uninstall = run_command("realms extension list")
    assert_in(list_after_uninstall, "No extensions installed")

    for name in EXTENSION_NAMES:
        result = run_command(f"realms extension install --package-path {name}.zip")
        if result is None:
            raise RuntimeError(f"Failed to install {name}.zip")

        # Check files based on what exists in source
        backend_src = f"extensions/{name}/backend"
        frontend_lib_src = f"extensions/{name}/frontend/lib"
        i18n_src = f"extensions/{name}/frontend/i18n"

        if os.path.exists(backend_src):
            assert_file_exists(f"src/realm_backend/extension_packages/{name}/entry.py")
            assert_file_exists(
                f"src/realm_backend/extension_packages/{name}/manifest.json"
            )

        if os.path.exists(frontend_lib_src):
            assert_file_exists(f"src/realm_frontend/src/lib/extensions/{name}/index.ts")

        if os.path.exists(i18n_src):
            assert_file_exists(
                f"src/realm_frontend/src/lib/i18n/locales/extensions/{name}/en.json"
            )

    list_after_install = run_command("realms extension list")
    for name in EXTENSION_NAMES:
        assert_in(list_after_install, name)

    # Verify extension_imports.py was updated correctly
    with open("src/realm_backend/extension_packages/extension_imports.py", "r") as f:
        imports_content = f.read()

    for name in EXTENSION_NAMES:
        if os.path.exists(f"extensions/{name}/backend"):
            assert_in(imports_content, f"import extension_packages.{name}.entry")

    # Test uninstalling again
    for name in EXTENSION_NAMES:
        run_command(f"realms extension uninstall --extension-id {name}")

    list_after_uninstall = run_command("realms extension list")
    assert_in(list_after_uninstall, "No extensions installed")

    print_ok("Tests OK")


if __name__ == "__main__":
    test_extensions()
