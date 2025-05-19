/**
 * Formats a number as USD currency string
 * @param value - The value to format
 * @returns Formatted USD string
 */
export function formatUSD(value: number): string;

/**
 * Formats a number to a compact representation with appropriate suffix (K, M, B, T)
 * @param value - The value to format
 * @returns Formatted string with suffix
 */
export function formatCompact(value: number): string;

/**
 * Formats a number with specified decimal places
 * @param value - The value to format
 * @param decimals - Number of decimal places
 * @returns Formatted number string
 */
export function formatNumber(value: number, decimals?: number): string;
