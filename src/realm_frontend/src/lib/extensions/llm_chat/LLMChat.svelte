<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { Card, Button, Textarea, Spinner, Toggle } from 'flowbite-svelte';
	import { PaperPlaneSolid, MessagesSolid, DatabaseSolid } from 'flowbite-svelte-icons';
	import SvelteMarkdown from 'svelte-markdown';
	// @ts-ignore
	import { backend } from '$lib/canisters';
	// @ts-ignore
	import { canisterId as backendCanisterId } from 'declarations/realm_backend';
	import { principal } from '$lib/stores/auth';

	// Define message interface to fix TypeScript errors
	interface ChatMessage {
		text: string;
		isUser: boolean;
	}

	// Interface for the payload sent to the LLM API
	interface LLMPayload {
		message: string;
		max_tokens: number;
		realm_data?: any;
	}

	 
	// State variables
	let messages: ChatMessage[] = [];
	let newMessage = '';
	let isLoading = false;
	let error = '';
	let messagesContainer: HTMLElement;
	let includeRealmData = true;
	let realmData: any = null;
	let isLoadingRealmData = false;
	let userPrincipal = $principal || '';

	// LLM API configuration

	// const isLocalhost = window.location.hostname === 'localhost' || 
	// 		window.location.hostname === '127.0.0.1' ||
	// 		window.location.hostname.includes('.localhost');

	const isLocalhost = false;
	console.log("isLocalhost", isLocalhost);
	
	// Function to fetch server host from remote config
	async function fetchServerHost(): Promise<string> {
			console.log("Fetching server host from remote config...");
			const response = await fetch('https://raw.githubusercontent.com/smart-social-contracts/ashoka/refs/heads/main/production.env');
			const text = await response.text();
			
			// Parse SERVER_HOST from the environment file format
			const lines = text.trim().split('\n');
			for (const line of lines) {
				if (line.startsWith('SERVER_HOST=')) {
					const serverHost = line.split('=')[1].trim();
					console.log("Found SERVER_HOST in remote config:", serverHost);
					return serverHost;
				}
			}
			throw new Error('SERVER_HOST not found in remote config');
	}
	
	// Determine API URL based on environment
	let API_URL = '';
	
	// Initialize API URL
	const initializeApiUrl = async () => {
		if (isLocalhost) {
			API_URL = "http://localhost:5000/api/ask";
		} else {
			// Fetch production server host dynamically
			const serverHost = await fetchServerHost();
			API_URL = `${serverHost}api/ask`;
		}
		console.log("API_URL set to:", API_URL);
	};
	
	// Get the canister ID dynamically
	let REALM_CANISTER_ID = "";
	
	onMount(async () => {
		try {
			// Try to get canister ID from direct import
			REALM_CANISTER_ID = backendCanisterId.toString();
			console.log("Got canister ID from direct import:", REALM_CANISTER_ID);
		} catch (err) {
			console.error("Error getting canister ID from direct import:", err);
			
			try {
				// Alternative method: try to get it from the URL
				const hostname = window.location.hostname;
				// Format: uzt4z-lp777-77774-qaaaq-cai.localhost:8000
				if (hostname.includes('-')) {
					const parts = hostname.split('.');
					if (parts.length > 0) {
						REALM_CANISTER_ID = parts[0];
						console.log("Got canister ID from hostname:", REALM_CANISTER_ID);
					}
				}
			} catch (err2) {
				console.error("Error getting canister ID from URL:", err2);
			}
			
			// Fallback if all else fails
			if (!REALM_CANISTER_ID) {
				REALM_CANISTER_ID = "uxrrr-q7777-77774-qaaaq-cai"; // Default fallback
				console.log("Using default canister ID:", REALM_CANISTER_ID);
			}
		}
		
		// Initialize API URL
		await initializeApiUrl();
	});

	// Auto-scroll to bottom of messages when content changes
	afterUpdate(() => {
		scrollToBottom();
	});

	// Watch for message changes to trigger scroll
	$: {
		messages;
		setTimeout(scrollToBottom, 100); // Delay slightly to ensure rendering is complete
	}

	// Function to scroll to bottom of messages container
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	// Function to fetch realm data
	async function fetchRealmData(): Promise<void> {
		if (isLoadingRealmData) return;
		
		isLoadingRealmData = true;
		try {
			// Call the backend extension to get realm data
			const response = await backend.extension_async_call({
				extension_name: "llm_chat",
				function_name: "get_realm_data",
				args: ""
			});
			
			realmData = response;
			console.log("Realm data fetched:", realmData);
		} catch (err) {
			console.error("Error fetching realm data:", err);
			error = "Failed to get realm data. LLM responses may be less accurate.";
		} finally {
			isLoadingRealmData = false;
		}
	}

	// Function to send a message to the LLM
	async function sendMessage(): Promise<void> {
		if (!newMessage.trim()) return;
		
		// Add user message to the chat
		messages = [...messages, { text: newMessage, isUser: true }];
		
		// Clear input and show loading state
		const messageToSend = newMessage;
		newMessage = '';
		isLoading = true;
		error = '';
		
		// Add a placeholder message for the AI response that we'll update as we stream
		const aiMessageIndex = messages.length;
		messages = [...messages, { text: '', isUser: false }];
		
		try {
			const payload = {
				question: messageToSend,
				realm_principal: REALM_CANISTER_ID,
				user_principal: userPrincipal,
				stream: true
			};

			console.log("Sending payload to LLM API:", payload);
			
			// Make streaming HTTP request to the LLM API
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Accept': 'text/event-stream'
				},
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}

			// Handle streaming response
			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error('Response body is not readable');
			}

			const decoder = new TextDecoder();
			let accumulatedText = '';

			try {
				while (true) {
					const { done, value } = await reader.read();
					
					if (done) {
						break;
					}

					// Decode the chunk
					const chunk = decoder.decode(value, { stream: true });
					console.log('Received chunk:', chunk);
					
					// Since your server sends plain text, just accumulate it directly
					accumulatedText += chunk;
					
					// Update the AI message in real-time
					messages = messages.map((msg, index) => 
						index === aiMessageIndex 
							? { ...msg, text: accumulatedText }
							: msg
					);
				}
			} finally {
				reader.releaseLock();
			}

			// Ensure we have some response
			if (!accumulatedText.trim()) {
				messages = messages.map((msg, index) => 
					index === aiMessageIndex 
						? { ...msg, text: "No response from LLM" }
						: msg
				);
			}

		} catch (err) {
			console.error("Error calling LLM:", err);
			error = "Failed to get response from LLM. Please try again.";
			
			// Remove the placeholder message if there was an error
			messages = messages.slice(0, -1);
		} finally {
			isLoading = false;
		}
	}

	// Handle Enter key in textarea
	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
