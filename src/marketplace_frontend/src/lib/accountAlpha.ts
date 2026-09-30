/** Whether My Purchases, Upload, and Developer are shown as coming soon. */

export function accountPagesAlpha(env: {
	accountAlpha?: string;
	envName?: string;
}): boolean {
	const explicit = (env.accountAlpha || '').trim().toLowerCase();
	if (explicit === 'true' || explicit === '1') return true;
	if (explicit === 'false' || explicit === '0') return false;
	const name = (env.envName || '').trim().toLowerCase();
	return name === 'staging' || name === 'demo' || name === 'test';
}
