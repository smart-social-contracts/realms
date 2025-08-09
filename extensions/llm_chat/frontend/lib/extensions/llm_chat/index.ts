// Export the component as default for dynamic loading
import LLMChatComponent from './LLMChat.svelte';
export default LLMChatComponent;

// Extension metadata for the marketplace
export const metadata = {
    name: 'AI Assistant',
    description: 'Chat with an LLM model via HTTP',
    version: '0.1.0',
    icon: 'chat',
    author: 'Smart Social Contracts Team',
    permissions: [],
    profiles: []
};   