</script>

<div class="w-full h-full flex flex-col p-0 m-0 max-w-none">
	<h2 class="text-2xl font-bold p-4">Governance AI assistant</h2>
	
	<div class="w-full flex-grow flex flex-col overflow-hidden">
		<Card class="w-full h-full flex-grow flex flex-col m-0 p-0 rounded-none border-0 max-w-none">
			<div 
				bind:this={messagesContainer}
				class="flex-grow overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800"
				style="min-height: 200px; max-height: calc(100vh - 200px);"
			>
				{#if messages.length === 0}
					<div class="text-center text-gray-500 dark:text-gray-400 py-8">
						<MessagesSolid class="w-12 h-12 mx-auto mb-2" />
						<p>Start a conversation with the LLM!</p>
					</div>
				{:else}
					{#each messages as message}
						<div class="mb-4 {message.isUser ? 'text-right' : ''}">
							<div 
								class="inline-block rounded-lg px-4 py-2 max-w-[90%] text-left {
									message.isUser 
										? 'bg-primary-600 text-white' 
										: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
								}"
							>
								{#if message.isUser}
									{message.text}
								{:else}
									<div class="markdown-content">
										<SvelteMarkdown source={message.text} />
									</div>
								{/if}
							</div>
						</div>
					{/each}
					
					{#if isLoading}
						<div class="flex items-center justify-start mb-4">
							<div class="inline-block rounded-lg px-4 py-2 bg-gray-200 dark:bg-gray-700">
								<Spinner size="4" class="mr-2" />
								<span>AI is thinking...</span>
							</div>
						</div>
					{/if}
					
					{#if error}
						<div class="mb-4">
							<div class="inline-block rounded-lg px-4 py-2 bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100">
								{error}
							</div>
						</div>
					{/if}
				{/if}
			</div>
			
			<div class="flex flex-col p-2 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 sticky bottom-0">
				<!-- Realm data toggle -->
				<div class="flex items-center mb-2">
					<Toggle bind:checked={includeRealmData} size="small" />
					<span class="ml-2 text-sm text-gray-700 dark:text-gray-300 flex items-center">
						<DatabaseSolid class="w-4 h-4 mr-1" />
						Include realm data
						{#if isLoadingRealmData}
							<Spinner size="4" class="ml-2" />
						{/if}
					</span>
					{#if includeRealmData && !realmData && !isLoadingRealmData}
						<Button size="xs" color="light" class="ml-2" on:click={fetchRealmData}>Fetch Data</Button>
					{/if}
				</div>
				
				<!-- Message input -->
				<div class="flex">
					<Textarea
						class="flex-grow resize-none rounded-r-none"
						placeholder="Type your message..."
						rows="2"
						bind:value={newMessage}
						on:keydown={handleKeydown}
					/>
					<Button 
						color="primary" 
						class="rounded-l-none"
						disabled={isLoading || !newMessage.trim()}
						on:click={sendMessage}
					>
						<PaperPlaneSolid class="w-5 h-5" />
					</Button>
				</div>
			</div>
		</Card>
	</div>
</div> 

<style>
	.markdown-content :global(h1) {
		font-size: 1.8rem;
		font-weight: 700;
		margin: 1rem 0;
		color: inherit;
	}
	
	.markdown-content :global(h2) {
		font-size: 1.5rem;
		font-weight: 700;
		margin: 0.8rem 0;
		color: inherit;
	}
	
	.markdown-content :global(h3) {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0.6rem 0;
		color: inherit;
	}
	
	.markdown-content :global(ul) {
		list-style-type: disc !important;
		margin: 0.5rem 0 !important;
		padding-left: 2rem !important;
	}
	
	.markdown-content :global(ol) {
		list-style-type: decimal !important;
		margin: 0.5rem 0 !important;
		padding-left: 2rem !important;
	}
	
	.markdown-content :global(li) {
		display: list-item !important;
		margin: 0.25rem 0 !important;
	}
	
	.markdown-content :global(p) {
		margin: 0.5rem 0 !important;
	}
	
	.markdown-content :global(code) {
		font-family: monospace;
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.1rem 0.2rem;
		border-radius: 0.2rem;
	}
	
	.markdown-content :global(pre) {
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.5rem;
		border-radius: 0.3rem;
		overflow-x: auto;
		margin: 0.5rem 0;
	}
	
	.markdown-content :global(blockquote) {
		border-left: 3px solid #ccc;
		padding-left: 0.8rem;
		margin: 0.5rem 0 0.5rem 0.5rem;
		color: #555;
	}
</style> 