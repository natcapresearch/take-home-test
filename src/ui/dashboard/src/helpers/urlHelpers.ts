/**
 * Detect if a URL is based on the React Router hash-based router and replace
 * it with the equivalent URL when using the non-hash-based router (without
 * adding an entry to history).
 */
export function redirectHashRouterToBrowserRouter() {
    // Hash-based routes are always of the form: /#/PATHNAME
    if (window.location.hash.startsWith("#/")) {
        // Replace the history state with the new URL. Note that this does not
        // affect the history stack, so a user can't navigate back to the bad
        // URL
        window.history.replaceState(
            null,
            "",
            // Strip out the hash so it becomes /PATHNAME
            window.location.hash.replace(/^#/, ""),
        );
    }
}

interface OrgScopedPathUpdate {
    changeSetUid?: string | null;
    /** Override the path suffix instead of preserving the current one. */
    suffix?: string;
}

/**
 * Pages that carry the change set uid (`/c/:changeSetUid`) in their URL.
 */
export const CHANGESET_PAGE_PATHS = ["/commodities-overview"] as const;

/**
 * Rewrites the org/changeset prefix of an organisation-scoped path while
 * preserving the remaining route suffix.
 *
 * Supported prefix format: /o/:orgId[/c/:changeSetUid]
 */
export function rewriteOrgScopedPath(
    pathname: string,
    updates: OrgScopedPathUpdate,
) {
    const match = pathname.match(/^(\/o\/[^/]+)(?:\/c\/([^/]+))?/);

    if (!match) {
        return pathname;
    }

    const matchedPrefix = match[0];
    const orgPrefix = match[1];
    const currentChangeSetUid = match[2] ?? null;

    const nextChangeSetUid =
        updates.changeSetUid === undefined
            ? currentChangeSetUid
            : updates.changeSetUid;

    const nextPrefix = `${orgPrefix}${
        nextChangeSetUid ? `/c/${nextChangeSetUid}` : ""
    }`;

    const suffix =
        updates.suffix !== undefined
            ? updates.suffix
            : pathname.slice(matchedPrefix.length);

    return `${nextPrefix}${suffix}`;
}
