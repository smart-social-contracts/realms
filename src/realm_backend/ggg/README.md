# Examples



Realm rents out a land plot to organization for a period of time
Driving license issuance, renovation and revocation




Organization(
    justice administrator
)

Organization(
    justice executor
)




Mandate(
    name="land_lease_policy",
    description="Allows organization ABC to rent the land plot in (X,Y) for 1 year.",
    category="land",
    governed_by="land_law_2024"
)

Proposal(
    name="land_lease_policy",
    description="Allows organization ABC to rent the land plot in (X,Y) for 1 year.",
    category="land",
    governed_by="land_law_2024"
)

Contract(
    mandate="land_lease_policy",
    status="active",
    metadata="{}"
)

12 x
Trade(
    user_a="user_a",
    user_b="user_b",
    instruments_a=["instrument_a"],
    instruments_b=["instrument_b"],
    mandate="land_lease_policy",
    metadata="{}"
)

Dispute(
    trade="trade_1",
    status="pending",
    metadata="{}"
)

Contract(
    # between the claimant and the justice administrator
) 