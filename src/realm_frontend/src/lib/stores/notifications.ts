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
        // Response might already be parsed by IC Candid, check type
        const notificationData = typeof response === 'string' ? JSON.parse(response) : response;
        notifications.set(notificationData.notifications || []);
        unreadCount.set(notificationData.unread_count || 0);
    } catch (error) {
        console.error('Failed to load notifications:', error);
        // Set empty data on error
        notifications.set([]);
        unreadCount.set(0);
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
