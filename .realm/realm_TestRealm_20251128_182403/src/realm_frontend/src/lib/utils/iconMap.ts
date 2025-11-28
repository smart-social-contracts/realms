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
    RectangleListSolid,
    TableColumnSolid,
    UsersOutline,
    HomeOutline,
    FileChartBarSolid,
    BellSolid,
    LandmarkSolid,
    BookOutline,
    BrainOutline,
    MapPinSolid,
    ProfileCardSolid,
    ObjectsColumnSolid,
    ScaleBalancedSolid,
    CheckCircleOutline,
    UsersGroupSolid
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
    'analytics': ChartPieOutline,
    'list': RectangleListSolid,
    'table': TableColumnSolid,
    'users': UsersOutline,
    'home': HomeOutline,
    'file': FileChartBarSolid,
    'bell': BellSolid,
    'building': LandmarkSolid,
    'book': BookOutline,
    'brain': BrainOutline,
    'map_pin': MapPinSolid,
    'id_card': ProfileCardSolid,
    'objects': ObjectsColumnSolid,
    'scale': ScaleBalancedSolid,
    'vote': CheckCircleOutline,
    'users_group': UsersGroupSolid
};

/**
 * Get an icon component by name, with fallback to default
 * @param iconName The name of the icon to retrieve
 * @param defaultIcon Default icon to use if not found
 * @returns The icon component
 */
export function getIcon(iconName: string, defaultIcon: any = LayersSolid): any {
    return iconMap[iconName] || defaultIcon;
}
