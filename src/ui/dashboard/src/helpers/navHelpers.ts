import { useMatch } from "react-router-dom";

/**
 * Check if a given path strictly matches the current path.
 *
 * @param toPathname The pathname to compare against the current path
 * @returns Whether the current path strictly matches the given path
 */
export const usePathIsMatch = (toPathname: string): boolean => {
    const match = useMatch(toPathname);
    return Boolean(match);
};

/**
 * Check if a given path partially matches the current path.
 *
 * This allows for "sub-paths", so if currently on /site/id_101, then /site
 * will still return true.
 *
 * @param toPathname The pathname to compare against the current path
 * @returns Whether the current path partially matches the given path
 */
export const usePathIsPartialMatch = (toPathname: string): boolean => {
    const match = useMatch(`${toPathname}/*`);
    return Boolean(match);
};

/**
 * Appends or updates a single query parameter on a given path or URL string.
 *
 * Safely handles URLs that may already contain existing query parameters by using
 * the native `URL` API, ensuring proper encoding and concatenation.
 *
 * @param {string} to - The base path or URL to modify (e.g. "/organisation/upload").
 * @param {string} key - The query parameter name to add or update.
 * @param {string} value - The value to assign to the query parameter.
 * @returns {string} The resulting path (pathname + search) with the specified query parameter.
 *
 * @example
 * // Returns "/organisation/upload?reupload=true"
 * withParam("/organisation/upload", "reupload", "true");
 *
 * // Returns "/organisation/upload?step=create&reupload=true"
 * withParam("/organisation/upload?step=create", "reupload", "true");
 */
export const withParam = (to: string, key: string, value: string) => {
    const url = new URL(to, window.location.origin);
    url.searchParams.set(key, value);
    return url.pathname + url.search;
};

/** Adds `?<param>=true`, e.g. so the destination page shows a success toast. */
export const withSuccessParam = (to: string, param: string) =>
    withParam(to, param, "true");
