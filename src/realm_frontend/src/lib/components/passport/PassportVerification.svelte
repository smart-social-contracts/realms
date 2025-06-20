<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters.js';
  import { Button, Card, Heading, P, Spinner } from 'flowbite-svelte';
  import { CheckCircleSolid, ExclamationCircleSolid, ClipboardListSolid } from 'flowbite-svelte-icons';
  
  export let userId;
  
  let verificationStatus = 'idle'; // idle, generating, pending, verified, failed, error
  let verificationLink = '';
  let qrCodeData = '';
  let errorMessage = '';
  let verificationResult = null;
  let pollingInterval = null;
  
  async function generateVerificationLink() {
    try {
      verificationStatus = 'generating';
      errorMessage = '';
      
      console.log('Generating passport verification for user:', userId);
      const response = await backend.generate_passport_verification(userId);
      
      if (response.success) {
        const result = JSON.parse(response.data.Message);
        console.log('Verification link result:', result);
        
        if (result.success) {
          verificationLink = result.verification_link;
          qrCodeData = result.qr_code_url || generateQRCodeData(result.verification_link);
          verificationStatus = 'pending';
          startPolling();
        } else {
          verificationStatus = 'error';
          errorMessage = result.error || 'Failed to generate verification link';
        }
      } else {
        verificationStatus = 'error';
        errorMessage = response.data.Error || 'Backend error occurred';
      }
    } catch (error) {
      console.error('Error generating verification link:', error);
      verificationStatus = 'error';
      errorMessage = error.message || 'Network error occurred';
    }
  }
  
  function generateQRCodeData(link) {
    // For now, return the link itself - in a real implementation, 
    // this would generate a proper QR code image URL
    return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(link)}`;
  }
  
  async function checkVerificationStatus() {
    try {
      const response = await backend.check_passport_status(userId);
      
      if (response.success) {
        const result = JSON.parse(response.data.Message);
        console.log('Verification status result:', result);
        
        if (result.success) {
          if (result.status === 'verified') {
            verificationStatus = 'verified';
            verificationResult = result;
            stopPolling();
            
            // Create the passport identity
            await createPassportIdentity(result);
          } else if (result.status === 'failed') {
            verificationStatus = 'failed';
            errorMessage = 'Passport verification failed';
            stopPolling();
          }
          // If status is still 'pending', continue polling
        } else {
          console.warn('Status check returned error:', result.error);
        }
      }
    } catch (error) {
      console.error('Error checking verification status:', error);
    }
  }
  
  async function createPassportIdentity(verificationData) {
    try {
      const response = await backend.create_passport_identity(userId, JSON.stringify(verificationData));
      
      if (response.success) {
        const result = JSON.parse(response.data.Message);
        console.log('Identity creation result:', result);
        
        if (!result.success) {
          console.warn('Identity creation failed:', result.error);
        }
      }
    } catch (error) {
      console.error('Error creating passport identity:', error);
    }
  }
  
  function startPolling() {
    // Poll every 5 seconds for verification status
    pollingInterval = setInterval(checkVerificationStatus, 5000);
  }
  
  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }
  
  function resetVerification() {
    verificationStatus = 'idle';
    verificationLink = '';
    qrCodeData = '';
    errorMessage = '';
    verificationResult = null;
    stopPolling();
  }
  
  onMount(() => {
    return () => {
      stopPolling();
    };
  });
</script>

<Card size="xl" class="p-6">
  <div class="text-center">
    <div class="flex items-center justify-center mb-4">
      <ClipboardListSolid class="w-8 h-8 text-blue-600 dark:text-blue-400 mr-2" />
      <Heading tag="h3">Verify Your Passport</Heading>
    </div>
    
    {#if verificationStatus === 'idle'}
      <P class="mb-6 text-gray-600 dark:text-gray-400">
        Use zero-knowledge proofs to verify your passport identity securely and privately.
        Your passport data never leaves your device.
      </P>
      <Button on:click={generateVerificationLink} class="px-6 py-3">
        Start Passport Verification
      </Button>
      
    {:else if verificationStatus === 'generating'}
      <div class="flex items-center justify-center mb-4">
        <Spinner class="mr-3" size="4" />
        <P>Generating verification link...</P>
      </div>
      
    {:else if verificationStatus === 'pending'}
      <P class="mb-4 text-gray-600 dark:text-gray-400">
        Scan the QR code with your RariMe app to verify your passport
      </P>
      
      {#if qrCodeData}
        <div class="mb-6">
          <img src={qrCodeData} alt="Passport Verification QR Code" class="mx-auto border rounded-lg shadow-sm" />
        </div>
      {/if}
      
      <div class="flex items-center justify-center mb-4">
        <Spinner class="mr-3" size="4" />
        <P class="text-blue-600 dark:text-blue-400">Waiting for verification...</P>
      </div>
      
      <P class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Open your RariMe app and scan the QR code above
      </P>
      
      <Button color="alternative" on:click={resetVerification} size="sm">
        Cancel
      </Button>
      
    {:else if verificationStatus === 'verified'}
      <div class="text-green-600 dark:text-green-400 mb-4">
        <CheckCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-green-600 dark:text-green-400">Passport Verified Successfully!</Heading>
      </div>
      
      {#if verificationResult}
        <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 mb-4">
          <P class="text-sm text-green-800 dark:text-green-200">
            <strong>Citizenship:</strong> {verificationResult.citizenship || 'Verified'}
          </P>
          {#if verificationResult.verified_at}
            <P class="text-sm text-green-800 dark:text-green-200">
              <strong>Verified:</strong> {new Date(verificationResult.verified_at).toLocaleString()}
            </P>
          {/if}
        </div>
      {/if}
      
      <P class="text-sm text-gray-600 dark:text-gray-400">
        Your passport identity has been securely linked to your account using zero-knowledge proofs.
      </P>
      
    {:else if verificationStatus === 'failed'}
      <div class="text-red-600 dark:text-red-400 mb-4">
        <ExclamationCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-red-600 dark:text-red-400">Verification Failed</Heading>
      </div>
      
      <P class="text-red-600 dark:text-red-400 mb-4">
        Passport verification was not successful. Please try again.
      </P>
      
      <Button on:click={resetVerification}>
        Try Again
      </Button>
      
    {:else if verificationStatus === 'error'}
      <div class="text-red-600 dark:text-red-400 mb-4">
        <ExclamationCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-red-600 dark:text-red-400">Error Occurred</Heading>
      </div>
      
      <P class="text-red-600 dark:text-red-400 mb-4">
        {errorMessage}
      </P>
      
      <Button on:click={resetVerification}>
        Try Again
      </Button>
    {/if}
  </div>
</Card>
