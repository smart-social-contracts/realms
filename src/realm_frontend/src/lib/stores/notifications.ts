import { writable } from 'svelte/store';
// @ts-ignore
import { backend } from '$lib/canisters';

export interface NotificationItem {
    id: string;
    title: string;
    message: string;
    timestamp: string;
    read: boolean;
    icon?: string;
    href?: string;
    color?: string;
}

export const notifications = writable<NotificationItem[]>([]);
export const unreadCount = writable<number>(0);

export async function loadNotifications() {
    try {
        const response = await backend.extension_sync_call({
            extension_name: 'notifications',
            function_name: 'get_notifications',
            args: '{}'
        });
        const notificationData = JSON.parse(response);
        notifications.set(notificationData.notifications || []);
        unreadCount.set(notificationData.unread_count || 0);
    } catch (error) {
        console.error('Failed to load notifications:', error);
        const sampleNotifications = [
            {
                id: '1',
                title: 'Welcome to Realms',
                message: 'Your account has been successfully created and verified.',
                timestamp: 'a few moments ago',
                read: false,
                icon: 'users',
                href: '/dashboard',
                color: 'green'
            },
            {
                id: '2',
                title: 'New Task Assignment',
                message: 'You have been assigned a new governance task that requires your attention.',
                timestamp: '10 minutes ago',
                read: false,
                icon: 'clipboard',
                href: '/ggg',
                color: 'blue'
            },
            {
                id: '3',
                title: 'Vault Transaction',
                message: 'A transfer of 100 tokens has been completed successfully.',
                timestamp: '1 hour ago',
                read: true,
                icon: 'wallet',
                href: '/extensions/vault_manager',
                color: 'purple'
            }
        ];
        notifications.set(sampleNotifications);
        unreadCount.set(sampleNotifications.filter(n => !n.read).length);
    }
}

export async function markAsRead(notificationId: string) {
    try {
        await backend.extension_sync_call({
            extension_name: 'notifications',
            function_name: 'mark_as_read',
            args: JSON.stringify({ notification_id: notificationId })
        });
        
        notifications.update(items => {
            const updated = items.map(item => 
                item.id === notificationId ? { ...item, read: true } : item
            );
            unreadCount.set(updated.filter(n => !n.read).length);
            return updated;
        });
    } catch (error) {
        console.error('Failed to mark notification as read:', error);
        notifications.update(items => {
            const updated = items.map(item => 
                item.id === notificationId ? { ...item, read: true } : item
            );
            unreadCount.set(updated.filter(n => !n.read).length);
            return updated;
        });
    }
}
