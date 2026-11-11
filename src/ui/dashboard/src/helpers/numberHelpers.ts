export function formatNumberToZeroDecimalPlaces(value: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
}

export function formatNumberToTwoDecimalPlaces(value: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(value);
}

/**
 * Formats a numeric string with locale-specific grouping separators while preserving its displayed
 * decimal precision and trailing zeros. Non-numeric strings are returned unchanged. Whole numbers
 * outside JavaScript's safe integer range are grouped directly to avoid changing their value.
 */
export function formatNumericStringWithGrouping(value: string): string {
    const [integerPart, fractionalPart] = value.split(".");

    if (
        !/^-?\d+$/.test(integerPart) ||
        (fractionalPart !== undefined && !/^\d+$/.test(fractionalPart))
    ) {
        return value;
    }

    const numericValue = Number(value);

    if (!Number.isSafeInteger(numericValue) && fractionalPart === undefined) {
        const sign = integerPart.startsWith("-") ? "-" : "";
        const digits = sign ? integerPart.slice(1) : integerPart;

        return `${sign}${digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
    }

    const fractionDigits = fractionalPart?.length ?? 0;

    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
    }).format(numericValue);
}

export function formatNumberToOneDecimalPlace(value: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 1,
    }).format(value);
}

export function formatNumberToFourDecimalPlaces(value: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 4,
    }).format(value);
}

export function formatNumberCompact(
    value: number,
    significantDigits?: number,
): string {
    return new Intl.NumberFormat(undefined, {
        notation: "compact",
        ...(significantDigits !== undefined
            ? { maximumSignificantDigits: significantDigits }
            : { maximumFractionDigits: 1 }),
    }).format(value);
}

export function calculatePercent(value: number, total: number): number {
    if (total <= 0 || value <= 0) {
        return 0;
    }

    return (value / total) * 100;
}

export function calculateSignedPercent(value: number, total: number): number {
    if (total <= 0) {
        return 0;
    }

    return (value / total) * 100;
}

export function formatPercentOneDecimal(value: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
    }).format(value);
}

// A formatted value, with a more precise one to show on hover when the
// display is clamped, e.g. "<0.1%".
export interface FormattedNumber {
    display: string;
    tooltip?: string;
}

function formatFixedDecimal(value: number, fractionDigits: number): string {
    return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
    }).format(value);
}

// To `fractionDigits` decimal places, keeping trailing zeros. A non-zero
// value that would round to zero shows as "<0.1" (">-0.1" when negative),
// with the value to `tooltipFractionDigits` decimal places on hover.
// Risk v3 shows event values to 2 decimal places (5 on hover) and financial
// percentages to 1 (2 on hover).
export function formatWithFloor(
    value: number,
    fractionDigits: number,
    tooltipFractionDigits: number,
    suffix = "",
): FormattedNumber {
    const smallest = 10 ** -fractionDigits;
    if (value !== 0 && Math.abs(value) < smallest / 2) {
        return {
            display:
                value > 0
                    ? `<${formatFixedDecimal(
                          smallest,
                          fractionDigits,
                      )}${suffix}`
                    : `>${formatFixedDecimal(
                          -smallest,
                          fractionDigits,
                      )}${suffix}`,
            tooltip: `${formatFixedDecimal(
                value,
                tooltipFractionDigits,
            )}${suffix}`,
        };
    }
    // `|| 0` turns -0 into 0, which would otherwise show as "-0.00".
    return {
        display: `${formatFixedDecimal(value || 0, fractionDigits)}${suffix}`,
    };
}

// A $ amount to 2 significant figures, abbreviated with K or M (e.g. $380K,
// $2.3M). A non-zero amount under $0.05 shows as "<$0.1" (">-$0.1" when
// negative), with the amount to 2 significant figures on hover.
export function formatAmountWithFloor(value: number): FormattedNumber {
    const amount = `$${formatNumberCompact(value, 2)}`;
    if (value !== 0 && Math.abs(value) < 0.05) {
        return {
            display: value > 0 ? "<$0.1" : ">-$0.1",
            tooltip: amount,
        };
    }
    return { display: amount };
}

export function getScaledProgressValue(
    value: number,
    maxValue: number,
): number {
    if (value <= 0 || maxValue <= 0) {
        return 0;
    }

    const PROGRESS_SCALE_EXPONENT = 0.7;
    const MIN_VISIBLE_PROGRESS = 2;

    // Progress bars use a power scale: (value / maxValue)^exponent * 100.
    // With exponent 1 this is linear. Using 0.7 lifts smaller non-zero values
    // enough to stay visible, but less aggressively than square-root (0.5)
    // or logarithmic scaling.
    const normalizedProgress = Math.min(value / maxValue, 1);
    const scaledProgress =
        Math.pow(normalizedProgress, PROGRESS_SCALE_EXPONENT) * 100;

    return Math.min(100, Math.max(MIN_VISIBLE_PROGRESS, scaledProgress));
}

const KG_PER_KILOTONNE = 1000000;

/** Converts a raw kilogram value to kilotonnes (divides by 1,000,000). */
export function convertKgToKilotonnes(valueInKg: number): number {
    return valueInKg / KG_PER_KILOTONNE;
}

/**
 * Formats a weight given in **kilotonnes** to a human-readable string.
 * Automatically scales down to tonnes for values below 1 kt.
 * Use this when the value has already been converted from kg (e.g. chart axis/tooltip values).
 */
export function formatWeightFromKilotonnes(kilotonnes: number): string {
    if (kilotonnes === 0) {
        return "0 tonnes";
    }

    if (kilotonnes < 1) {
        const tonnes = kilotonnes * 1000;

        if (tonnes < 1) {
            return `${formatNumberToTwoDecimalPlaces(tonnes)} tonnes`;
        }

        if (tonnes < 10) {
            return `${formatNumberToOneDecimalPlace(tonnes)} tonnes`;
        }

        return `${formatNumberToZeroDecimalPlaces(tonnes)} tonnes`;
    }

    if (kilotonnes < 10) {
        return `${formatNumberToOneDecimalPlace(kilotonnes)} k tonnes`;
    }

    return `${formatNumberToZeroDecimalPlaces(kilotonnes)} k tonnes`;
}

/**
 * Formats a raw **kilogram** value (e.g. directly from the API) to a human-readable weight string.
 * Converts to kilotonnes internally before formatting.
 * Use this when working with raw API data — do not use if the value has already been converted.
 */
export function formatWeightFromKg(
    quantityKilograms: number | null | undefined,
): string {
    return formatWeightFromKilotonnes(
        convertKgToKilotonnes(quantityKilograms ?? 0),
    );
}
