console.log('=== TEST CANISTERS LOADING ===');

import { createDummyBackend } from './dummyBackend.js';

console.log('=== DUMMY BACKEND IMPORTED IN TEST ===');

const testBackend = createDummyBackend();
console.log('=== TEST BACKEND CREATED ===', testBackend);

export { testBackend };
