<script lang="ts">
  import { backend } from '$lib/canisters.js';
  import { Button, Card, Heading, P, Spinner } from 'flowbite-svelte';
  import { CheckCircleSolid, ExclamationCircleSolid, ClipboardListSolid } from 'flowbite-svelte-icons';
  import { styles, cn } from '../../theme/utilities';
  
  export let userId: string;
  
  let verificationStatus = 'idle'; // idle, generating, pending, verified, failed, error
  let verificationLink = '';
  let qrCodeData = '';
  let errorMessage = '';
  let verificationResult: any = null;
  let sessionId = '';
  let eventId = '';

  
  async function generateVerificationLink() {
    try {
      verificationStatus = 'generating';
      errorMessage = '';
      
      console.log('Generating passport verification for user:', userId);
      
      // Get event_id from backend
      const eventIdResponse = await backend.extension_sync_call({
        extension_name: "passport_verification",
        function_name: "get_current_application_id",
        args: ""
      });
      
      if (eventIdResponse.success) {
        const eventIdData = JSON.parse(eventIdResponse.response);
        eventId = eventIdData.application_id || '';
      }
      
      const response = await backend.extension_async_call({
        extension_name: "passport_verification",
        function_name: "get_verification_link",
        args: userId || ""
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        console.log('Verification link result:', result);
        
        if (result.data && result.data.attributes) {
          const verificationUrl = result.data.attributes.rarime_app_url || result.data.attributes.get_proof_params;
          verificationLink = verificationUrl;
          qrCodeData = generateQRCodeData(verificationUrl);
          sessionId = result.data.id || userId;
          verificationStatus = 'pending';
        } else {
          verificationStatus = 'error';
          errorMessage = 'Invalid response format from verification service';
        }
      } else {
        verificationStatus = 'error';
        errorMessage = response.response || 'Backend error occurred';
      }
    } catch (error: any) {
      console.error('Error generating verification link:', error);
      verificationStatus = 'error';
      errorMessage = error.message || 'Network error occurred';
    }
  }
  
  function generateQRCodeData(link: string) {
    // For now, return the link itself - in a real implementation, 
    // this would generate a proper QR code image URL
    return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(link)}`;
  }
  
  async function checkVerificationStatus() {
    try {
      const response = await backend.extension_async_call({
        extension_name: "passport_verification",
        function_name: "check_verification_status",
        args: userId || ""
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        console.log('Verification status result:', result);
        
        if (result.data && result.data.attributes) {
          const status = result.data.attributes.status;
          if (status === 'verified') {
            verificationStatus = 'verified';
            verificationResult = result.data.attributes;
            
            await createPassportIdentity(result);
          } else if (status === 'failed') {
            verificationStatus = 'failed';
            errorMessage = 'Passport verification failed';
          }
        } else {
          console.warn('Unexpected response format:', result);
        }
      }
    } catch (error) {
      console.error('Error checking verification status:', error);
    }
  }
  
  async function createPassportIdentity(verificationData: any) {
    try {
      const response = await backend.extension_sync_call({
        extension_name: "passport_verification",
        function_name: "create_passport_identity",
        args: JSON.stringify(verificationData)
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        console.log('Identity creation result:', result);
        
        if (!result.success) {
          console.warn('Identity creation failed:', result.error);
        }
      }
    } catch (error) {
      console.error('Error creating passport identity:', error);
    }
  }
  
  function resetVerification() {
    verificationStatus = 'idle';
    verificationLink = '';
    qrCodeData = '';
    errorMessage = '';
    verificationResult = null;
    sessionId = '';
    eventId = '';
  }
</script>

<Card size="xl" class="p-6">
  <div class="text-center">
    <div class="flex items-center justify-center mb-4">
      <ClipboardListSolid class="w-8 h-8 text-gray-600 dark:text-gray-400 mr-2" />
      <Heading tag="h3">Verify Your Passport</Heading>
    </div>
    
    {#if verificationStatus === 'idle'}
      <P class="mb-6 text-gray-600 dark:text-gray-400">
        Use zero-knowledge proofs to verify your passport identity securely and privately.
        Your passport data never leaves your device.
      </P>
      <Button on:click={generateVerificationLink} class={cn(styles.button.primary(), "px-6 py-3")}>
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
        <div class="mb-4">
          <img src={qrCodeData} alt="Passport Verification QR Code" class="mx-auto border rounded-lg shadow-sm" />
        </div>
      {/if}
      
      {#if sessionId || eventId}
        <div class="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <P class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Verification Details:</P>
          {#if sessionId}
            <P class="text-xs text-gray-600 dark:text-gray-400 mb-1 font-mono break-all">
              <strong>Session ID:</strong> {sessionId}
            </P>
          {/if}
          {#if eventId}
            <P class="text-xs text-gray-600 dark:text-gray-400 font-mono break-all">
              <strong>Event ID:</strong> {eventId}
            </P>
          {/if}
        </div>
      {/if}
      
      <div class="flex items-center justify-center mb-4">
        <Spinner class="mr-3" size="4" />
        <P class="text-gray-600 dark:text-gray-400">Waiting for verification...</P>
      </div>
      
      <P class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Open your RariMe app and scan the QR code above
      </P>
      
      <div class="flex gap-2 justify-center">
        <Button on:click={checkVerificationStatus} size="sm" class={styles.button.primary()}>
          Check Status
        </Button>
        <Button color="alternative" on:click={resetVerification} size="sm">
          Cancel
        </Button>
      </div>
      
    {:else if verificationStatus === 'verified'}
      <div class="text-gray-700 dark:text-gray-300 mb-4">
        <CheckCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-gray-700 dark:text-gray-300">Passport Verified Successfully!</Heading>
      </div>
      
      {#if verificationResult}
        <div class={cn(styles.alert.success(), "p-4 mb-4")}>
          <P class="text-sm text-gray-800 dark:text-gray-200">
            <strong>Citizenship:</strong> {verificationResult.citizenship || 'Verified'}
          </P>
          {#if verificationResult.verified_at}
            <P class="text-sm text-gray-800 dark:text-gray-200">
              <strong>Verified:</strong> {new Date(verificationResult.verified_at).toLocaleString()}
            </P>
          {/if}
        </div>
      {/if}
      
      <P class="text-sm text-gray-600 dark:text-gray-400">
        Your passport identity has been securely linked to your account using zero-knowledge proofs.
      </P>
      
    {:else if verificationStatus === 'failed'}
      <div class="text-gray-700 dark:text-gray-300 mb-4">
        <ExclamationCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-gray-700 dark:text-gray-300">Verification Failed</Heading>
      </div>
      
      <P class="text-gray-600 dark:text-gray-400 mb-4">
        Passport verification was not successful. Please try again.
      </P>

      <Button on:click={resetVerification} class={cn(styles.button.primary())}>
        Try Again
      </Button>
      
    {:else if verificationStatus === 'error'}
      <div class="text-gray-700 dark:text-gray-300 mb-4">
        <ExclamationCircleSolid class="w-12 h-12 mx-auto mb-2" />
        <Heading tag="h4" class="text-gray-700 dark:text-gray-300">Error Occurred</Heading>
      </div>

      <P class="text-gray-600 dark:text-gray-400 mb-4">
        {errorMessage}
      </P>

      <Button on:click={resetVerification} class={cn(styles.button.primary())}>
        Try Again
      </Button>
    {/if}
  </div>
</Card>
