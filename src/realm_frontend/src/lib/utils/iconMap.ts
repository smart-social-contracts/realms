import { 
    WalletSolid, 
    CogOutline, 
    ChartPieOutline,
    LightbulbOutline,
    DollarOutline,
    ClipboardListSolid,
    LayersSolid,
    LifeSaverSolid,
    LockSolid,
    WandMagicSparklesOutline,
    ChartOutline,
    RectangleListSolid,
    TableColumnSolid,
    UsersOutline,
    HomeOutline,
    FileChartBarSolid
} from 'flowbite-svelte-icons';

/**
 * Map of icon names to their corresponding icon components
 * Used by the extension system to dynamically render icons
 */
export const iconMap: Record<string, any> = {
    'wallet': WalletSolid,
    'cog': CogOutline,
    'chart': ChartPieOutline,
    'chart-pie': ChartPieOutline,
    'lightbulb': LightbulbOutline,
    'dollar': DollarOutline,
    'clipboard': ClipboardListSolid,
    'layers': LayersSolid,
    'lifesaver': LifeSaverSolid,
    'lock': LockSolid,
    'wand': WandMagicSparklesOutline,
    'analytics': ChartOutline,
    'list': RectangleListSolid,
    'table': TableColumnSolid,
    'users': UsersOutline,
    'home': HomeOutline,
    'file': FileChartBarSolid
};

/**
 * Get an icon component by name, with fallback to default
 * @param iconName The name of the icon to retrieve
 * @param defaultIcon Default icon to use if not found
 * @returns The icon component
 */
export function getIcon(iconName: string, defaultIcon: any = LightbulbOutline): any {
    return iconMap[iconName] || defaultIcon;
}
