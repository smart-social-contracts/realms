#!/usr/bin/env python3
import json
import os
import sys

backend_path = os.path.join(os.path.dirname(__file__), "src", "realm_backend")
sys.path.insert(0, backend_path)

try:
    from api.extensions import list_extensions

    print("Testing backend extensions API...")
    result = list_extensions()

    print(f"API call success: {result['success']}")

    if result["success"] and "ExtensionsList" in result["data"]:
        extensions_json = result["data"]["ExtensionsList"]["extensions"]
        extensions = [json.loads(ext) for ext in extensions_json]

        print(f"Found {len(extensions)} extensions:")

        categories_found = {}
        for ext in extensions:
            name = ext.get("name", "Unknown")
            categories = ext.get("categories", ["other"])
            print(f"  - {name}: categories={categories}")

            for category in categories:
                if category not in categories_found:
                    categories_found[category] = []
                categories_found[category].append(name)

        print("\nExtensions grouped by category:")
        for category, ext_names in categories_found.items():
            print(f"  {category}: {ext_names}")

        expected_categories = {
            "public_services": ["citizen_dashboard"],
            "finances": ["vault"],
            "identity": ["passport_verification"],
        }

        print("\nValidating expected categorizations:")
        for expected_cat, expected_exts in expected_categories.items():
            if expected_cat in categories_found:
                found_exts = categories_found[expected_cat]
                for expected_ext in expected_exts:
                    if expected_ext in found_exts:
                        print(f"  ✅ {expected_ext} correctly in {expected_cat}")
                    else:
                        print(f"  ❌ {expected_ext} NOT found in {expected_cat}")
            else:
                print(f"  ❌ Category {expected_cat} not found")

    else:
        print(f"Error or no extensions data: {result['data']}")

except Exception as e:
    print(f"Error testing extensions API: {str(e)}")
    import traceback

    traceback.print_exc()
