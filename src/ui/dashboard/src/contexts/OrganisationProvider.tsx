import { createContext, PropsWithChildren, useContext } from "react";
import { useLocation, useParams } from "react-router-dom";
import {
    ChangeSet,
    ChangeSetByUidDocument,
    ChangeSetState,
    CommoditySourceSummary,
    DataCoverage,
    Organisation,
} from "../../../common/__generated__/client-types";
import { valueFromResult } from "../helpers/graphqlHelpers";
import useAuthenticatedQuery from "../helpers/hooks/useAuthenticatedQuery";

export type OrganisationContextType = Pick<
    Organisation,
    "config" | "name" | "defaultChangeSetUid" | "commoditySourceSummary"
> & {
    uuid: string;
};

export interface OrganisationContextValue extends OrganisationContextType {
    commoditySourcesCount?: number | null;
    /**
     * The change set (version) the page shows: the one named in the URL
     * (`/c/:changeSetUid` or `?changeSetUid=`), else the org's default.
     */
    selectedChangeSetUid?: string;
    selectedChangeSetState?: ChangeSetState;
    selectedChangeSetName?: string;
    selectedChangeSetCommoditySpendCoverage?: DataCoverage;
}

const OrganisationContext = createContext<OrganisationContextValue | undefined>(
    undefined,
);

interface OrganisationContextProps extends PropsWithChildren {
    organisation: OrganisationContextType;
}

function OrganisationProvider({
    organisation,
    children,
}: OrganisationContextProps) {
    const { search } = useLocation();
    const { changeSetUid: changeSetUidFromUrl } = useParams();
    const searchSelectedChangeSetUid =
        new URLSearchParams(search).get("changeSetUid") ?? undefined;

    const selectedChangeSetUid =
        changeSetUidFromUrl ||
        searchSelectedChangeSetUid ||
        organisation.defaultChangeSetUid ||
        undefined;

    const { data: selectedChangeSetData } = useAuthenticatedQuery(
        ChangeSetByUidDocument,
        {
            variables: {
                orgUid: organisation.uuid,
                changeSetUid: selectedChangeSetUid ?? "",
            },
            skip: !selectedChangeSetUid,
        },
    );

    const selectedChangeSet = valueFromResult<ChangeSet>(
        "ChangeSet",
        valueFromResult<Organisation>(
            "Organisation",
            selectedChangeSetData?.organisationByUuid,
        )?.changeSetByUid,
    );

    const commoditySourceSummary = valueFromResult<CommoditySourceSummary>(
        "CommoditySourceSummary",
        organisation.commoditySourceSummary,
    );

    const context: OrganisationContextValue = {
        ...organisation,
        commoditySourcesCount: commoditySourceSummary?.totalCommodities,
        selectedChangeSetUid,
        selectedChangeSetState: selectedChangeSet?.state,
        selectedChangeSetName: selectedChangeSet?.name ?? undefined,
        selectedChangeSetCommoditySpendCoverage:
            selectedChangeSet?.commoditySpendCoverage ?? undefined,
    };

    return (
        <OrganisationContext.Provider value={context}>
            {children}
        </OrganisationContext.Provider>
    );
}

export function useOrganisation() {
    const context = useContext(OrganisationContext);

    if (!context) {
        throw new Error(
            "useOrganisation is only available inside OrganisationProvider",
        );
    }

    return context;
}

// Returns the organisation context if available, or undefined when rendered
// outside an OrganisationProvider.
export function useOptionalOrganisation() {
    return useContext(OrganisationContext);
}

export default OrganisationProvider;
