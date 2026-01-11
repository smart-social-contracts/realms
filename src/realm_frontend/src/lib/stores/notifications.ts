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
        console.log('[notifications] Loading notifications...');
        const result = await backend.extension_sync_call({
            extension_name: 'notifications',
            function_name: 'get_notifications',
            args: '{}'
        });
        console.log('[notifications] Raw result:', result);
        // ExtensionCallResponse is { response: string, success: bool }
        const responseStr = result.response || result;
        console.log('[notifications] Response string:', responseStr);
        const notificationData = typeof responseStr === 'string' ? JSON.parse(responseStr) : responseStr;
        console.log('[notifications] Parsed data:', notificationData);
        console.log('[notifications] Notifications array:', notificationData.notifications);
        console.log('[notifications] Unread count:', notificationData.unread_count);
        notifications.set(notificationData.notifications || []);
        unreadCount.set(notificationData.unread_count || 0);
    } catch (error) {
        console.error('[notifications] Failed to load notifications:', error);
        // Set empty data on error
        notifications.set([]);
        unreadCount.set(0);
    }
}

export async function markAsRead(notificationId: string, read: boolean = true) {
    try {
        await backend.extension_sync_call({
            extension_name: 'notifications',
            function_name: 'mark_as_read',
            args: JSON.stringify({ id: notificationId, read })
        });
        
        notifications.update(items => {
            const updated = items.map(item => 
                item.id === notificationId ? { ...item, read } : item
            );
            unreadCount.set(updated.filter(n => !n.read).length);
            return updated;
        });
    } catch (error) {
        console.error('Failed to update notification read status:', error);
        notifications.update(items => {
            const updated = items.map(item => 
                item.id === notificationId ? { ...item, read } : item
            );
            unreadCount.set(updated.filter(n => !n.read).length);
            return updated;
        });
    }
}
