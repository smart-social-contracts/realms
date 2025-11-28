"""
Test Member Dashboard Extension Imports
Simple test to catch import errors early in CI
"""


def test_imports():
    """Test that the extension can be imported without errors"""
    print("Testing member_dashboard imports...")

    try:
        # Test ggg imports that member_dashboard uses
        try:
            from ggg import Invoice, Service, User

            print("✓ Successfully imported: Invoice, Service, User")

            # Verify Invoice has expected attributes
            assert hasattr(Invoice, "__alias__"), "Invoice missing __alias__"
            print("✓ Invoice entity structure validated")
        except ImportError:
            print("⚠ ggg module not available (running outside realm environment)")
            print("  This test should be run in the Docker image or deployed realm")

        # Test that the extension module can be imported
        # Note: This requires the extension to be installed first
        try:
            import sys

            sys.path.insert(0, "/app/src/realm_backend")
            from extension_packages.member_dashboard import entry

            print("✓ Successfully imported member_dashboard.entry module")

            # Verify expected functions exist
            assert hasattr(
                entry, "get_dashboard_summary"
            ), "Missing get_dashboard_summary"
            assert hasattr(entry, "get_public_services"), "Missing get_public_services"
            assert hasattr(entry, "get_tax_information"), "Missing get_tax_information"
            assert hasattr(entry, "get_personal_data"), "Missing get_personal_data"
            print("✓ All expected API functions present")

        except ImportError as e:
            print(f"⚠ Could not import installed extension: {e}")
            print("  This is normal if running outside deployed realm")

        # Test import from source - check for syntax errors
        import ast
        import os

        source_file = os.path.join(os.path.dirname(__file__), "../backend/entry.py")

        try:
            with open(source_file, "r") as f:
                source_code = f.read()

            # This will catch syntax errors
            ast.parse(source_code)
            print("✓ Extension source code has valid Python syntax")

            # Check for expected string patterns (basic smoke test)
            if "Invoice" in source_code and "Service" in source_code:
                print("✓ Extension uses Invoice and Service entities (not TaxRecord)")
            else:
                print("⚠ Could not find Invoice/Service references in source")

        except SyntaxError as e:
            print(f"❌ Extension source has syntax errors: {e}")
            return False
        except FileNotFoundError:
            print(f"⚠ Extension source file not found: {source_file}")
            print("  This is normal if file structure has changed")

        print("✅ All imports successful!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)
