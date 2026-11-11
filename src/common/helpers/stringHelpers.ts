/**
 * Converts a string into a slug-friendly format by:
 * - Replacing all spaces with underscores (`_`)
 * - Converting all characters to lowercase
 *
 * @param str - The input string to slugify.
 * @returns The slugified string with underscores instead of spaces.
 */
export const slugify = (str: string) => {
    return str.replace(/\s+/g, "_").toLowerCase();
};

export const booleanStringMap: { [key: string]: string } = {
    True: "Yes",
    False: "No",
};

export const unitMap: { [key: string]: string } = {
    "m<sup>3</sup>": " m³",
    percent: "%",
    percentage: "%",
    kilograms: "kg",
    "percentage points": "% points",
    "kilograms per year": " kg/year",
    "kilograms per millimetre per hectare": " kg/mm/ha",
    "kilograms per hectare per year": " kg/ha/year",
    "metres cubed per year": " m³/year",
    "milligrams of carbon/metre squared/day": " mg C/m²/day",
};
