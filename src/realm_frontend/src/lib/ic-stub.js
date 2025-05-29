// Comprehensive stub implementation for Internet Computer dependencies
// Used during development to avoid replica connection errors

// @dfinity/candid exports
export class Some {
  constructor(value) {
    this._value = value;
  }
  
  get value() {
    return this._value;
  }
}

export class None {}

// @dfinity/principal exports
export class Principal {
  constructor(id = "2vxsx-fae") {
    this._id = id;
  }
  
  toText() {
    return this._id;
  }
  
  toString() {
    return this._id;
  }
  
  static fromText(text) {
    return new Principal(text);
  }
}

// @dfinity/agent exports
export class HttpAgent {
  static create() {
    return {
      fetchRootKey: async () => true,
      getPrincipal: () => new Principal()
    };
  }
}

export class AnonymousIdentity {
  getPrincipal() {
    return new Principal();
  }
}

// @dfinity/identity exports
export class Identity {
  getPrincipal() {
    return new Principal();
  }
}

export class DelegationIdentity extends Identity {}
export class Ed25519KeyIdentity extends Identity {}
export class ECDSAKeyIdentity extends Identity {}
export class PartialDelegationIdentity extends Identity {}

export class Delegation {
  constructor() {
    this.pubkey = new Uint8Array();
    this.expiration = BigInt(0);
  }
}

export class DelegationChain {
  static fromJSON() {
    return new DelegationChain();
  }
  
  toJSON() {
    return {};
  }
}

export function isDelegationValid() {
  return true;
}

// Helper functions
export const isStubMode = () => true;
