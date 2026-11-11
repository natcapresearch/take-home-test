import {
    ChangeSetCommoditySourceRead,
    ChangeSetRead,
    ChangeSetSummary as BackendChangeSetSummary,
    DataCoverage as BackendDataCoverage,
    OrganisationRead,
    ParentChangeSet as BackendParentChangeSet,
    UnitOfAnalysisChangeSummaryBreakdown as BackendUnitOfAnalysisChangeSummaryBreakdown,
} from "../../__generated__/backend";
import {
    ChangeSet,
    ChangeSetEdge,
    ChangeSetState,
    ChangeSetSummary,
    ChangeSetsConnection,
    CommoditySource,
    CommoditySourceFilter,
    DataCoverage,
    Organisation,
    OrganisationConfig,
} from "../../__generated__/resolvers-types";
import { base64Encode } from "../service";
import {
    BackendPagination,
    indexCursorFromIndex,
    pageInfoFromBackendPagination,
    paginationToPageInfo,
    SortArgs,
} from "./paginationHelpers";

export function backendOrgConfigToGraphqlOrgConfig(
    orgUid: string,
    config: OrganisationRead["config"],
): OrganisationConfig {
    return {
        __typename: "OrganisationConfig",
        id: base64Encode("OrganisationConfig:byOrgUuid", orgUid),
        hasCommodityImpacts: config?.hasCommodityImpacts || false,
        hasCommodityDependencies: config?.hasCommodityDependencies || false,
        hasCommodityRisks: config?.hasCommodityRisks || false,
    };
}

export function backendOrganisationToGraphqlOrganisation(
    organisation: Pick<
        OrganisationRead,
        "uid" | "name" | "config" | "defaultChangeSetUid"
    >,
): Organisation {
    return {
        __typename: "Organisation",
        id: base64Encode("Organisation:byUid", organisation.uid!),
        uuid: organisation.uid!,
        config: backendOrgConfigToGraphqlOrgConfig(
            organisation.uid!,
            organisation.config,
        ),
        name: organisation.name,
        defaultChangeSetUid: organisation.defaultChangeSetUid,
    };
}

function backendChangeSetStateToGraphqlChangeSetState(
    state: string,
): ChangeSetState {
    switch (state) {
        case "draft":
            return ChangeSetState.Draft;
        case "processing":
            return ChangeSetState.Processing;
        case "done":
            return ChangeSetState.Done;
        case "published":
            return ChangeSetState.Published;
        default:
            throw new Error(
                `Unsupported ChangeSetState from backend: ${state}`,
            );
    }
}

export function graphqlChangeSetStateToBackendChangeSetUpdateState(
    state: ChangeSetState | null | undefined,
) {
    switch (state) {
        case ChangeSetState.Draft:
            return "draft";
        case ChangeSetState.Processing:
            return "processing";
        case ChangeSetState.Done:
            return "done";
        case ChangeSetState.Published:
            return "published";
    }
}

const backendDataCoverageToGraphqlDataCoverage: Record<
    BackendDataCoverage,
    DataCoverage
> = {
    FULL: DataCoverage.Full,
    PARTIAL: DataCoverage.Partial,
    NONE: DataCoverage.None,
};

function backendParentChangeSetToGraphql(
    parentChangeSet: BackendParentChangeSet | null | undefined,
) {
    if (!parentChangeSet) {
        return null;
    }
    return {
        __typename: "ParentChangeSet" as const,
        uid: String(parentChangeSet.uid),
        name: parentChangeSet.name ?? null,
    };
}

export function backendChangeSetToGraphqlChangeSet(
    changeSet: ChangeSetRead,
): ChangeSet {
    const uid = String(changeSet.uid);

    return {
        __typename: "ChangeSet",
        id: base64Encode("ChangeSet:byUid", uid),
        uid,
        orgUid: changeSet.orgUid,
        state: backendChangeSetStateToGraphqlChangeSetState(changeSet.state),
        name: changeSet.name ?? `Version ${changeSet.createdAt}`,
        description: changeSet.description,
        parentUid: changeSet.parentUid,
        parentChangeSet: backendParentChangeSetToGraphql(
            changeSet.parentChangeSet,
        ),
        isLatest: changeSet.isLatest ?? false,
        commoditySpendCoverage: changeSet.commoditySpendCoverage
            ? backendDataCoverageToGraphqlDataCoverage[
                  changeSet.commoditySpendCoverage
              ]
            : null,
        createdAt: changeSet.createdAt,
        updatedAt: changeSet.updatedAt,
        processedAt: changeSet.processedAt,
        publishedAt: changeSet.publishedAt,
        unpublishedAt: changeSet.unpublishedAt,
    };
}

