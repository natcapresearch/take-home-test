import { useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useOrganisation } from "../../contexts/OrganisationProvider";
import { CHANGESET_PAGE_PATHS, rewriteOrgScopedPath } from "../urlHelpers";

/**
 * Redirects a bare org URL (no change set in the path) on a changeset page
 * to its changeset-scoped equivalent (`/c/:changeSetUid`), using the org's
 * `defaultChangeSetUid`.
 */
export function useChangeSetPageRedirect() {
    const { changeSetUid: changeSetUidFromUrl } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { defaultChangeSetUid } = useOrganisation();

    const normalizedPathname = location.pathname.replace(/\/$/, "");
    const isChangeSetPage = CHANGESET_PAGE_PATHS.some(
        (path) =>
            normalizedPathname.endsWith(path) ||
            normalizedPathname.includes(`${path}/`),
    );

    const shouldRedirect =
        !changeSetUidFromUrl && isChangeSetPage && Boolean(defaultChangeSetUid);

    useEffect(() => {
        if (shouldRedirect && defaultChangeSetUid) {
            const pathname = rewriteOrgScopedPath(location.pathname, {
                changeSetUid: defaultChangeSetUid,
            });
            navigate(
                { pathname, search: location.search, hash: location.hash },
                { replace: true },
            );
        }
    }, [shouldRedirect, defaultChangeSetUid, location, navigate]);
}
