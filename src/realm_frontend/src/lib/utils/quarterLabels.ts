export type QuarterLabelInput = {
	index?: number | bigint | null;
	is_capital?: boolean;
};

/** Human-readable quarter label (hides internal agora-quarter-N names). */
export function formatQuarterLabel(quarter: QuarterLabelInput | null | undefined): string {
	if (!quarter) return 'Quarter';
	// candid nat decodes to BigInt — normalize before comparing.
	const index = Number(quarter.index ?? 0);
	// The candid QuarterInfoRecord (status()) has no is_capital field — only the
	// JSON endpoints carry it. The capital is always catalog index 0, so treat
	// index 0 as capital when the flag is absent.
	if (quarter.is_capital || index === 0) {
		return 'Quarter 0 (Capital)';
	}
	return `Quarter ${index}`;
}
