# Realms Roadmap

## Current Status: Genesis Alpha

Realms GOS is currently in the **alpha** stage of the **1.0 "Genesis"** release — features are still being implemented and the system is experimental.

---

## Realms Proto — Basic Life Workflow Demo

A functional prototype demonstrating the core "life workflow" of a digital realm. Not a full MVP, but a working showcase of the governance lifecycle.

### Core Workflow
- **Join a Realm** — Buy land (NFT) or pay membership fee
- **Create Proposals** — Submit governance proposals
- **Vote on Proposals** — Participate in democratic decisions
- **Pay Taxes** — Automated tax collection via codex

### Key Components
- Voting, passport verification, land registry, member dashboard, vault, task monitor, and notifications extensions
- Governance automation, tax collection, token transfer, and user registration codices
- Demo deployment on [demo.realmsgos.org](https://demo.realmsgos.org)

📋 [Full details — GitHub Epic #104](https://github.com/smart-social-contracts/realms/issues/104)

---

## Realms GOS 1.0 "Genesis" — One-Click Realm Creation

Enable anyone to create their own digital Realm — a self-contained governance space — with just a few clicks. No code, no blockchain knowledge required.

### User Flow
1. Visit https://demo.realmsgos.org
2. Sign up with Internet Identity
3. Pay via credit card ($1 = 1 credit)
4. Pick a template (Syntropia, Agora, Dominion, or blank)
5. Click Create → Realm is live

### Key Components
- Template selection wizard UI
- Payment integration (Stripe)
- Realm provisioning backend API
- Credit balance tracking and cycles management
- Founder auto-registration on new realms

📋 [Full details — GitHub Epic #98](https://github.com/smart-social-contracts/realms/issues/98)

---

## Future

### Encryption via vetKeys
End-to-end encryption powered by the Internet Computer's vetKeys (Verifiably Encrypted Threshold Keys), enabling secure private data handling within Realms without relying on external key management.

### Horizontal Scalability through Quarters
Introduction of Quarters — federated autonomous realm backends within a Realm — allowing horizontal scaling, realm split, and realm merge. Each Quarter is a full realm backend that can operate independently if detached, enabling near-zero-cost split and merge operations. Multi-quarter policies (taxes, voting, justice) are encoded in a Federation Codex shared across quarters.

📋 [Full details — GitHub Epic #143](https://github.com/smart-social-contracts/realms/issues/143)

### Enhanced Python Interpreter
Transition from the Kybra Python-to-Wasm toolchain to Basilisk, delivering improved performance, broader Python compatibility, and a more streamlined developer experience for canister development.
