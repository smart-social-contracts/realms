/**
 * Formats a number as USD currency string
 * @param {number} value - The value to format
 * @returns {string} Formatted USD string
 */
export function formatUSD(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Formats a number to a compact representation with appropriate suffix (K, M, B, T)
 * @param {number} value - The value to format
 * @returns {string} Formatted string with suffix
 */
export function formatCompact(value) {
    const formatter = new Intl.NumberFormat('en-US', {
        notation: 'compact',
        compactDisplay: 'short',
        maximumFractionDigits: 1
    });
    return formatter.format(value);
}

/**
 * Formats a number with specified decimal places
 * @param {number} value - The value to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number string
 */
export function formatNumber(value, decimals = 2) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}
