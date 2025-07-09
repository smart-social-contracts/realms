export class DummyHttpAgent {
  constructor(options = {}) {
    console.log('🔧 DEV MODE: DummyHttpAgent created');
    this._identity = options.identity || null;
  }

  async fetchRootKey() {
    console.log('🔧 DEV MODE: fetchRootKey called (dummy)');
    return Promise.resolve();
  }
}

export class DummyPrincipal {
  constructor(text = 'dummy-principal-123456789') {
    this._text = text;
  }

  static fromText(text) {
    return new DummyPrincipal(text);
  }

  toText() {
    return this._text;
  }

  toString() {
    return this._text;
  }
}

export const DummyCandid = {
  Some: (value) => ({ Some: value }),
  None: null
};
