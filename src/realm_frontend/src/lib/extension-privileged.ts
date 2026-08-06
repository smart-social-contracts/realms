/**
 * In-process extension allowlist (privileged tier).
 *
 * When `VITE_PRIVILEGED_EXTENSIONS` is unset the guard is open (status quo).
 * When set (comma-separated extension ids), only listed extensions may mount
 * in-process; others must declare `runtime: "sandboxed"`.
 */

let loggedOpenGuard = false;

const privilegedExtensions: Set<string> | null = (() => {
	const raw = import.meta.env.VITE_PRIVILEGED_EXTENSIONS as string | undefined;
	if (!raw) return null;
	return new Set(
		raw
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean),
	);
})();

export function isPrivilegedExtension(id: string): boolean {
	if (privilegedExtensions === null) {
		if (!loggedOpenGuard) {
			loggedOpenGuard = true;
			console.info(
				'[extension-privileged] VITE_PRIVILEGED_EXTENSIONS not set; all in-process mounts allowed. Third-party installs will require runtime:"sandboxed".',
			);
		}
		return true;
	}
	return privilegedExtensions.has(id);
}
