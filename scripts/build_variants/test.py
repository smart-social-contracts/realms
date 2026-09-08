"""Build variant: test. GENERATED FILE — do not edit in place.

Source of truth: ``scripts/build_variants/test.py``. See the production variant
for how the swap works.

This variant enables the test-only code paths. It must never be deployed to a
production network. Two things make that visible rather than a matter of
discipline: ``status()`` reports ``build_variant``, and the WASM contains
``TEST_BUILD_SENTINEL`` below, which the packer refuses to find in a production
artifact.
"""

BUILD_VARIANT = "test"

# Deliberately a literal so it survives into the WASM's data section, where
# scripts/pack_realm_backend.py can find it by byte-scanning the artifact.
TEST_BUILD_SENTINEL = "REALMS_TEST_BUILD_AUTH_BYPASS"


def is_test_build() -> bool:
    return True


def ii_bypass_available() -> bool:
    """Whether Internet Identity may be bypassed with a deterministic keypair."""
    return True


def test_flags_available() -> bool:
    """Whether runtime test flags may be enabled at all in this build."""
    return True
