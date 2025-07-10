export class DummyAuthClient {
  constructor() {
    this.authenticated = true;
    this.identity = {
      getPrincipal: () => ({
        toText: () => 'dummy-principal-123456789'
      })
    };
  }

  static async create() {
    return new DummyAuthClient();
  }

  async login(options = {}) {
    console.log('🔧 DEV MODE: Dummy login called');
    if (options.onSuccess) {
      options.onSuccess();
    }
    return Promise.resolve();
  }

  async logout() {
    console.log('🔧 DEV MODE: Dummy logout called');
    return Promise.resolve();
  }

  async isAuthenticated() {
    return true;
  }

  getIdentity() {
    return this.identity;
  }
}

export const dummyPrincipal = {
  toText: () => 'dummy-principal-123456789',
  toString: () => 'dummy-principal-123456789'
};
