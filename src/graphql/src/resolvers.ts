import { Resolvers } from "../__generated__/resolvers-types";
import type { Context } from "./app";
import {
    backendChangeSetSummaryToGraphqlChangeSetSummary,
    backendChangeSetToGraphqlChangeSet,
    backendChangeSetsToGraphqlChangeSetsConnection,
    backendOrganisationToGraphqlOrganisation,
    changeSetCommoditySourcesToGraphqlConnection,
    graphqlChangeSetStateToBackendChangeSetUpdateState,
} from "./helpers/backendApiHelpers";
import {
    asResult,
    OnErrorPolicy,
    schemaErrorFromMissingField,
} from "./service";
import { settings } from "./settings";

/**
 * The change set a versioned org's commodity data answers for. A request
 * naming no change set means the org's default change set: the same rule the
 * dashboard applies to a URL that names none (OrganisationProvider). An org
 * with no change set at all yet has uploaded nothing, so this returns
 * undefined and the caller answers with nothing.
 */
function changeSetUidForCounts(
    parent: { defaultChangeSetUid?: string | null },
    requestedChangeSetUid: string | null | undefined,
): string | undefined {
    return requestedChangeSetUid || parent.defaultChangeSetUid || undefined;
}

export const resolvers: Resolvers<Context> = {
    Mutation: {
        async updateChangeSet(
            _,
            { orgUid, changeSetUid, state, name, description },
            { dataSources },
        ) {
            return asResult({
                resolver: async () => {
                    if (name !== undefined && name !== null) {
                        const trimmedName = name.trim();

                        if (!trimmedName) {
                            throw new Error(
                                "updateChangeSet name cannot be empty",
                            );
                        }

                        name = trimmedName;
                    }

                    if (description !== undefined && description !== null) {
                        description = description.trim();
                    }

                    const updated = await dataSources.backendApi.patchChangeSet(
                        orgUid,
                        changeSetUid,
                        {
                            state: graphqlChangeSetStateToBackendChangeSetUpdateState(
                                state,
                            ),
                            name,
                            description,
                        },
                    );
                    return backendChangeSetToGraphqlChangeSet(updated);
                },
            });
        },
    },
    Query: {
        async organisationByUuid(_, { uuid }, { dataSources }) {
            return asResult({
                resolver: async () => {
                    const org =
                        await dataSources.backendApi.getOrganisation(uuid);

                    return backendOrganisationToGraphqlOrganisation(org);
                },
                onError: OnErrorPolicy.Null,
            });
        },
        config() {
            return asResult({
                resolver: async () => ({
                    __typename: "ApplicationConfig" as const,
                    defaultOrgUid: settings.DEFAULT_ORG_UID ?? null,
                }),
            });
        },
        viewer(_, __, { dataSources }) {
            return asResult({
                resolver: async () => {
                    const { uid, email, nickname } =
                        await dataSources.backendApi.getCurrentUser();
                    return {
                        __typename: "User" as const,
                        id: uid,
                        email,
                        nickname,
                    };
                },
                onError: OnErrorPolicy.Null,
            });
        },
        async permissionSet(_, __, { dataSources }) {
            return asResult({
                resolver: async () => {
                    const permissionSet =
                        await dataSources.backendApi.getRootPermissionSet();
                    return {
                        ...permissionSet,
                        __typename: "PermissionSet" as const,
                    };
                },
            });
        },
    },
    Organisation: {
        async permissionSet(parent, _, { dataSources }) {
            return asResult({
                requiredFields: { orgUid: parent.uuid },
                resolver: async ({ orgUid }) => {
                    const permissionSet =
                        await dataSources.backendApi.getObjectPermissionSet(
                            "org",
                            orgUid,
                        );
                    return {
                        ...permissionSet,
                        __typename: "PermissionSet" as const,
                    };
                },
            });
        },
        async changeSets(
            parent,
            { first, after, before, sortOn, sortOrder, state },
            { dataSources },
        ) {
            return asResult({
                requiredFields: { orgUid: parent.uuid },
                resolver: async ({ orgUid }) => {
                    const response = await dataSources.backendApi.getChangeSets(
                        orgUid,
                        { first, after, before },
                        { sortOn, sortOrder },
                        state ? state.toLowerCase() : undefined,
                    );

                    return backendChangeSetsToGraphqlChangeSetsConnection(
                        response.response,
                        response.headers,
                    );
                },
            });
        },
        async changeSetByUid(parent, { uid }, { dataSources }) {
            return asResult({
                requiredFields: { orgUid: parent.uuid },
                resolver: async ({ orgUid }) => {
                    const changeSet = await dataSources.backendApi.getChangeSet(
                        orgUid,
                        uid ?? undefined,
                    );

                    return backendChangeSetToGraphqlChangeSet(changeSet);
                },
            });
        },
        async changeSetSummary(parent, { changeSetUid }, { dataSources }) {
            return asResult({
                requiredFields: { orgUid: parent.uuid },
                resolver: async ({ orgUid }) => {
                    const summary =
                        await dataSources.backendApi.getChangeSetSummary(
                            orgUid,
                            changeSetUid,
                        );

                    return backendChangeSetSummaryToGraphqlChangeSetSummary(
                        summary,
                    );
                },
            });
        },
        async commoditySources(
            parent,
            {
                first,
                after,
                before,
                sortOn,
                sortOrder,
                filter,
                changeSetUid,
                scope,
            },
            { dataSources },
        ) {
            if (!parent.uuid) {
                return schemaErrorFromMissingField("orgUuid");
            }
            if (!changeSetUid) {
                return schemaErrorFromMissingField("changeSetUid");
            }
            return asResult({
                resolver: async () => {
                    const { response: sources, headers } =
                        await dataSources.backendApi.getChangeSetCommoditySources(
                            parent.uuid!,
                            changeSetUid,
                            { first, after, before },
                            { sortOn, sortOrder },
                            filter,
                            // The backend enum is lowercase, the GraphQL one
                            // SCREAMING_CASE.
                            scope ? scope.toLowerCase() : undefined,
                        );
                    return changeSetCommoditySourcesToGraphqlConnection(
                        sources,
                        headers,
                    );
                },
            });
        },
        async commoditySourceSummary(
            parent,
            { changeSetUid: requestedChangeSetUid, scope },
            { dataSources },
        ) {
            // Answer from a change set (the org's default when none is
            // named), or an empty summary when the org has none yet.
            if (!parent.uuid) {
                return schemaErrorFromMissingField("orgUuid");
            }
            const changeSetUid = changeSetUidForCounts(
                parent,
                requestedChangeSetUid,
            );
            if (!changeSetUid) {
                return {
                    __typename: "CommoditySourceSummary" as const,
                    totalCommodities: 0,
                    commodityTypes: [],
                    commoditySubgroups: [],
                    sourcingCountries: [],
                    sourcingRegions: [],
                    supplierNames: [],
                    productNames: [],
                    totalSuppliers: 0,
                    totalLocations: 0,
                    totalSpend: 0,
                    totalQuantity: 0,
                    // With no commodities these are neither true nor false.
                    allCommoditiesHaveQuantity: null,
                    allCommoditiesHaveSpend: null,
                    missingQuantityCount: 0,
                    missingSpendCount: 0,
                    totalCommoditySources: 0,
                };
            }
            return asResult({
                resolver: async () => {
                    const summary =
                        await dataSources.backendApi.getChangeSetCommoditySummary(
                            parent.uuid!,
                            changeSetUid,
                            scope ? scope.toLowerCase() : undefined,
                        );
                    return {
                        __typename: "CommoditySourceSummary" as const,
                        ...summary,
                    };
                },
            });
        },
        async aggregatedCommoditySourceRegions(
            parent,
            {
                commoditySubgroups,
                includeGeometry,
                groupByCountry,
                changeSetUid: requestedChangeSetUid,
            },
            { dataSources },
        ) {
            return asResult({
                requiredFields: { orgUid: parent.uuid },
                resolver: async ({ orgUid }) => {
                    // Answer from a change set (the org's default when none
                    // is named), or no regions when the org has none yet.
                    const changeSetUid = changeSetUidForCounts(
                        parent,
                        requestedChangeSetUid,
                    );
                    const regions = changeSetUid
                        ? await dataSources.backendApi.getAggregatedCommoditySourceRegions(
                              orgUid,
                              changeSetUid,
                              commoditySubgroups,
                              includeGeometry ?? undefined,
                              groupByCountry ?? undefined,
                          )
                        : [];
                    return {
                        __typename:
                            "AggregatedCommoditySourceRegionsList" as const,
                        regions: regions.map((region) => ({
                            __typename:
                                "AggregatedCommoditySourceRegion" as const,
                            countryName: region.countryName,
                            sourcingAdministrativeLevel1Name:
                                region.sourcingAdministrativeLevel1Name || null,
                            totalSpend: region.totalSpend,
                            totalQuantity: region.totalQuantity,
                            geometry: region.geometry
                                ? {
                                      __typename: "Geometry" as const,
                                      type: region.geometry.type,
                                      coordinates: region.geometry.coordinates,
                                  }
                                : null,
                            commodityBreakdown: (
                                region.commodityBreakdown ?? []
                            ).map((entry) => ({
                                __typename: "CommodityBreakdownEntry" as const,
                                commoditySubgroup: entry.commoditySubgroup,
                                totalSpend: entry.totalSpend,
                                totalQuantity: entry.totalQuantity,
                            })),
                        })),
                    };
                },
            });
        },
    },
    ChangeSet: {
        async permissionSet(parent, _, { dataSources }) {
            return asResult({
                resolver: async () => {
                    const permissionSet =
                        await dataSources.backendApi.getObjectPermissionSet(
                            "change_set",
                            parent.uid,
                            parent.orgUid,
                        );
                    return {
                        ...permissionSet,
                        __typename: "PermissionSet" as const,
                    };
                },
            });
        },
    },
};
