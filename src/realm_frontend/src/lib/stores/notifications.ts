import { writable } from 'svelte/store';

let backend: any;
if (typeof window !== 'undefined' && (window as any).__DUMMY_MODE__) {
    // @ts-ignore - Dynamic import for dev dummy mode
    import('$lib/dummyCanisters').then(module => {
        backend = module.backend;
    });
} else {
    // @ts-ignore - Dynamic import for canisters module
    import('$lib/canisters').then(module => {
        backend = module.backend;
    });
}

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
        if (backend) {
            const response = await backend.extension_sync_call({
                extension_name: 'notifications',
                function_name: 'get_notifications',
                args: '{}'
            });
            const notificationData = JSON.parse(response);
            notifications.set(notificationData.notifications || []);
            unreadCount.set(notificationData.unread_count || 0);
            return;
        }
        throw new Error('Backend not available - using sample data');
    } catch (error) {
        console.log('Using sample notifications data:', (error as Error).message);
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
        if (backend) {
            await backend.extension_sync_call({
                extension_name: 'notifications',
                function_name: 'mark_as_read',
                args: JSON.stringify({ notification_id: notificationId })
            });
        } else {
            throw new Error('Backend not available - using local update');
        }
    } catch (error) {
        console.log('Using local notification update:', (error as Error).message);
        notifications.update(items => {
            const updated = items.map(item => 
                item.id === notificationId ? { ...item, read: true } : item
            );
            unreadCount.set(updated.filter(n => !n.read).length);
            return updated;
        });
    }
}
