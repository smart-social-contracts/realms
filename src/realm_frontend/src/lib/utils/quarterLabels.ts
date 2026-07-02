export type QuarterLabelInput = {
	index?: number | null;
	is_capital?: boolean;
};

/** Human-readable quarter label (hides internal agora-quarter-N names). */
export function formatQuarterLabel(quarter: QuarterLabelInput | null | undefined): string {
	if (!quarter) return 'Quarter';
	const index = quarter.index ?? 0;
	if (quarter.is_capital) {
		return 'Quarter 0 (Capital)';
	}
	return `Quarter ${index}`;
}
