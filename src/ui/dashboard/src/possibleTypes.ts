// Hand-maintained from src/graphql/resources/schema.graphql: update it when
// a union or interface there changes.
//
// Tells Apollo Client which concrete types belong to each abstract
// type (union / interface). Without this map, cache reads through
// inline fragments on abstract types rely on heuristic matching,
// which can silently serve stale data after cache.evict() calls.
const possibleTypes = {
    Node: [
        "User",
        "OrganisationConfig",
        "Organisation",
        "ChangeSet",
        "CommoditySource",
    ],
    Error: ["ResultError"],
    PermissionSetResult: ["PermissionSet", "ResultError"],
    ApplicationConfigResult: ["ApplicationConfig", "ResultError"],
    ChangeSetResult: ["ChangeSet", "ResultError"],
    ChangeSetsConnectionResult: ["ChangeSetsConnection", "ResultError"],
    ChangeSetSummaryResult: ["ChangeSetSummary", "ResultError"],
    CommoditySourcesConnectionResult: [
        "CommoditySourcesConnection",
        "ResultError",
    ],
    CommoditySourceSummaryResult: ["CommoditySourceSummary", "ResultError"],
    AggregatedCommoditySourceRegionsResult: [
        "AggregatedCommoditySourceRegionsList",
        "ResultError",
    ],
};

export default possibleTypes;
