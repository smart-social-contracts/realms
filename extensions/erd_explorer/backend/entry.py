"""
ERD Explorer Extension Backend
Provides entity relationship data and metadata for the ERD visualization
"""

def get_entity_schema():
    """
    Returns the complete entity schema with relationships
    """
    return {
        "entities": {
            "Realm": {
                "fields": ["id", "name", "description", "created_at", "updated_at"],
                "relationships": {
                    "treasury": {"type": "OneToOne", "target": "Treasury", "field": "realm"}
                }
            },
            "User": {
                "fields": ["id", "profile_picture_url", "created_at", "updated_at"],
                "relationships": {
                    "profiles": {"type": "ManyToMany", "target": "UserProfile", "field": "users"},
                    "human": {"type": "OneToOne", "target": "Human", "field": "user"},
                    "citizen": {"type": "OneToOne", "target": "Citizen", "field": "user"},
                    "transfers_from": {"type": "OneToMany", "target": "Transfer", "field": "from_user"},
                    "transfers_to": {"type": "OneToMany", "target": "Transfer", "field": "to_user"},
                    "trades_a": {"type": "OneToMany", "target": "Trade", "field": "user_a"},
                    "trades_b": {"type": "OneToMany", "target": "Trade", "field": "user_b"},
                    "owned_lands": {"type": "OneToMany", "target": "Land", "field": "owner_user"}
                }
            },
            "Human": {
                "fields": ["id", "name", "date_of_birth", "created_at", "updated_at"],
                "relationships": {
                    "user": {"type": "OneToOne", "target": "User", "field": "human"},
                    "identities": {"type": "OneToMany", "target": "Identity", "field": "human"}
                }
            },
            "Identity": {
                "fields": ["id", "type", "metadata", "created_at", "updated_at"],
                "relationships": {
                    "human": {"type": "ManyToOne", "target": "Human", "field": "identities"}
                }
            },
            "Citizen": {
                "fields": ["id", "created_at", "updated_at"],
                "relationships": {
                    "user": {"type": "OneToOne", "target": "User", "field": "citizen"}
                }
            },
            "Organization": {
                "fields": ["id", "name", "created_at", "updated_at"],
                "relationships": {}
            },
            "Codex": {
                "fields": ["id", "name", "code", "url", "checksum", "created_at", "updated_at"],
                "relationships": {
                    "call": {"type": "OneToOne", "target": "Call", "field": "codex"}
                }
            },
            "Task": {
                "fields": ["id", "name", "description", "created_at", "updated_at"],
                "relationships": {}
            },
            "Transfer": {
                "fields": ["id", "amount", "created_at", "updated_at"],
                "relationships": {
                    "from_user": {"type": "ManyToOne", "target": "User", "field": "transfers_from"},
                    "to_user": {"type": "ManyToOne", "target": "User", "field": "transfers_to"}
                }
            },
            "Trade": {
                "fields": ["id", "created_at", "updated_at"],
                "relationships": {
                    "user_a": {"type": "ManyToOne", "target": "User", "field": "trades_a"},
                    "user_b": {"type": "ManyToOne", "target": "User", "field": "trades_b"}
                }
            },
            "Instrument": {
                "fields": ["id", "name", "symbol", "created_at", "updated_at"],
                "relationships": {}
            },
            "Mandate": {
                "fields": ["id", "name", "created_at", "updated_at"],
                "relationships": {}
            },
            "Dispute": {
                "fields": ["id", "case_id", "created_at", "updated_at"],
                "relationships": {}
            },
            "License": {
                "fields": ["id", "name", "created_at", "updated_at"],
                "relationships": {}
            },
            "Proposal": {
                "fields": ["id", "title", "created_at", "updated_at"],
                "relationships": {}
            },
            "Vote": {
                "fields": ["id", "choice", "created_at", "updated_at"],
                "relationships": {}
            },
            "Treasury": {
                "fields": ["id", "created_at", "updated_at"],
                "relationships": {
                    "realm": {"type": "OneToOne", "target": "Realm", "field": "treasury"}
                }
            }
        }
    }

def get_entity_counts():
    """
    Returns mock entity counts for visualization
    """
    return {
        "Realm": 1,
        "User": 150,
        "Human": 150,
        "Identity": 300,
        "Citizen": 120,
        "Organization": 25,
        "Codex": 8,
        "Task": 12,
        "Transfer": 450,
        "Trade": 75,
        "Instrument": 6,
        "Mandate": 5,
        "Dispute": 3,
        "License": 18,
        "Proposal": 7,
        "Vote": 42,
        "Treasury": 1
    }
