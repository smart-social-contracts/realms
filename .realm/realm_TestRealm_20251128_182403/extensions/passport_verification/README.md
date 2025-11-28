# Passport Verification

Rarimo ZK Passport verification extension for secure, privacy-preserving identity verification using zero-knowledge proofs.

## Overview

This extension integrates **Rarimo's zero-knowledge proof technology** to verify passport identities without exposing sensitive personal data. Users prove their citizenship, age, and identity uniqueness using cryptographic proofs generated from their physical passport—all while keeping passport data on their device.

## How It Works

1. **Generate Verification Link**: Backend creates a unique verification session via Rarimo API
2. **Scan QR Code**: User scans QR code with the RariMe mobile app
3. **NFC Passport Reading**: App reads passport data via NFC (data stays on device)
4. **ZK Proof Generation**: App creates zero-knowledge proofs locally
5. **Verification**: Proofs are submitted to Rarimo API for verification
6. **Identity Creation**: Upon success, passport identity is linked to user account

## Key Features

- **Zero-Knowledge Proofs**: Verify identity without revealing raw passport data
- **Privacy-Preserving**: Passport information never leaves user's device
- **Age Verification**: Prove age > 18 without revealing exact birthdate
- **Citizenship Verification**: Confirm nationality without exposing passport number
- **Uniqueness Check**: Prevent duplicate accounts (one person = one identity)
- **Session-Based Security**: Each verification uses unique session IDs from caller principal
- **Real-Time Status Tracking**: Monitor verification progress with polling mechanism

## Technical Architecture

**Frontend**: Svelte component with QR code display and status management
**Backend**: Python Kybra extension using IC HTTP outcalls
**External Service**: Rarimo API (`api.app.rarime.com`)
**Proof System**: Zero-knowledge cryptography with NFC passport reading

### Backend Functions

- `get_verification_link(user_id)` - Generate verification session and RariMe app URL
- `check_verification_status(user_id)` - Poll verification status from Rarimo API
- `create_passport_identity(verification_data)` - Store verified identity in realm

### Verification Requirements

- Minimum age: 18 years
- Uniqueness enforcement: enabled
- Optional nationality filtering
- NFC-enabled passport (ePassport)

## Use Cases

- **Government Identity Verification**: Verify citizenship for public services access
- **Age-Gated Services**: Confirm age requirements without revealing birthdates
- **KYC Compliance**: Meet regulatory requirements with privacy preservation
- **Sybil Resistance**: Ensure one person = one account in governance systems
- **Credential Issuance**: Link verified identities to digital credentials

## Security & Privacy

- ✅ Passport data remains on user's device (never uploaded)
- ✅ Only cryptographic proofs are shared
- ✅ No passport images or personal data stored on blockchain
- ✅ Session IDs derived from caller principals (unique per user)
- ✅ HTTP outcalls use IC consensus for security (100M cycles)

## External Dependencies

- **Rarimo API**: ZK proof verification service
- **RariMe Mobile App**: Required for NFC passport scanning
- **Internet Computer**: HTTP outcalls for API communication

## Requirements

- User must have RariMe mobile app installed
- Physical passport with NFC chip (ePassport)
- Smartphone with NFC capability
- User must be authenticated with member or admin profile

---

**Category:** Public Services  
**Access:** Members and Admins  
**Version:** 1.0.3
