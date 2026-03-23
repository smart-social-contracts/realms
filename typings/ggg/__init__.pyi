"""
Type stubs for the GGG (Generalized Global Governance) entity framework.

These stubs provide autocomplete, type checking, and inline documentation
for all GGG entities when writing codex files. Place this in your stub path
and configure pyrightconfig.json or VS Code settings accordingly.

Entity API Quick Reference:
    # Create
    user = User(id="alice", profile_picture_url="https://...")

    # Lookup by alias (bracket syntax)
    user = User["alice"]          # Returns User or None

    # Load by internal _id
    user = User.load("42")        # Returns User or None

    # List all
    all_users = User.instances()  # Returns List[User]

    # Count
    n = User.count()              # Returns int

    # Find by field match
    results = User.find({"id": "alice"})  # Returns List[User]

    # Delete
    user.delete()

Field size limits (important for avoiding ValueError):
    - String()            — unlimited
    - String(max_length=N) — N characters max
    - Proposal.metadata   — 256 chars  (use for tags only!)
    - Proposal.description — 2048 chars (use for structured data)
    - Invoice.metadata    — 256 chars
    - Notification.message — 2048 chars

ManyToOne relationships:
    ⚠️  In shell execution context, passing Entity objects to ManyToOne
    fields causes "Object of type X is not JSON serializable".
    Workaround: store entity IDs as strings in metadata instead.
"""

from typing import ClassVar, Dict, Iterator, List, Optional, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Entity base class
# ---------------------------------------------------------------------------

