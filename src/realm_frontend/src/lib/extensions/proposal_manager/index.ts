import ProposalManagerComponent from './ProposalManager.svelte';
export default ProposalManagerComponent;

export const metadata = {
    name: 'Proposal Manager',
    description: 'Manage proposals with voting and administration features',
    version: '1.0.0',
    icon: 'document-text',
    author: 'Smart Social Contracts Team',
    permissions: ['read_proposals', 'create_proposals', 'vote_proposals', 'manage_proposals'],
    profiles: ['admin', 'member']
};
