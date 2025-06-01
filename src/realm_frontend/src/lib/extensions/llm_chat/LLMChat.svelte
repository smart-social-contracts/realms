<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { Card, Button, Textarea, Spinner } from 'flowbite-svelte';
	import { PaperPlaneSolid, MessagesSolid } from 'flowbite-svelte-icons';

	// Define message interface to fix TypeScript errors
	interface ChatMessage {
		text: string;
		isUser: boolean;
	}

	// State variables
	let messages: ChatMessage[] = [];
	let newMessage = '';
	let isLoading = false;
	let error = '';
	let messagesContainer: HTMLElement;

	// LLM API configuration
	const API_URL = "https://api.example.com/v1/chat"; // Change this to your LLM API endpoint

	// Auto-scroll to bottom of messages when content changes
	afterUpdate(() => {
		scrollToBottom();
	});

	// Function to scroll to bottom of messages container
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
		
		try {
			// Make direct HTTP request to the LLM API
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Accept': 'application/json'
				},
				body: JSON.stringify({
					message: messageToSend,
					max_tokens: 1000
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}

			const data = await response.json();
			
			// Add response to the chat
			messages = [...messages, { 
				text: data.response || "No response from LLM", 
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

<div class="w-full h-full flex flex-col p-0 m-0">
	<h2 class="text-2xl font-bold p-4">LLM Chat</h2>
	
	<div class="w-full flex-grow flex flex-col">
		<Card class="w-full h-full flex-grow flex flex-col m-0 p-0 rounded-none border-0">
			<div 
				bind:this={messagesContainer}
				class="flex-grow overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800"
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
								class="inline-block rounded-lg px-4 py-2 max-w-[80%] text-left {
									message.isUser 
										? 'bg-primary-600 text-white' 
										: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
								}"
							>
								{message.text}
							</div>
						</div>
					{/each}
					
					{#if isLoading}
						<div class="flex items-center justify-start mb-4">
							<div class="inline-block rounded-lg px-4 py-2 bg-gray-200 dark:bg-gray-700">
								<Spinner size="4" />
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
			
			<div class="flex p-2 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
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
		</Card>
	</div>
</div> 