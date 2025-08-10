import NotificationsComponent from './Notifications.svelte';
export default NotificationsComponent;

export const metadata = {
    name: 'Notifications',
    description: 'View and manage your notifications in an inbox-style interface',
    version: '1.0.0',
    icon: 'bell',
    author: 'Smart Social Contracts Team',
    permissions: ['read_notifications'],
    profiles: ['member', 'admin']
};
