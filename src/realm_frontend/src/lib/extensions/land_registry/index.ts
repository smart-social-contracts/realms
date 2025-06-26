import LandRegistryComponent from './LandRegistry.svelte';
export default LandRegistryComponent;

import LandMap from './LandMap.svelte';
import LandTable from './LandTable.svelte';
import AdminControls from './AdminControls.svelte';

export {
    LandMap,
    LandTable,
    AdminControls
}

export const metadata = {
    name: 'Land Registry',
    description: 'Manage land ownership and visualize land parcels on a map',
    version: '1.0.0',
    icon: 'map',
    author: 'Smart Social Contracts Team',
    permissions: ['manage_land', 'view_land_registry']
};
