<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { Card, Button, Textarea, Spinner, Toggle } from 'flowbite-svelte';
	import { PaperPlaneSolid, MessagesSolid, DatabaseSolid } from 'flowbite-svelte-icons';
	import SvelteMarkdown from 'svelte-markdown';
	// @ts-ignore
	import { backend } from '$lib/canisters';
	
	// Remove direct import and handle canister ID differently
	// @ts-ignore
	// import { canisterId as backendCanisterId } from 'declarations/realm_backend';

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

	// LLM API configuration

	const isLocalhost = window.location.hostname === 'localhost' || 
			window.location.hostname === '127.0.0.1' ||
			window.location.hostname.includes('.localhost');
	console.log("isLocalhost", isLocalhost);
	
	// Determine API URL based on environment
	const API_URL = (() => {
		// Check if we're running locally

		
		if (isLocalhost) {
			return "http://localhost:5000/api/ask";
		} else {
			// Production URL
			return "https://jvql982sbyh2vo-5000.proxy.runpod.net/api/ask";
		}
	})();
	
	// Get the canister ID dynamically
	let REALM_CANISTER_ID = "";
	
	onMount(async () => {
		try {
			// Get canister ID from environment variables or window.env if available
			if (typeof window !== 'undefined' && window['canisterIds'] && window['canisterIds']['realm_backend']) {
				REALM_CANISTER_ID = window['canisterIds']['realm_backend'];
				console.log("Got canister ID from window.canisterIds:", REALM_CANISTER_ID);
			} else {
				// Try to get from process.env at build time (may not work in browser)
				REALM_CANISTER_ID = process.env.CANISTER_ID_REALM_BACKEND || "";
				console.log("Got canister ID from process.env:", REALM_CANISTER_ID);
			}
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
		
		// // If realm data is enabled but not loaded, load it first
		// if (includeRealmData && !realmData) {
		// 	await fetchRealmData();
		// }
		
		try {
			// Prepare request payload
			const payload = {
				question: messageToSend,
				realm_canister_id: REALM_CANISTER_ID
			};
			
			// Make direct HTTP request to the LLM API
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Accept': 'application/json'
				},
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}

			const data = await response.json();
			
			// Add response to the chat
			messages = [...messages, { 
				text: data.ai_response || "No response from LLM", 
				isUser: false 
			}];
		} catch (err) {
			console.error("Error calling LLM:", err);
			error = "Failed to get response from LLM. Please try again.";
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
	<h2 class="text-2xl font-bold p-4">AI assistant</h2>
	
	<div class="w-full flex-grow flex flex-col overflow-hidden">
		<Card class="w-full h-full flex-grow flex flex-col m-0 p-0 rounded-none border-0 max-w-none">
			<div 
				bind:this={messagesContainer}
				class="flex-grow overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800"
				style="min-height: 200px; max-height: calc(100vh - 200px);"
			>
				{#if messages.length === 0}
					<div class="text-center py-8 max-w-2xl mx-auto">
						<div class="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-6 shadow-sm border border-blue-100 dark:border-blue-800">
							<div class="flex items-center justify-center">
								<div class="rounded-full bg-blue-100 dark:bg-blue-800 p-3 mr-4">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-blue-600 dark:text-blue-300">
										<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
									</svg>
								</div>
								<h3 class="text-xl font-bold text-blue-700 dark:text-blue-300">Hello! I am Ashoka, your Governance AI assistant.</h3>
							</div>
							<p class="mt-3 text-gray-600 dark:text-gray-300">How can I help you today?</p>
							
							<!-- Template prompts -->
							<div class="mt-6">
								<p class="text-sm font-medium text-gray-700 dark:text-gray-400 mb-3">Try asking me:</p>
								<div class="grid gap-2">
									<button 
										class="text-left p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
										on:click={() => {
											newMessage = "Describe the status of this realm";
											sendMessage();
										}}
									>
										"Describe the status of this realm"
									</button>
									<button 
										class="text-left p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
										on:click={() => {
											newMessage = "How to improve the economy of this realm?";
											sendMessage();
										}}
									>
										"How to improve the economy of this realm?"
									</button>
									<button 
										class="text-left p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
										on:click={() => {
											newMessage = "Spot potential inefficiencies in this realm";
											sendMessage();
										}}
									>
										"Spot potential inefficiencies in this realm"
									</button>
								</div>
							</div>
						</div>
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