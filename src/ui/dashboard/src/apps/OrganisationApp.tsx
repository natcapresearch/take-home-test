import { ProductRegionalIcon } from "@twilio-paste/icons/esm/ProductRegionalIcon";
import { useParams } from "react-router-dom";
import {
    Organisation,
    OrganisationDocument,
} from "../../../common/__generated__/client-types";
import { NavItem } from "../../../common/types";
import App from "../App";
import GenericError from "../components/errors/GenericError";
import PageLoader from "../components/loaders/PageLoader";
import { BasenameProvider } from "../contexts/BasenameContext";
import OrganisationProvider, {
    useOrganisation,
} from "../contexts/OrganisationProvider";
import { valueFromResult } from "../helpers/graphqlHelpers";
import useAuthenticatedQuery from "../helpers/hooks/useAuthenticatedQuery";
import { ErrorType, PageId } from "../types/uiIdentifiers";

/**
 * The URL prefix every organisation-scoped path hangs off:
 * /o/:orgId[/c/:changeSetUid]
 */
function buildOrgBasename(orgUid: string, changeSetUid?: string) {
    const parts = [`/o/${orgUid}`];

    if (changeSetUid) {
        parts.push(`/c/${changeSetUid}`);
    }

    return parts.join("");
}

function OrganisationApp() {
    const { orgId, changeSetUid } = useParams() as {
        orgId: string;
        changeSetUid?: string;
    };

    const { displayedData, isShowingPreviousData, loading } =
        useAuthenticatedQuery(OrganisationDocument, {
            variables: {
                orgUuid: orgId,
                changeSetUid,
            },
        });

    const org = valueFromResult<Organisation>(
        "Organisation",
        displayedData?.organisationByUuid,
    );

    // The change set uid is a variable of this query, so switching version
    // refetches it. Tearing down the whole route subtree while that refetch
    // is in flight would also unmount the app bar, and with it the
    // version-selection panel, closing it. So once organisation data is
    // available to render the app chrome from (current or previous), keep it
    // mounted and only show a loading state for the page content underneath.
    // Previous data belonging to a *different* organisation must never be
    // shown, hence the uuid check.
    const isShowingPreviousOrgData =
        isShowingPreviousData && org?.uuid === orgId;

    if (loading && !isShowingPreviousOrgData) {
        return <PageLoader />;
    }

    if (!org) {
        return (
            <GenericError
                category={PageId.OrganisationApp}
                type={ErrorType.MissingOrganisation}
            />
        );
    }

    return (
        <BasenameProvider basename={buildOrgBasename(orgId, changeSetUid)}>
            <OrganisationProvider organisation={{ ...org, uuid: orgId }}>
                <OrganisationAppContent isPageContentLoading={loading} />
            </OrganisationProvider>
        </BasenameProvider>
    );
}

function OrganisationAppContent({
    isPageContentLoading,
}: {
    isPageContentLoading: boolean;
}) {
    const {
        uuid: orgUid,
        name: orgName,
        selectedChangeSetUid,
        defaultChangeSetUid,
    } = useOrganisation();

    const basename = buildOrgBasename(orgUid, selectedChangeSetUid);

    const navItems: NavItem[] = [
        {
            href: `${basename}/commodities-overview`,
            pageId: PageId.CommoditiesOverview,
            title: "Commodities overview",
            icon: <ProductRegionalIcon decorative />,
        },
    ];

    return (
        <App
            navItems={navItems}
            orgUid={orgUid}
            orgName={orgName}
            selectedChangeSetUid={selectedChangeSetUid}
            defaultChangeSetUid={defaultChangeSetUid}
            isPageContentLoading={isPageContentLoading}
        />
    );
}

export default OrganisationApp;
