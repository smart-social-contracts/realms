// Extension metadata for the marketplace
export const metadata = {
	name: 'Extensions Marketplace',
	description: 'Browse and install extensions for your Smart Social Contracts platform',
	version: '1.0.0',
	author: 'Realms Team',
	icon: 'LayersSolid',
	profiles: ['admin'], // Only admins can access the marketplace
	permissions: ['read_extensions', 'manage_extensions']
};

// No default export component needed since marketplace is handled by routes
export default null;
