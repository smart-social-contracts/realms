/** Copy text to the system clipboard.
 *
 * Tries execCommand first — works on user gesture when Permissions-Policy
 * blocks navigator.clipboard in portal iframes — then falls back to the
 * async Clipboard API.
 *
 * @param {string} text
 * @returns {Promise<boolean>}
 */
export async function copyText(text) {
	const execCopy = () => {
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.setAttribute('readonly', '');
			ta.style.position = 'fixed';
			ta.style.left = '-9999px';
			document.body.appendChild(ta);
			ta.select();
			const ok = document.execCommand('copy');
			document.body.removeChild(ta);
			return ok;
		} catch {
			return false;
		}
	};

	if (execCopy()) return true;

	if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch {
			/* Permissions-Policy or non-secure context */
		}
	}

	return false;
}