class Entity:
    """Base class for all GGG entities.

    Provides auto-generated sequential IDs, persistence, alias-based lookups,
    relationship management, and query methods.
    """

    _id: str
    """Internal sequential ID (auto-generated: "1", "2", "3", ...)"""

    _type: str
    """Entity type name (e.g., "User", "Proposal")"""

    _loaded: bool
    """True if loaded from DB, False if newly created"""

    timestamp_created: Optional[str]
    """ISO timestamp when entity was created (from TimestampedMixin)"""

    timestamp_updated: Optional[str]
    """ISO timestamp when entity was last updated (from TimestampedMixin)"""

    creator: Optional[str]
    """Principal ID of the entity creator"""

    updater: Optional[str]
    """Principal ID of the last updater"""

    owner: Optional[str]
    """Principal ID of the entity owner"""

    def __init__(self, **kwargs) -> None:
        """Create a new entity. All fields can be passed as keyword arguments."""
        ...

    def __class_getitem__(cls, alias_value: str) -> Optional["Entity"]:
        """Lookup entity by alias value. Returns entity or None.

        Example: User["alice"], Proposal["budget_fy2026"]
        """
        ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Entity"]:
        """Load an entity by its internal _id. Returns entity or None."""
        ...

    @classmethod
    def instances(cls) -> List["Entity"]:
        """Get all instances of this entity type."""
        ...

    @classmethod
    def count(cls) -> int:
        """Get the total count of entities of this type."""
        ...

    @classmethod
    def max_id(cls) -> int:
        """Get the maximum _id assigned to entities of this type."""
        ...

    @classmethod
    def find(cls, d: dict) -> List["Entity"]:
        """Find entities matching all key=value pairs in d."""
        ...

    @classmethod
    def load_some(cls, from_id: int, count: int = 10) -> List["Entity"]:
        """Load a range of entities by _id, starting from from_id."""
        ...

    def delete(self) -> None:
        """Delete this entity from the database."""
        ...

    def serialize(self) -> dict:
        """Serialize entity to a dictionary."""
        ...


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Entity):
    """User entity — represents an IC principal registered in the realm.

    Alias: ``id`` (lookup via ``User["principal_id"]``)
    """

    id: Optional[str]
    """IC principal ID (also the alias for bracket lookups)"""

    profile_picture_url: Optional[str]
    """URL to the user's profile picture (max 512 chars)"""

    profiles: List["UserProfile"]
    """ManyToMany: user profiles / roles assigned to this user"""

    human: Optional["Human"]
    """OneToOne: linked Human identity record"""

    member: Optional["Member"]
    """OneToOne: linked Member citizenship record"""

    proposals: List["Proposal"]
    """OneToMany: proposals submitted by this user"""

    votes: List["Vote"]
    """OneToMany: votes cast by this user"""

    notifications: List["Notification"]
    """OneToMany: notifications for this user"""

    services: List["Service"]
    """OneToMany: services associated with this user"""

    disputes_requested: List["Dispute"]
    """OneToMany: disputes filed by this user"""

    disputes_defendant: List["Dispute"]
    """OneToMany: disputes where this user is defendant"""

    payment_accounts: List["PaymentAccount"]
    """OneToMany: payment accounts owned by this user"""

    invoices: List["Invoice"]
    """OneToMany: invoices associated with this user"""

    zones: List["Zone"]
    """OneToMany: geographic zones of influence"""

    def __init__(
        self,
        *,
        id: Optional[str] = ...,
        profile_picture_url: Optional[str] = ...,
        profiles: Optional[List["UserProfile"]] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["User"]: ...
    @classmethod
    def instances(cls) -> List["User"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["User"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["User"]: ...


# ---------------------------------------------------------------------------
# Member
# ---------------------------------------------------------------------------

class Member(Entity):
    """Member entity — citizenship/membership record for a User.

    Alias: ``id``

    ⚠️  No ``metadata`` field. Use ``criminal_record`` for extra data if needed.
    """

    id: Optional[str]
    """Member ID (alias for bracket lookups)"""

    user: Optional[User]
    """OneToOne: the User this membership belongs to"""

    residence_permit: Optional[str]
    """Residence permit status"""

    tax_compliance: Optional[str]
    """Tax compliance status (e.g., 'compliant', 'under_review')"""

    identity_verification: Optional[str]
    """Identity verification status (e.g., 'verified', 'pending', 'rejected', 'revoked')"""

    voting_eligibility: Optional[str]
    """Voting eligibility (e.g., 'eligible', 'ineligible')"""

    public_benefits_eligibility: Optional[str]
    """Benefits eligibility (e.g., 'eligible', 'ineligible')"""

    criminal_record: Optional[str]
    """Criminal record field — also used to store zk_identity_hash"""

    def __init__(
        self,
        *,
        id: Optional[str] = ...,
        user: Optional[User] = ...,
        residence_permit: Optional[str] = ...,
        tax_compliance: Optional[str] = ...,
        identity_verification: Optional[str] = ...,
        voting_eligibility: Optional[str] = ...,
        public_benefits_eligibility: Optional[str] = ...,
        criminal_record: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Member"]: ...
    @classmethod
    def instances(cls) -> List["Member"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Member"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Member"]: ...


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------

class Proposal(Entity):
    """Governance proposal entity for voting system.

    Alias: ``proposal_id`` (lookup via ``Proposal["budget_fy2026"]``)

    ⚠️  ``metadata`` is max 256 chars — use for tags only (e.g., "branch:budget").
    Store structured data in ``description`` (max 2048 chars).
    """

    proposal_id: Optional[str]
    """Proposal identifier (max 64 chars) — THIS is the alias, not .id"""

    title: Optional[str]
    """Proposal title (max 256 chars)"""

    description: Optional[str]
    """Proposal description or structured data as JSON (max 2048 chars)"""

    code_url: Optional[str]
    """URL to proposal code (max 512 chars)"""

    code_checksum: Optional[str]
    """SHA-256 checksum of proposal code (max 128 chars)"""

    proposer: Optional[User]
    """ManyToOne: User who submitted this proposal"""

    status: Optional[str]
    """Proposal status (max 32 chars): debate, enacted, rejected, etc."""

    voting_deadline: Optional[str]
    """ISO timestamp for voting deadline (max 64 chars)"""

    votes_yes: Optional[float]
    """Number of yes votes"""

    votes_no: Optional[float]
    """Number of no votes"""

    votes_abstain: Optional[float]
    """Number of abstain votes"""

    total_voters: Optional[float]
    """Total number of eligible voters"""

    required_threshold: Optional[float]
    """Required vote threshold for passage"""

    metadata: Optional[str]
    """Short metadata string (⚠️  max 256 chars!)"""

    def __init__(
        self,
        *,
        proposal_id: Optional[str] = ...,
        title: Optional[str] = ...,
        description: Optional[str] = ...,
        code_url: Optional[str] = ...,
        code_checksum: Optional[str] = ...,
        proposer: Optional[User] = ...,
        status: Optional[str] = ...,
        voting_deadline: Optional[str] = ...,
        votes_yes: Optional[float] = ...,
        votes_no: Optional[float] = ...,
        votes_abstain: Optional[float] = ...,
        total_voters: Optional[float] = ...,
        required_threshold: Optional[float] = ...,
        metadata: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Proposal"]: ...
    @classmethod
    def instances(cls) -> List["Proposal"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Proposal"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Proposal"]: ...


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice(Entity):
    """Invoice entity — denominated in the realm's accounting currency.

    Alias: ``id`` (auto-generated as ``inv_XXXXXXXXXXXX`` if not provided)

    Multi-currency: invoices are denominated in accounting currency (e.g., ckUSDC).
    Payments can arrive in any registered Token; FX rates convert to accounting
    currency equivalent on refresh.

    ⚠️  ``metadata`` is max 256 chars.
    ⚠️  ``recipient`` is ManyToOne(User) — may cause serialization issues in shell.
    """

    id: Optional[str]
    """Invoice ID (max 32 chars, auto-generated if not provided)"""

    amount: Optional[float]
    """Amount in accounting currency (e.g., 10.00 ckUSDC)"""

    currency: Optional[str]
    """Accounting currency symbol (max 16 chars, default: 'ckBTC')"""

    due_on: Optional[str]
    """ISO timestamp for due date (max 64 chars) — NOT 'due_date'!"""

    status: Optional[str]
    """Invoice status (max 32 chars): Pending, Paid, Overdue, Warned, Defaulted"""

    recipient: Optional[User]
    """ManyToOne: User who should pay this invoice
    ⚠️  Passing User object may cause serialization error in shell context"""

    payer: Optional[User]
    """ManyToOne: User who paid this invoice"""

    transfers: List["Transfer"]
    """OneToMany: transfers that paid this invoice"""

    paid_on: Optional[str]
    """ISO timestamp when paid (max 64 chars)"""

    type: Optional[str]
    """Invoice type (max 32 chars): monthly_dues, tax, fine, etc."""

    metadata: Optional[str]
    """Short metadata string (⚠️  max 256 chars!)"""

    # Multi-currency payment fields (populated on payment)
    payment_currency: Optional[str]
    """Token symbol actually used to pay (e.g., 'ckBTC') (max 16 chars)"""
    payment_amount: Optional[float]
    """Amount received in payment currency"""
    payment_amount_raw: Optional[int]
    """Raw amount in smallest unit of payment currency"""
    fx_rate: Optional[float]
    """FX rate used: 1 unit of payment currency = fx_rate units of accounting currency"""
    fx_rate_timestamp: Optional[str]
    """When the FX rate was captured (max 64 chars)"""

    def __init__(
        self,
        *,
        id: Optional[str] = ...,
        amount: Optional[float] = ...,
        currency: Optional[str] = ...,
        due_on: Optional[str] = ...,
        status: Optional[str] = ...,
        recipient: Optional[User] = ...,
        payer: Optional[User] = ...,
        paid_on: Optional[str] = ...,
        type: Optional[str] = ...,
        metadata: Optional[str] = ...,
        payment_currency: Optional[str] = ...,
        payment_amount: Optional[float] = ...,
        payment_amount_raw: Optional[int] = ...,
        fx_rate: Optional[float] = ...,
        fx_rate_timestamp: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    def get_subaccount(self) -> bytes:
        """Get the 32-byte subaccount for this invoice."""
        ...

    def get_subaccount_hex(self) -> str:
        """Get the subaccount as a hex string."""
        ...

    def get_subaccount_list(self) -> list:
        """Get the subaccount as a list of integers (for ICRC-1 API calls)."""
        ...

    @staticmethod
    def from_subaccount(subaccount: bytes) -> Optional["Invoice"]:
        """Look up an Invoice by its subaccount bytes."""
        ...

    def get_amount_raw(self, decimals: int = ...) -> int:
        """Get the invoice amount in raw units of accounting currency."""
        ...

    def mark_paid(
        self,
        payment_currency: str = ...,
        payment_amount: float = ...,
        payment_amount_raw: int = ...,
        fx_rate: float = ...,
        fx_rate_timestamp: str = ...,
    ) -> None:
        """Mark this invoice as paid with current timestamp and payment details."""
        ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Invoice"]: ...
    @classmethod
    def instances(cls) -> List["Invoice"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Invoice"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Invoice"]: ...


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------

class Transfer(Entity):
    """Transfer entity — represents a token transfer on the ledger.

    Alias: ``id``

    ⚠️  ``amount`` is Integer (int), not Float.
    ⚠️  ``id`` is NOT auto-generated — you must provide it explicitly.
    """

    id: Optional[str]
    """Transfer ID (⚠️  must be provided explicitly, not auto-generated)"""

    principal_from: Optional[str]
    """Sender principal ID"""

    principal_to: Optional[str]
    """Receiver principal ID"""

    subaccount: Optional[str]
    """Hex-encoded destination subaccount (max 64 chars)"""

    invoice: Optional[Invoice]
    """ManyToOne: linked invoice if this transfer paid one"""

    instrument: Optional[str]
    """Token/instrument name (e.g., 'ckBTC', 'ICP')"""

    amount: Optional[int]
    """Transfer amount (⚠️  Integer, not Float!)"""

    timestamp: Optional[str]
    """ISO timestamp of the transfer"""

    tags: Optional[str]
    """Tags string (e.g., 'social_security', 'procurement')"""

    status: Optional[str]
    """Transfer status (e.g., 'completed', 'pending', 'failed')"""

    def __init__(
        self,
        *,
        id: Optional[str] = ...,
        principal_from: Optional[str] = ...,
        principal_to: Optional[str] = ...,
        subaccount: Optional[str] = ...,
        invoice: Optional[Invoice] = ...,
        instrument: Optional[str] = ...,
        amount: Optional[int] = ...,
        timestamp: Optional[str] = ...,
        tags: Optional[str] = ...,
        status: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Transfer"]: ...
    @classmethod
    def instances(cls) -> List["Transfer"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Transfer"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Transfer"]: ...


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(Entity):
    """Notification entity for user notifications.

    ⚠️  ``user`` is ManyToOne(User) — may cause serialization issues in shell.
    Store user ID in ``metadata`` as workaround: ``metadata="uid:user_002|..."``
    """

    topic: Optional[str]
    """Notification topic (max 64 chars)"""

    title: Optional[str]
    """Notification title (max 256 chars)"""

    message: Optional[str]
    """Notification message body (max 2048 chars)"""

    user: Optional[User]
    """ManyToOne: target user
    ⚠️  May cause serialization error in shell context"""

    read: Optional[bool]
    """Whether the notification has been read"""

    metadata: Optional[str]
    """Short metadata string (max 256 chars)"""

    icon: Optional[str]
    """Icon name (max 64 chars)"""

    href: Optional[str]
    """Link URL (max 256 chars)"""

    color: Optional[str]
    """Color hint (max 32 chars)"""

    def __init__(
        self,
        *,
        topic: Optional[str] = ...,
        title: Optional[str] = ...,
        message: Optional[str] = ...,
        user: Optional[User] = ...,
        read: Optional[bool] = ...,
        metadata: Optional[str] = ...,
        icon: Optional[str] = ...,
        href: Optional[str] = ...,
        color: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Notification"]: ...
    @classmethod
    def instances(cls) -> List["Notification"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Notification"]: ...


# ---------------------------------------------------------------------------
# Vote
# ---------------------------------------------------------------------------

class Vote(Entity):
    """Individual vote entity for tracking votes on proposals."""

    proposal: Optional[Proposal]
    """ManyToOne: the proposal being voted on"""

    voter: Optional[User]
    """ManyToOne: the user casting the vote"""

    vote_choice: Optional[str]
    """Vote choice (max 16 chars): 'yes', 'no', 'abstain'"""

    metadata: Optional[str]
    """Short metadata string (max 256 chars)"""

    def __init__(
        self,
        *,
        proposal: Optional[Proposal] = ...,
        voter: Optional[User] = ...,
        vote_choice: Optional[str] = ...,
        metadata: Optional[str] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Vote"]: ...
    @classmethod
    def instances(cls) -> List["Vote"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Vote"]: ...


# ---------------------------------------------------------------------------
# Treasury
# ---------------------------------------------------------------------------

class Treasury(Entity):
    """Treasury entity — realm treasury with balance tracking.

    Alias: ``name``
    """

    name: Optional[str]
    """Treasury name (min 2, max 256 chars)"""

    balance: Optional[int]
    """Treasury balance (Integer, default 0)"""

    realm: Optional["Realm"]
    """OneToOne: the realm this treasury belongs to"""

    def __init__(
        self,
        *,
        name: Optional[str] = ...,
        balance: Optional[int] = ...,
        realm: Optional["Realm"] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Treasury"]: ...
    @classmethod
    def instances(cls) -> List["Treasury"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Treasury"]: ...


# ---------------------------------------------------------------------------
# Human
# ---------------------------------------------------------------------------

class Human(Entity):
    """Human identity entity — physical person behind a User.

    Alias: ``name``
    """

    name: Optional[str]
    """Human name (max 256 chars)"""

    date_of_birth: Optional[str]
    """Date of birth (max 256 chars)"""

    latitude: Optional[float]
    longitude: Optional[float]
    h3_index: Optional[str]
    """H3 hexagonal index (max 20 chars)"""

    user: Optional[User]
    """OneToOne: linked User entity"""

    identities: List["Identity"]
    """OneToMany: identity documents/proofs"""

    def __init__(
        self,
        *,
        name: Optional[str] = ...,
        date_of_birth: Optional[str] = ...,
        latitude: Optional[float] = ...,
        longitude: Optional[float] = ...,
        h3_index: Optional[str] = ...,
        user: Optional[User] = ...,
        **kwargs,
    ) -> None: ...

    @classmethod
    def load(cls, entity_id: str, level: int = ...) -> Optional["Human"]: ...
    @classmethod
    def instances(cls) -> List["Human"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Human"]: ...


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class Identity(Entity):
    """Identity document/proof entity."""

    type: Optional[str]
    metadata: Optional[str]
    human: Optional[Human]
    """ManyToOne: the Human this identity belongs to"""

    def __init__(self, *, type: Optional[str] = ..., metadata: Optional[str] = ..., human: Optional[Human] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Identity"]: ...
    @classmethod
    def count(cls) -> int: ...


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------

class Instrument(Entity):
    """Financial instrument entity.

    Alias: ``name``
    """

    name: Optional[str]
    """Instrument name (max 256 chars)"""

    principal_id: Optional[str]
    """IC canister principal ID (max 256 chars)"""

    metadata: Optional[str]
    """Metadata (max 256 chars)"""

    def __init__(self, *, name: Optional[str] = ..., principal_id: Optional[str] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Instrument"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Instrument"]: ...


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------

class Balance(Entity):
    """Balance entity — tracks a user's balance for an instrument.

    Alias: ``id``
    """

    id: Optional[str]
    user: Optional[User]
    """ManyToOne: the user who owns this balance"""
    instrument: Optional[str]
    amount: Optional[int]
    transfers: List[Transfer]
    """OneToMany: transfers affecting this balance"""
    tag: Optional[str]

    def __init__(self, *, id: Optional[str] = ..., user: Optional[User] = ..., instrument: Optional[str] = ..., amount: Optional[int] = ..., tag: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Balance"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Balance"]: ...


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------

class Codex(Entity):
    """Codex entity — governance script stored in the realm.

    Alias: ``name``
    """

    name: Optional[str]
    code: Optional[str]
    url: Optional[str]
    """Optional URL for downloadable code"""
    checksum: Optional[str]
    """Optional SHA-256 checksum"""

    def __init__(self, *, name: Optional[str] = ..., code: Optional[str] = ..., url: Optional[str] = ..., checksum: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Codex"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Codex"]: ...


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

class Contract(Entity):
    """Contract entity.

    Alias: ``name``
    """

    name: Optional[str]
    mandate: Optional["Mandate"]
    """ManyToOne: parent mandate"""
    status: Optional[str]
    """Status (max 16 chars)"""
    metadata: Optional[str]
    """Metadata (max 256 chars)"""

    def __init__(self, *, name: Optional[str] = ..., mandate: Optional["Mandate"] = ..., status: Optional[str] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Contract"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Contract"]: ...


# ---------------------------------------------------------------------------
# Dispute
# ---------------------------------------------------------------------------

class Dispute(Entity):
    """Dispute entity — judicial dispute between parties.

    Alias: ``dispute_id``
    """

    dispute_id: Optional[str]
    """Dispute identifier (max 64 chars)"""
    requester: Optional[User]
    """ManyToOne: user who filed the dispute"""
    defendant: Optional[User]
    """ManyToOne: user being disputed"""
    case_title: Optional[str]
    """Case title (max 256 chars)"""
    description: Optional[str]
    """Case description (max 2048 chars)"""
    status: Optional[str]
    """Dispute status (max 16 chars)"""
    verdict: Optional[str]
    """Verdict text (max 1024 chars)"""
    actions_taken: Optional[str]
    """JSON array of actions taken (max 2048 chars)"""
    metadata: Optional[str]
    """Metadata (max 256 chars)"""

    def __init__(self, *, dispute_id: Optional[str] = ..., requester: Optional[User] = ..., defendant: Optional[User] = ..., case_title: Optional[str] = ..., description: Optional[str] = ..., status: Optional[str] = ..., verdict: Optional[str] = ..., actions_taken: Optional[str] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Dispute"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Dispute"]: ...


# ---------------------------------------------------------------------------
# Realm
# ---------------------------------------------------------------------------

class Realm(Entity):
    """Realm entity — a governance realm.

    Alias: ``name``
    """

    name: Optional[str]
    """Realm name (min 2, max 256 chars)"""
    description: Optional[str]
    """Realm description (max 256 chars)"""
    logo: Optional[str]
    """Logo URL (max 512 chars)"""
    welcome_image: Optional[str]
    """Welcome page background image URL (max 512 chars)"""
    welcome_message: Optional[str]
    """Welcome message (max 1024 chars)"""
    calendar: Optional["Calendar"]
    """OneToOne: realm calendar"""
    treasury: Optional[Treasury]
    """OneToOne: realm treasury"""
    accounting_currency: Optional[str]
    """Accounting/reference currency symbol (max 16 chars, default: 'ckBTC')"""
    accounting_currency_decimals: Optional[int]
    """Decimal places for accounting currency (default: 8)"""
    principal_id: Optional[str]
    """Canister principal ID (max 64 chars)"""

    def __init__(self, *, name: Optional[str] = ..., description: Optional[str] = ..., logo: Optional[str] = ..., welcome_image: Optional[str] = ..., welcome_message: Optional[str] = ..., accounting_currency: Optional[str] = ..., accounting_currency_decimals: Optional[int] = ..., principal_id: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Realm"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Realm"]: ...


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class Calendar(Entity):
    """Realm calendar — defines governance time cycles.

    Alias: ``name``. All durations are in seconds.
    """

    name: Optional[str]
    realm: Optional[Realm]
    epoch: Optional[int]
    """Unix seconds when calendar starts"""
    fiscal_period: Optional[int]
    """Budget/accounting cycle (default: 90 days)"""
    voting_window: Optional[int]
    """Proposal voting window (default: 7 days)"""
    codex_release_cycle: Optional[int]
    """Codex release interval (default: 14 days)"""
    benefit_cycle: Optional[int]
    """Social benefit payment interval (default: 30 days)"""
    service_payment_cycle: Optional[int]
    """Service payment interval (default: 30 days)"""
    license_review_cycle: Optional[int]
    """License review interval (default: 90 days)"""
    custom_cycles: Optional[str]
    """JSON string for extension-defined cycles (max 2048 chars)"""

    def __init__(self, *, name: Optional[str] = ..., epoch: Optional[int] = ..., fiscal_period: Optional[int] = ..., voting_window: Optional[int] = ..., codex_release_cycle: Optional[int] = ..., benefit_cycle: Optional[int] = ..., service_payment_cycle: Optional[int] = ..., license_review_cycle: Optional[int] = ..., custom_cycles: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Calendar"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Calendar"]: ...


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class Service(Entity):
    """Public service entity.

    Alias: ``service_id``
    """

    service_id: Optional[str]
    """Service identifier (max 64 chars)"""
    name: Optional[str]
    """Service name (max 256 chars)"""
    description: Optional[str]
    """Service description (max 2048 chars)"""
    provider: Optional[str]
    """Provider name (max 256 chars)"""
    status: Optional[str]
    """Service status (max 32 chars): Active, Pending, Expired"""
    due_date: Optional[str]
    """ISO timestamp due date (max 64 chars)"""
    link: Optional[str]
    """URL (max 512 chars)"""
    user: Optional[User]
    """ManyToOne: associated user"""
    metadata: Optional[str]
    """Metadata (max 256 chars)"""

    def __init__(self, *, service_id: Optional[str] = ..., name: Optional[str] = ..., description: Optional[str] = ..., provider: Optional[str] = ..., status: Optional[str] = ..., due_date: Optional[str] = ..., link: Optional[str] = ..., user: Optional[User] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Service"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Service"]: ...


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

class Token(Entity):
    """Token/ledger entity — represents a token the realm can interact with.

    Alias: ``id`` (symbol, e.g., "ckBTC", "REALMS")
    """

    id: Optional[str]
    """Token symbol as ID (max 16 chars)"""
    symbol: Optional[str]
    """Token symbol (max 16 chars)"""
    name: Optional[str]
    """Token display name (max 64 chars)"""
    ledger_canister_id: Optional[str]
    """Ledger canister principal (max 64 chars)"""
    indexer_canister_id: Optional[str]
    """Indexer canister principal (max 64 chars)"""
    decimals: Optional[int]
    """Decimal places (default: 8)"""
    token_type: Optional[str]
    """'shared' or 'realm' (max 16 chars, default: 'realm')"""
    enabled: Optional[str]
    """'true' or 'false' (max 8 chars, default: 'true')"""

    def is_enabled(self) -> bool: ...
    def get_ledger_config(self) -> dict: ...

    def __init__(self, *, id: Optional[str] = ..., symbol: Optional[str] = ..., name: Optional[str] = ..., ledger_canister_id: Optional[str] = ..., indexer_canister_id: Optional[str] = ..., decimals: Optional[int] = ..., token_type: Optional[str] = ..., enabled: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Token"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Token"]: ...


# ---------------------------------------------------------------------------
# Land & Zone
# ---------------------------------------------------------------------------

class LandType:
    RESIDENTIAL: str
    AGRICULTURAL: str
    INDUSTRIAL: str
    COMMERCIAL: str
    UNASSIGNED: str


class Land(Entity):
    """Land parcel entity.

    Alias: ``id``
    """

    id: Optional[str]
    x_coordinate: Optional[int]
    y_coordinate: Optional[int]
    land_type: Optional[str]
    """Land type (max 64 chars, default: 'unassigned')"""
    owner_user: Optional[User]
    """ManyToOne: user owner"""
    owner_organization: Optional["Organization"]
    """ManyToOne: organization owner"""
    size_width: Optional[int]
    size_height: Optional[int]
    metadata: Optional[str]
    """Metadata JSON (max 512 chars)"""
    zones: List["Zone"]
    """OneToMany: zones within this land"""

    def __init__(self, *, id: Optional[str] = ..., x_coordinate: Optional[int] = ..., y_coordinate: Optional[int] = ..., land_type: Optional[str] = ..., owner_user: Optional[User] = ..., owner_organization: Optional["Organization"] = ..., size_width: Optional[int] = ..., size_height: Optional[int] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Land"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Land"]: ...


class Zone(Entity):
    """Geographic zone of influence using H3 indexing.

    Alias: ``h3_index``
    """

    h3_index: Optional[str]
    """H3 cell index (max 32 chars)"""
    name: Optional[str]
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    resolution: Optional[float]
    """H3 resolution level (0-15)"""
    metadata: Optional[str]
    """Metadata JSON (max 2048 chars)"""
    user: Optional[User]
    """ManyToOne: associated user"""
    land: Optional[Land]
    """ManyToOne: associated land parcel"""

    def __init__(self, *, h3_index: Optional[str] = ..., name: Optional[str] = ..., description: Optional[str] = ..., latitude: Optional[float] = ..., longitude: Optional[float] = ..., resolution: Optional[float] = ..., metadata: Optional[str] = ..., user: Optional[User] = ..., land: Optional[Land] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Zone"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Zone"]: ...


# ---------------------------------------------------------------------------
# Organization, License, Mandate, Permission, Registry
# ---------------------------------------------------------------------------

class Organization(Entity):
    """Organization entity. Alias: ``name``"""
    name: Optional[str]
    owned_lands: List[Land]
    def __init__(self, *, name: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Organization"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Organization"]: ...


class License(Entity):
    """License entity. Alias: ``name``"""
    name: Optional[str]
    metadata: Optional[str]
    def __init__(self, *, name: Optional[str] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["License"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["License"]: ...


class Mandate(Entity):
    """Mandate entity. Alias: ``name``"""
    name: Optional[str]
    metadata: Optional[str]
    def __init__(self, *, name: Optional[str] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Mandate"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Mandate"]: ...


class Permission(Entity):
    """Permission entity."""
    description: Optional[str]
    def __init__(self, *, description: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Permission"]: ...
    @classmethod
    def count(cls) -> int: ...


class Registry(Entity):
    """Registry entity. Alias: ``name``"""
    name: Optional[str]
    description: Optional[str]
    principal_id: Optional[str]
    def __init__(self, *, name: Optional[str] = ..., description: Optional[str] = ..., principal_id: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Registry"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Registry"]: ...


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

class Trade(Entity):
    """Trade entity — exchange of transfers under a contract."""
    contract: Optional[Contract]
    metadata: Optional[str]
    transfer_1: Optional[Transfer]
    transfer_2: Optional[Transfer]
    def __init__(self, *, contract: Optional[Contract] = ..., metadata: Optional[str] = ..., transfer_1: Optional[Transfer] = ..., transfer_2: Optional[Transfer] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Trade"]: ...
    @classmethod
    def count(cls) -> int: ...


# ---------------------------------------------------------------------------
# PaymentAccount
# ---------------------------------------------------------------------------

class PaymentAccount(Entity):
    """Payment account entity. Alias: ``id`` (auto: {currency}_{network}_{address})"""

    id: Optional[str]
    user: Optional[User]
    """ManyToOne: account owner"""
    address: Optional[str]
    """Address/principal/IBAN (max 256 chars)"""
    label: Optional[str]
    """User-friendly name (max 100 chars)"""
    network: Optional[str]
    """Network name: ICP, Bitcoin, Ethereum, SEPA (max 50 chars)"""
    currency: Optional[str]
    """Currency: ckBTC, EUR, ICP, ETH (max 20 chars)"""
    is_active: Optional[bool]
    """Active flag (default: True)"""
    is_verified: Optional[bool]
    """Verification status (default: False)"""
    metadata: Optional[str]
    """Metadata JSON (max 512 chars)"""

    def __init__(self, *, id: Optional[str] = ..., user: Optional[User] = ..., address: Optional[str] = ..., label: Optional[str] = ..., network: Optional[str] = ..., currency: Optional[str] = ..., is_active: Optional[bool] = ..., is_verified: Optional[bool] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["PaymentAccount"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["PaymentAccount"]: ...


# ---------------------------------------------------------------------------
# UserProfile, Operations, Profiles
# ---------------------------------------------------------------------------

class Operations:
    ALL: str
    USER_ADD: str
    USER_EDIT: str
    USER_DELETE: str
    ORGANIZATION_ADD: str
    ORGANIZATION_EDIT: str
    ORGANIZATION_DELETE: str
    TRANSFER_CREATE: str
    TRANSFER_REVERT: str
    TASK_CREATE: str
    TASK_EDIT: str
    TASK_DELETE: str
    TASK_RUN: str
    TASK_SCHEDULE: str
    TASK_CANCEL: str


class Profiles:
    ADMIN: dict
    MEMBER: dict


class UserProfile(Entity):
    """User profile/role entity. Alias: ``name``"""

    name: Optional[str]
    description: Optional[str]
    allowed_to: Optional[str]
    """Comma-separated operation strings"""
    users: List[User]
    """ManyToMany: users assigned this profile"""

    def add(self, operation: str) -> None:
        """Add an operation permission."""
        ...

    def remove(self, operation: str) -> None:
        """Remove an operation permission."""
        ...

    def is_allowed(self, operation: str) -> bool:
        """Check if an operation is allowed."""
        ...

    def __init__(self, *, name: Optional[str] = ..., description: Optional[str] = ..., allowed_to: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["UserProfile"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["UserProfile"]: ...


# ---------------------------------------------------------------------------
# Task, TaskStep, TaskSchedule, TaskExecution, Call
# ---------------------------------------------------------------------------

class Call(Entity):
    """Call entity — links Codex code to TaskStep execution."""
    is_async: Optional[bool]
    codex: Optional[Codex]
    task_step: Optional["TaskStep"]
    def __init__(self, *, is_async: Optional[bool] = ..., codex: Optional[Codex] = ..., task_step: Optional["TaskStep"] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Call"]: ...
    @classmethod
    def count(cls) -> int: ...


class TaskStep(Entity):
    """TaskStep entity — a single step in a task execution."""
    call: Optional[Call]
    status: Optional[str]
    """Step status (max 32 chars, default: 'pending')"""
    run_next_after: Optional[int]
    """Seconds to wait before next step (default: 0)"""
    timer_id: Optional[int]
    task: Optional["Task"]
    """ManyToOne: parent task"""
    def __init__(self, *, call: Optional[Call] = ..., status: Optional[str] = ..., run_next_after: Optional[int] = ..., timer_id: Optional[int] = ..., task: Optional["Task"] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["TaskStep"]: ...
    @classmethod
    def count(cls) -> int: ...


class TaskExecution(Entity):
    """TaskExecution entity — execution record. Alias: ``name``"""
    name: Optional[str]
    task: Optional["Task"]
    """ManyToOne: parent task"""
    status: Optional[str]
    """Execution status (max 50 chars): completed, failed, running, idle"""
    result: Optional[str]
    """Execution result (max 5000 chars)"""
    def __init__(self, *, name: Optional[str] = ..., task: Optional["Task"] = ..., status: Optional[str] = ..., result: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["TaskExecution"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["TaskExecution"]: ...


class TaskSchedule(Entity):
    """TaskSchedule entity — schedule for running tasks. Alias: ``name``"""
    name: Optional[str]
    disabled: Optional[bool]
    task: Optional["Task"]
    """ManyToOne: the task to schedule"""
    run_at: Optional[int]
    """Unix seconds to first run"""
    repeat_every: Optional[int]
    """Interval in seconds between runs"""
    last_run_at: Optional[int]
    """Unix seconds of last execution"""
    def __init__(self, *, name: Optional[str] = ..., disabled: Optional[bool] = ..., task: Optional["Task"] = ..., run_at: Optional[int] = ..., repeat_every: Optional[int] = ..., last_run_at: Optional[int] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["TaskSchedule"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["TaskSchedule"]: ...


class Task(Entity):
    """Task entity — a unit of work that can be scheduled. Alias: ``name``"""
    name: Optional[str]
    metadata: Optional[str]
    """Task metadata (max 256 chars)"""
    status: Optional[str]
    """Task status (max 32 chars, default: 'pending')"""
    step_to_execute: Optional[int]
    """Index of next step to execute (default: 0)"""
    steps: List[TaskStep]
    """OneToMany: execution steps"""
    schedules: List[TaskSchedule]
    """OneToMany: schedules for this task"""
    executions: List[TaskExecution]
    """OneToMany: execution records"""

    def new_task_execution(self) -> TaskExecution:
        """Create a new execution record for this task."""
        ...

    def __init__(self, *, name: Optional[str] = ..., metadata: Optional[str] = ..., status: Optional[str] = ..., step_to_execute: Optional[int] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Task"]: ...
    @classmethod
    def count(cls) -> int: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Task"]: ...


# ===========================================================================
# Finance Entities
# ===========================================================================

# ---------------------------------------------------------------------------
# FundType & Fund
# ---------------------------------------------------------------------------

class FundType:
    """Standard governmental fund types (GASB)."""
    GENERAL: str
    SPECIAL_REVENUE: str
    CAPITAL_PROJECTS: str
    DEBT_SERVICE: str
    ENTERPRISE: str
    INTERNAL_SERVICE: str
    TRUST: str
    AGENCY: str


class Fund(Entity):
    """Governmental Fund — organizes money by purpose.

    Alias: ``code`` (e.g., ``Fund["GEN"]``)
    """

    code: Optional[str]
    """Fund code (max 16 chars), e.g., "GEN", "SS", "PROC" — this is the alias"""

    name: Optional[str]
    """Fund name (max 256 chars)"""

    fund_type: Optional[str]
    """Fund type from FundType (max 32 chars, default: 'general')"""

    description: Optional[str]
    """Description (max 512 chars)"""

    realm: Optional[Realm]
    """ManyToOne: the realm this fund belongs to"""

    ledger_entries: List["LedgerEntry"]
    """OneToMany: ledger entries for this fund"""

    budgets: List["Budget"]
    """OneToMany: budgets allocated to this fund"""

    def __init__(self, *, code: Optional[str] = ..., name: Optional[str] = ..., fund_type: Optional[str] = ..., description: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Fund"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Fund"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Fund"]: ...


# ---------------------------------------------------------------------------
# FiscalPeriodStatus & FiscalPeriod
# ---------------------------------------------------------------------------

class FiscalPeriodStatus:
    """Fiscal period lifecycle states."""
    OPEN: str
    CLOSED: str
    ARCHIVED: str


class FiscalPeriod(Entity):
    """Fiscal Period — accounting period boundaries.

    Alias: ``id`` (e.g., ``FiscalPeriod["FY2026"]``)
    """

    id: Optional[str]
    """Period ID (max 16 chars), e.g., "FY2026", "2026-Q1" """

    name: Optional[str]
    """Display name (max 64 chars)"""

    start_date: Optional[str]
    """ISO format start date, e.g., "2026-01-01" (max 32 chars)"""

    end_date: Optional[str]
    """ISO format end date, e.g., "2026-12-31" (max 32 chars)"""

    status: Optional[str]
    """Period status (max 16 chars, default: 'open'): open, closed, archived"""

    ledger_entries: List["LedgerEntry"]
    """OneToMany: ledger entries in this period"""

    budgets: List["Budget"]
    """OneToMany: budgets for this period"""

    def is_open(self) -> bool:
        """Check if period accepts new entries."""
        ...

    def close(self) -> None:
        """Close the fiscal period."""
        ...

    def __init__(self, *, id: Optional[str] = ..., name: Optional[str] = ..., start_date: Optional[str] = ..., end_date: Optional[str] = ..., status: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["FiscalPeriod"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["FiscalPeriod"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["FiscalPeriod"]: ...


# ---------------------------------------------------------------------------
# BudgetStatus & Budget
# ---------------------------------------------------------------------------

class BudgetStatus:
    """Budget lifecycle states."""
    DRAFT: str
    PROPOSED: str
    ADOPTED: str
    AMENDED: str
    CLOSED: str


class Budget(Entity):
    """Budget — tracks planned vs actual for a fund within a fiscal period.

    Alias: ``id`` (e.g., ``Budget["FY2026_GEN_personnel"]``)

    Links to a Proposal for governance approval workflow.
    """

    id: Optional[str]
    """Budget ID (max 64 chars)"""

    name: Optional[str]
    """Budget name (max 256 chars)"""

    fund: Optional[Fund]
    """ManyToOne: which fund this budget belongs to"""

    fiscal_period: Optional[FiscalPeriod]
    """ManyToOne: which fiscal period"""

    category: Optional[str]
    """Budget category (max 64 chars), e.g., "tax_revenue", "personnel" """

    budget_type: Optional[str]
    """'revenue' or 'expense' (max 16 chars)"""

    planned_amount: Optional[int]
    """Planned amount (Integer, default 0)"""

    actual_amount: Optional[int]
    """Actual amount spent/received (Integer, default 0)"""

    status: Optional[str]
    """Budget status (max 16 chars, default: 'draft')"""

    proposal: Optional[Proposal]
    """ManyToOne: governance proposal that approved this budget"""

    description: Optional[str]
    """Description (max 512 chars)"""

    def variance(self) -> int:
        """Calculate budget variance (actual - planned)."""
        ...

    def variance_percent(self) -> float:
        """Calculate variance as percentage of planned."""
        ...

    def update_actual(self, amount: int) -> None:
        """Add to actual amount."""
        ...

    def __init__(self, *, id: Optional[str] = ..., name: Optional[str] = ..., category: Optional[str] = ..., budget_type: Optional[str] = ..., planned_amount: Optional[int] = ..., actual_amount: Optional[int] = ..., status: Optional[str] = ..., description: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Budget"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Budget"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Budget"]: ...


# ---------------------------------------------------------------------------
# EntryType, Category & LedgerEntry
# ---------------------------------------------------------------------------

class EntryType:
    """Ledger entry classification for financial statements."""
    ASSET: str
    LIABILITY: str
    EQUITY: str
    REVENUE: str
    EXPENSE: str


class Category:
    """Standard categories for ledger entries."""
    # Revenues
    TAX: str
    FEE: str
    GRANT: str
    FINE: str
    SERVICE: str
    INVESTMENT_INCOME: str
    INTERGOVERNMENTAL: str
    # Expenses
    PERSONNEL: str
    SUPPLIES: str
    SERVICES: str
    CAPITAL: str
    DEBT: str
    TRANSFER_OUT: str
    # Assets
    CASH: str
    RECEIVABLE: str
    PROPERTY: str
    EQUIPMENT: str
    INVENTORY: str
    # Liabilities
    PAYABLE: str
    BOND: str
    LOAN: str
    DEFERRED_REVENUE: str
    # Equity
    FUND_BALANCE: str
    RETAINED_EARNINGS: str


class LedgerEntry(Entity):
    """Double-entry ledger line — the core of GGG government accounting.

    Alias: ``id``

    Multiple entries share a ``transaction_id`` where
    ``sum(debit) == sum(credit)`` (balanced transaction).

    Use ``LedgerEntry.create_transaction()`` for convenient balanced creation.
    """

    id: Optional[str]
    """Entry ID (max 64 chars)"""

    transaction_id: Optional[str]
    """Groups debit/credit pairs (max 64 chars)"""

    entry_type: Optional[str]
    """Classification (max 32 chars): asset, liability, equity, revenue, expense"""

    category: Optional[str]
    """Category from Category class (max 64 chars)"""

    debit: Optional[int]
    """Debit amount (Integer, default 0)"""

    credit: Optional[int]
    """Credit amount (Integer, default 0)"""

    entry_date: Optional[str]
    """ISO format date (max 32 chars)"""

    fund: Optional[Fund]
    """ManyToOne: which fund"""

    fiscal_period: Optional[FiscalPeriod]
    """ManyToOne: which fiscal period"""

    transfer: Optional[Transfer]
    """ManyToOne: linked transfer (optional)"""

    invoice: Optional[Invoice]
    """ManyToOne: linked invoice (optional)"""

    user: Optional[User]
    """ManyToOne: linked user (optional)"""

    organization: Optional[Organization]
    """ManyToOne: linked organization (optional)"""

    contract: Optional[Contract]
    """ManyToOne: linked contract (optional)"""

    currency: Optional[str]
    """Currency denomination for this entry (max 16 chars, e.g., 'ckUSDC')"""

    description: Optional[str]
    """Description (max 512 chars)"""

    reference: Optional[str]
    """External reference number (max 128 chars)"""

    tags: Optional[str]
    """Flexible tagging (max 256 chars)"""

    def amount(self) -> int:
        """Return the non-zero amount (debit or credit)."""
        ...

    def is_debit(self) -> bool: ...
    def is_credit(self) -> bool: ...

    @classmethod
    def validate_transaction(cls, transaction_id: str) -> bool:
        """Validate that debits == credits for a transaction."""
        ...

    @classmethod
    def create_transaction(cls, transaction_id: str, entries: List[dict], validate: bool = True) -> List["LedgerEntry"]:
        """Create a balanced double-entry transaction.

        Args:
            transaction_id: Unique ID for this transaction
            entries: List of dicts with entry_type, category, debit/credit, etc.
            validate: Raise ValueError if unbalanced
        """
        ...

    @classmethod
    def get_balance(cls, entry_type: str, category: Optional[str] = None, fund: Optional[Fund] = None) -> int:
        """Calculate net balance for an entry type."""
        ...

    def __init__(self, *, id: Optional[str] = ..., transaction_id: Optional[str] = ..., entry_type: Optional[str] = ..., category: Optional[str] = ..., debit: Optional[int] = ..., credit: Optional[int] = ..., entry_date: Optional[str] = ..., description: Optional[str] = ..., reference: Optional[str] = ..., tags: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["LedgerEntry"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["LedgerEntry"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["LedgerEntry"]: ...


# ── Realm Lifecycle ──────────────────────────────────────────────────────

class RealmStatus:
    """Realm lifecycle stages.

    registration  — Users register interest with ZK proof (Rarimo) + deposit.
    accreditation — Infrastructure built (electricity, roads, hospitals).
    operational   — Citizens move in, governance active.
    stable        — Fully self-sustaining.
    deprecation   — Winding down, no new members.
    terminated    — Closed, read-only archive.
    """
    REGISTRATION: str
    ACCREDITATION: str
    OPERATIONAL: str
    STABLE: str
    DEPRECATION: str
    TERMINATED: str


# ── Land ─────────────────────────────────────────────────────────────────

class LandStatus:
    """Land parcel status values."""
    ACTIVE: str
    DISPUTED: str
    TRANSFERRED: str
    REVOKED: str


# ── Justice System ───────────────────────────────────────────────────────

class JusticeSystemType:
    """Type of justice system."""
    PUBLIC: str
    PRIVATE: str
    HYBRID: str


class JusticeSystem:
    """Container for justice infrastructure within a Realm.

    Alias: ``name``

    Example::

        js = JusticeSystem(
            name="Public Justice",
            system_type=JusticeSystemType.PUBLIC,
            status="active",
        )
    """

    name: str
    """Unique name (alias). 2-256 chars."""

    description: Optional[str]
    """Description (max 1024 chars)."""

    system_type: Optional[str]
    """public, private, hybrid."""

    status: Optional[str]
    """active, suspended, dissolved."""

    realm: Optional[Realm]
    """ManyToOne → Realm."""

    courts: List["Court"]
    """OneToMany → Court."""

    license: Optional["License"]
    """OneToOne → License."""

    metadata: Optional[str]

    def is_active(self) -> bool: ...
    def get_courts(self) -> List["Court"]: ...
    def get_active_courts(self) -> List["Court"]: ...

    def __init__(self, *, name: str, description: Optional[str] = ..., system_type: Optional[str] = ..., status: Optional[str] = ..., realm: Optional[Realm] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["JusticeSystem"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["JusticeSystem"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["JusticeSystem"]: ...


class CourtLevel:
    """Court hierarchy level."""
    FIRST_INSTANCE: str
    APPELLATE: str
    SUPREME: str
    SPECIALIZED: str


class Court:
    """A Court handles Cases within a JusticeSystem.

    Alias: ``name``

    Example::

        court = Court(
            name="District Court",
            level=CourtLevel.FIRST_INSTANCE,
            status="active",
            justice_system=js,
        )
    """

    name: str
    """Unique name (alias). 2-256 chars."""

    description: Optional[str]
    jurisdiction: Optional[str]
    """Geographic or subject matter jurisdiction."""

    level: Optional[str]
    """first_instance, appellate, supreme, specialized."""

    status: Optional[str]
    """active, suspended, dissolved."""

    justice_system: Optional[JusticeSystem]
    codex: Optional["Codex"]
    license: Optional["License"]
    judges: List["Judge"]
    cases: List["Case"]
    appeals_received: List["Appeal"]
    parent_court: Optional["Court"]
    child_courts: List["Court"]
    metadata: Optional[str]

    def is_active(self) -> bool: ...
    def can_hear_appeal(self) -> bool: ...

    def __init__(self, *, name: str, description: Optional[str] = ..., jurisdiction: Optional[str] = ..., level: Optional[str] = ..., status: Optional[str] = ..., justice_system: Optional[JusticeSystem] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Court"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Court"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Court"]: ...


class Judge:
    """A Judge authorized to adjudicate Cases.

    Alias: ``id``

    Example::

        judge = Judge(
            id="judge_001",
            status="active",
            specialization="contract_law",
            court=court,
        )
    """

    id: str
    """Unique ID (alias). Max 64 chars."""

    appointment_date: Optional[str]
    status: Optional[str]
    """active, suspended, retired, revoked."""

    specialization: Optional[str]
    member: Optional["Member"]
    court: Optional[Court]
    cases_assigned: List["Case"]
    verdicts_issued: List["Verdict"]
    metadata: Optional[str]

    def is_active(self) -> bool: ...

    @staticmethod
    def judge_conflict_check_hook(judge: "Judge", case: "Case") -> bool:
        """Override via Codex. Return True if no conflict."""
        ...

    def __init__(self, *, id: str, appointment_date: Optional[str] = ..., status: Optional[str] = ..., specialization: Optional[str] = ..., court: Optional[Court] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Judge"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Judge"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Judge"]: ...


class CaseStatus:
    """Case lifecycle statuses."""
    FILED: str
    ASSIGNED: str
    IN_PROGRESS: str
    VERDICT_ISSUED: str
    CLOSED: str
    APPEALED: str
    DISMISSED: str


class Case:
    """A legal Case filed at a Court.

    Alias: ``case_number``

    Example::

        case = Case(
            case_number="DC-2026-001",
            title="Contract Dispute",
            status=CaseStatus.FILED,
            court=court,
            plaintiff=user_a,
            defendant=user_b,
        )
    """

    case_number: str
    """Unique case number (alias). Max 64 chars."""

    title: Optional[str]
    description: Optional[str]
    status: Optional[str]
    filed_date: Optional[str]
    closed_date: Optional[str]
    court: Optional[Court]
    plaintiff: Optional["User"]
    defendant: Optional["User"]
    judges: List[Judge]
    verdict: Optional["Verdict"]
    appeals: List["Appeal"]
    ledger_entries: List[LedgerEntry]
    metadata: Optional[str]

    def is_open(self) -> bool: ...
    def has_verdict(self) -> bool: ...
    def can_appeal(self) -> bool: ...

    def __init__(self, *, case_number: str, title: Optional[str] = ..., description: Optional[str] = ..., status: Optional[str] = ..., filed_date: Optional[str] = ..., court: Optional[Court] = ..., plaintiff: Optional["User"] = ..., defendant: Optional["User"] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Case"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Case"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Case"]: ...


class Verdict:
    """The outcome of a Case, issued by Judges.

    Alias: ``id``

    Example::

        verdict = Verdict(
            id="VRD-001",
            decision="liable",
            reasoning="Breach of contract proven",
            case=case,
            issued_by=judge,
        )
    """

    id: str
    decision: Optional[str]
    """guilty, not_guilty, liable, dismissed, etc."""

    reasoning: Optional[str]
    issued_date: Optional[str]
    case: Optional[Case]
    issued_by: Optional[Judge]
    penalties: List["Penalty"]
    appeal: Optional["Appeal"]
    metadata: Optional[str]

    def get_penalties(self) -> List["Penalty"]: ...
    def is_appealed(self) -> bool: ...
    def total_penalty_amount(self) -> float: ...

    def __init__(self, *, id: str, decision: Optional[str] = ..., reasoning: Optional[str] = ..., issued_date: Optional[str] = ..., case: Optional[Case] = ..., issued_by: Optional[Judge] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Verdict"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Verdict"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Verdict"]: ...


class PenaltyType:
    """Types of penalties."""
    FINE: str
    RESTITUTION: str
    COMMUNITY_SERVICE: str
    SUSPENSION: str
    REVOCATION: str
    INJUNCTION: str
    OTHER: str


class Penalty:
    """A sanction or remedy resulting from a Verdict.

    Alias: ``id``

    Example::

        penalty = Penalty(
            id="PEN-001",
            penalty_type=PenaltyType.FINE,
            amount=5000.0,
            status="pending",
            verdict=verdict,
            target_user=defendant,
        )
    """

    id: str
    penalty_type: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    description: Optional[str]
    status: Optional[str]
    """pending, executed, waived, appealed."""

    due_date: Optional[str]
    executed_date: Optional[str]
    verdict: Optional[Verdict]
    target_user: Optional["User"]
    ledger_entries: List[LedgerEntry]
    metadata: Optional[str]

    def is_financial(self) -> bool: ...
    def is_pending(self) -> bool: ...

    def __init__(self, *, id: str, penalty_type: Optional[str] = ..., amount: Optional[float] = ..., currency: Optional[str] = ..., description: Optional[str] = ..., status: Optional[str] = ..., due_date: Optional[str] = ..., verdict: Optional[Verdict] = ..., target_user: Optional["User"] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Penalty"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Penalty"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Penalty"]: ...


class AppealStatus:
    """Appeal lifecycle statuses."""
    FILED: str
    UNDER_REVIEW: str
    GRANTED: str
    DENIED: str
    WITHDRAWN: str


class Appeal:
    """An Appeal allows Case review by a higher Court.

    Alias: ``id``

    Example::

        appeal = Appeal(
            id="APL-001",
            grounds="Procedural error in trial",
            status=AppealStatus.FILED,
            original_case=case,
            appellate_court=appeals_court,
            appellant=defendant,
        )
    """

    id: str
    grounds: Optional[str]
    status: Optional[str]
    filed_date: Optional[str]
    decided_date: Optional[str]
    decision: Optional[str]
    """upheld, reversed, modified, remanded."""

    decision_reasoning: Optional[str]
    original_case: Optional[Case]
    original_verdict: Optional[Verdict]
    appellate_court: Optional[Court]
    appellant: Optional["User"]
    new_verdict: Optional[Verdict]
    ledger_entries: List[LedgerEntry]
    metadata: Optional[str]

    def is_pending(self) -> bool: ...
    def was_granted(self) -> bool: ...

    def __init__(self, *, id: str, grounds: Optional[str] = ..., status: Optional[str] = ..., filed_date: Optional[str] = ..., original_case: Optional[Case] = ..., original_verdict: Optional[Verdict] = ..., appellate_court: Optional[Court] = ..., appellant: Optional["User"] = ..., metadata: Optional[str] = ..., **kwargs) -> None: ...
    @classmethod
    def instances(cls) -> List["Appeal"]: ...
    @classmethod
    def count(cls) -> int: ...
    @classmethod
    def find(cls, d: dict) -> List["Appeal"]: ...
    def __class_getitem__(cls, alias_value: str) -> Optional["Appeal"]: ...
