import JusticeLitigationComponent from './JusticeLitigation.svelte';
export default JusticeLitigationComponent;

import LitigationsList from './LitigationsList.svelte';
import CreateLitigationForm from './CreateLitigationForm.svelte';

export {
    LitigationsList,
    CreateLitigationForm
}

export const metadata = {
    name: 'Justice Litigation',
    description: 'External justice litigation system integration',
    version: '1.0.0',
    icon: 'lock',
    author: 'Smart Social Contracts Team',
    permissions: ['litigation_access']
};
