import { format as dfFormat, parse } from "date-fns";
import { slugify } from "../../../../common/helpers/stringHelpers";

export const toTitleCase = (str: string): string => {
    return str.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};

export const isEmailValid = (email: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

export const deslugify = (str: string) => {
    const result = str.replace(/_/g, " ");
    return capitalise(result);
};

export const conditionalLowercase = (str: string): string => {
    const alwaysUpper = ["tnfd", "csrd", "leap", "esrs"];

    return str
        .split(" ")
        .map((word) => {
            if (alwaysUpper.includes(word.toLowerCase())) {
                return word.toUpperCase();
            }
            return word.toLowerCase();
        })
        .join(" ");
};

export const replaceDotsWithSpaces = (str: string): string => {
    return str.replace(/\./g, " ");
};

export const capitalise = (str: string): string => {
    return str.charAt(0).toUpperCase() + str.slice(1);
};

/**
 * Converts a string into a URL-friendly slug by:
 * - Replacing slashes (`/`) with hyphens (`-`), allowing for optional spaces around them
 * - Passing the result through `slugify` to replace spaces with underscores (`_`) and convert to lowercase
 */
export const slugifyForUrl = (str: string) => {
    return slugify(str.replace(/\s*\/\s*/g, "-"));
};

export function hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export const afterLast = (str: string, char: string): string => {
    const lastIndex = str.lastIndexOf(char);
    const result = lastIndex !== -1 ? str.slice(lastIndex + 1) : str;
    return result.trim();
};

/**
 * Returns the filename without the extension (everything before the last dot).
 */
export const getFilename = (str: string): string => {
    // First, get the filename with extension from the full path
    const filenameWithExt = afterLast(str, "/");
    // Then remove the extension
    const lastDot = filenameWithExt.lastIndexOf(".");
    return lastDot !== -1 ? filenameWithExt.slice(0, lastDot) : filenameWithExt;
};

export const dateFormat = "yyyy-MM-dd";
export const dateTimeFormat = `${dateFormat} h:mma`;

/**
 * Formats a change set name for display in the UI, converting embedded timestamps
 * to the shared `dateTimeFormat` display format.
 *
 * Supports two timestamp formats:
 * - ISO Z format: YYYY-MM-DDTHH:MM:SS(.fraction)Z
 * - Slash format: YYYY-MM-DD/HH:MM:SS (treated as UTC)
 *
 * If the name contains no timestamp, it is returned unchanged.
 */
export const formatChangeSetNameForViewer = (name: string): string => {
    // ISO Z format: YYYY-MM-DDTHH:MM:SS(.fraction)Z
    const isoZRegex = /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)/g;
    const isoZMatch = name.match(isoZRegex)?.[0];

    if (isoZMatch) {
        try {
            // Parse ISO Z by treating it as a UTC time string
            // Remove the 'Z' and fractional seconds, then parse as UTC
            const dateStr = isoZMatch.replace(/\.\d+Z$/, "").replace("Z", "");
            const date = parse(dateStr, "yyyy-MM-dd'T'HH:mm:ss", new Date());
            const formatted = dfFormat(date, dateTimeFormat);
            return name.replace(isoZMatch, formatted);
        } catch {
            // Fall through to return original name
        }
    }

    // Slash format: YYYY-MM-DD/HH:MM:SS (treated as UTC)
    const slashRegex = /(\d{4}-\d{2}-\d{2})\/(\d{2}:\d{2}:\d{2})/g;
    const slashMatch = name.match(slashRegex)?.[0];

    if (slashMatch) {
        try {
            // Parse slash format as UTC by converting to standard format
            const dateStr = slashMatch.replace("/", " ");
            const date = parse(dateStr, "yyyy-MM-dd HH:mm:ss", new Date());
            const formatted = dfFormat(date, dateTimeFormat);
            return name.replace(slashMatch, formatted);
        } catch {
            // Fall through to return original name
        }
    }

    return name;
};
