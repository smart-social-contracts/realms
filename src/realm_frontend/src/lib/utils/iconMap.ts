import {
	IconWallet,
	IconSettings,
	IconChartPie,
	IconBulb,
	IconCurrencyDollar,
	IconClipboardList,
	IconStack2,
	IconLifebuoy,
	IconLock,
	IconWand,
	IconList,
	IconColumns3,
	IconUsers,
	IconHome,
	IconFileAnalytics,
	IconBell,
	IconBuildingBank,
	IconBook,
	IconBrain,
	IconMapPin,
	IconIdBadge,
	IconLayoutGrid,
	IconScale,
	IconCircleCheck,
	IconUsersGroup,
	IconLayoutDashboard,
} from '@tabler/icons-svelte';

/**
 * Map of icon names to their corresponding Tabler icon components.
 * Used by the extension system to dynamically render icons from manifest metadata.
 */
export const iconMap: Record<string, any> = {
	'wallet': IconWallet,
	'cog': IconSettings,
	'chart': IconChartPie,
	'chart-pie': IconChartPie,
	'lightbulb': IconBulb,
	'dollar': IconCurrencyDollar,
	'clipboard': IconClipboardList,
	'layers': IconStack2,
	'lifesaver': IconLifebuoy,
	'lock': IconLock,
	'wand': IconWand,
	'analytics': IconChartPie,
	'list': IconList,
	'table': IconColumns3,
	'users': IconUsers,
	'home': IconHome,
	'file': IconFileAnalytics,
	'bell': IconBell,
	'building': IconBuildingBank,
	'book': IconBook,
	'brain': IconBrain,
	'map_pin': IconMapPin,
	'id_card': IconIdBadge,
	'objects': IconLayoutGrid,
	'scale': IconScale,
	'vote': IconCircleCheck,
	'users_group': IconUsersGroup,
	'dashboard': IconLayoutDashboard,
};

/**
 * Get an icon component by name, with fallback to default.
 */
export function getIcon(iconName: string, defaultIcon: any = IconStack2): any {
	return iconMap[iconName] || defaultIcon;
}
