<script>
  console.log('=== TEST PAGE COMPONENT LOADING ===');
  
  import { testBackend } from '$lib/test-canisters.js';
  
  console.log('=== TEST BACKEND IMPORTED ===', testBackend);
  
  let status = 'Loading...';
  
  async function callTestBackend() {
    try {
      console.log('=== CALLING TEST BACKEND ===');
      const response = await testBackend.status();
      console.log('=== TEST RESPONSE ===', response);
      status = JSON.stringify(response, null, 2);
    } catch (error) {
      console.error('=== TEST ERROR ===', error);
      status = 'Error: ' + error.message;
    }
  }
  
  callTestBackend();
</script>

<h1>Dummy Backend Test (Page Route)</h1>
<pre>{status}</pre>
