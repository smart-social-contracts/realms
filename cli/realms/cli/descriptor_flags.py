"""Deployment-descriptor parameter names → runtime test-flag keys.

Single source of truth for TEST_MODE_* YAML parameters used in
deployment-descriptors/*-mundus-layered.yml and consumed by mundus deploy,
CI install, and Casals arrangement generation.
"""

TEST_PARAM_MAP: dict[str, str] = {
    "TEST_MODE": "test_mode",
    "TEST_MODE_II_BYPASS": "ii_bypass",
    "TEST_MODE_USER_SELF_REGISTRATION": "user_self_registration",
    "TEST_MODE_DEMO_DATA": "demo_data",
    "TEST_MODE_SKIP_TERMS": "skip_terms",
    "TEST_MODE_SKIP_PASSPORT_ZKPROOF": "skip_passport_zkproof",
    "TEST_MODE_DISABLE_MONETARY_TOKENS": "disable_monetary_tokens",
    "TEST_MODE_DEMO_NOTICE": "demo_notice",
}
