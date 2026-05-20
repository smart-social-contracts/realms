/**
 * Tabler icon resolver — maps `ti-<name>` strings to Svelte icon components.
 * Only outline variants are used per the design spec.
 */
import {
	IconUserCircle,
	IconMail,
	IconSettings,
	IconLayoutDashboard,
	IconIdBadge,
	IconBallpen,
	IconGavel,
	IconMap2,
	IconReceipt,
	IconFileCode,
	IconUserPlus,
	IconLayersSubtract,
	IconChartBar,
	IconShieldDollar,
	IconBuildingStore,
	IconPackage,
	IconServer,
	IconActivity,
	IconTopologyStar3,
	IconDatabase,
	IconMessageChatbot,
} from '@tabler/icons-svelte';

const tablerIconMap: Record<string, any> = {
	'ti-user-circle': IconUserCircle,
	'ti-mail': IconMail,
	'ti-settings': IconSettings,
	'ti-layout-dashboard': IconLayoutDashboard,
	'ti-id-badge': IconIdBadge,
	'ti-ballpen': IconBallpen,
	'ti-gavel': IconGavel,
	'ti-map-2': IconMap2,
	'ti-receipt': IconReceipt,
	'ti-file-code': IconFileCode,
	'ti-user-plus': IconUserPlus,
	'ti-layers-subtract': IconLayersSubtract,
	'ti-chart-bar': IconChartBar,
	'ti-safe': IconShieldDollar,
	'ti-building-store': IconBuildingStore,
	'ti-package': IconPackage,
	'ti-server': IconServer,
	'ti-activity': IconActivity,
	'ti-topology-star-3': IconTopologyStar3,
	'ti-database': IconDatabase,
	'ti-message-chatbot': IconMessageChatbot,
};

/**
 * Resolve a `ti-<name>` icon string to its Tabler Svelte component.
 * Returns IconLayoutDashboard as default fallback.
 */
export function getTablerIcon(iconName: string): any {
	return tablerIconMap[iconName] ?? IconLayoutDashboard;
}