export function backendChangeSetsToGraphqlChangeSetsConnection(
    changeSets: ChangeSetRead[],
    pagination: BackendPagination,
): ChangeSetsConnection {
    const edges: ChangeSetEdge[] = changeSets.map((changeSet, index) => ({
        cursor:
            (changeSet._meta?.cursor as string) ?? indexCursorFromIndex(index),
        node: backendChangeSetToGraphqlChangeSet(changeSet),
    }));

    return {
        __typename: "ChangeSetsConnection",
        edges,
        pageInfo: paginationToPageInfo(edges, pagination),
    };
}

export function backendChangeSetSummaryToGraphqlChangeSetSummary(
    summary: BackendChangeSetSummary,
): ChangeSetSummary {
    const toSummaryBreakdown = (
        breakdown?: BackendUnitOfAnalysisChangeSummaryBreakdown,
    ) => ({
        __typename: "UnitOfAnalysisChangeSummaryBreakdown" as const,
        regions: breakdown?.regions ?? [],
        commodities: breakdown?.commodities ?? [],
        suppliers: breakdown?.suppliers ?? [],
        products: breakdown?.products ?? [],
    });

    return {
        __typename: "ChangeSetSummary",
        orgUid: summary.orgUid,
        changeSetUid: summary.changeSetUid,
        state: summary.state,
        name: summary.name ?? null,
        description: summary.description ?? null,
        commoditySourceUnitOfAnalysisSummaries: toSummaryBreakdown(
            summary.unitOfAnalysisSummaries?.commodity_source,
        ),
    };
}

/**
 * Map a changeset-aware commodity source to the GraphQL CommoditySource type.
 */
export function changeSetCommoditySourceToGraphqlCommoditySource(
    source: ChangeSetCommoditySourceRead,
): CommoditySource {
    return {
        __typename: "CommoditySource",
        id: base64Encode("CommoditySource", `byEntityUid:${source.entityUid}`),
        uid: source.entityUid,
        aliveInChangeSet: source.aliveInChangeSet ?? true,
        identifier: source.identifier,
        commodityType: source.commodityType,
        commoditySubgroup: source.commoditySubgroup,
        commodityCode: source.commodityCode,
        yearPurchased: source.yearPurchased,
        sourcingCountry: source.sourcingCountry ?? "",
        sourcingRegion: source.sourcingRegion || null,
        quantityKilograms: source.quantityKilograms ?? null,
        spend: source.spend ?? null,
        supplier: source.supplier || null,
        product: source.product || null,
    };
}

export function changeSetCommoditySourcesToGraphqlConnection(
    sources: ChangeSetCommoditySourceRead[],
    pagination: BackendPagination,
) {
    const edges = sources.map((source) => ({
        cursor: base64Encode(
            "CommoditySource",
            `byEntityUid:${source.entityUid}`,
        ),
        node: changeSetCommoditySourceToGraphqlCommoditySource(source),
    }));

    return {
        __typename: "CommoditySourcesConnection" as const,
        edges,
        pageInfo: pageInfoFromBackendPagination(pagination),
    };
}

/**
 * Builds the query string for a backend listing from GraphQL sort/filter
 * arguments plus any extra parameters. Null and undefined values are omitted.
 */
export function paramsToBackendParams(
    sortArgs?: SortArgs,
    filters?: CommoditySourceFilter | null,
    extraParams?: Record<
        string,
        string | string[] | number | boolean | null | undefined
    >,
) {
    const params = new URLSearchParams();

    if (sortArgs?.sortOn) {
        params.append("sort_on", sortArgs.sortOn);
    }
    if (sortArgs?.sortOrder) {
        params.append("sort_order", sortArgs.sortOrder.toLowerCase());
    }

    if (filters) {
        if (filters.commoditySubgroup) {
            params.append("commodity_subgroup", filters.commoditySubgroup);
        }
        filters.commoditySubgroups?.forEach((subgroup) =>
            params.append("commodity_subgroups", subgroup),
        );
        filters.countries?.forEach((country) =>
            params.append("countries", country),
        );
        filters.sourcingAdministrativeLevel1Names?.forEach((region) =>
            params.append("sourcing_administrative_level_1_names", region),
        );
        filters.suppliers?.forEach((supplier) =>
            params.append("suppliers", supplier),
        );
        filters.productNames?.forEach((product) =>
            params.append("product_names", product),
        );
    }

    Object.entries(extraParams ?? {}).forEach(([key, value]) => {
        if (value === null || value === undefined) {
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item) => params.append(key, item));
        } else {
            params.append(key, String(value));
        }
    });

    return params;
}
