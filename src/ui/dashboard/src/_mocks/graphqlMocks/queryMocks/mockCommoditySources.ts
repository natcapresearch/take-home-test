import type { FetchResult } from "@apollo/client";
import { MockedResponse } from "@apollo/client/testing";
import {
    CommoditySource,
    OrganisationCommoditySourcesDocument,
    OrganisationCommoditySourcesQuery,
    OrganisationCommoditySourcesQueryVariables,
    SortOrder,
} from "../../../../../common/__generated__/client-types";
import { mockOrganisation } from "../../../helpers/testHelpers/testHelpers";

export type MockCommoditySourcesResponse = MockedResponse<
    OrganisationCommoditySourcesQuery,
    OrganisationCommoditySourcesQueryVariables
>;

// Default filter state as initialised by CommoditiesListTableProvider. Every
// MultiSelectFilter mount effect calls applyFilters() once, but
// useApplyFilters bails out via shallowEqual when nothing actually changed,
// so this is the only filter shape ever queried before the user picks
// something: there's no separate "initial vs settled" fetch to mock.
const settledFilter = {
    commoditySubgroups: [],
    countries: [],
    sourcingAdministrativeLevel1Names: [],
    suppliers: [],
    productNames: [],
    yearsPurchased: [],
};

// Base variables for summary view (nestedSortState default).
const summaryVariables: OrganisationCommoditySourcesQueryVariables = {
    orgUuid: mockOrganisation.uuid,
    first: 8000,
    sortOrder: SortOrder.Asc,
    sortOn: "sourcing_country",
    filter: settledFilter,
    changeSetUid: null,
};

const detailedVariables: OrganisationCommoditySourcesQueryVariables = {
    orgUuid: mockOrganisation.uuid,
    first: 8000,
    sortOrder: SortOrder.Asc,
    sortOn: "commodity_subgroup", // detailedSortState default
    filter: settledFilter,
    changeSetUid: null,
};

// ---------------------------------------------------------------------------
// Shared node data
// ---------------------------------------------------------------------------

const coffeeNodeBrazil = {
    __typename: "CommoditySource" as const,
    id: "id-1",
    uid: "uid-1",
    identifier: "BRA-COFFEE-1",
    commodityCode: "COFFEE_CODE",
    commodityType: "Coffee",
    commoditySubgroup: "Coffee",
    yearPurchased: 2023,
    sourcingCountry: "Brazil",
    sourcingRegion: "São Paulo",
    quantityKilograms: 1_000_000,
    spend: 5000,
    supplier: "Supplier A",
    product: "Espresso Blend",
} satisfies CommoditySource;

const coffeeNodeColombia = {
    __typename: "CommoditySource" as const,
    id: "id-2",
    uid: "uid-2",
    identifier: "COL-COFFEE-1",
    commodityCode: "COFFEE_CODE",
    commodityType: "Coffee",
    commoditySubgroup: "Coffee",
    yearPurchased: 2022,
    sourcingCountry: "Colombia",
    sourcingRegion: "Huila",
    quantityKilograms: 500_000,
    spend: 3000,
    supplier: "Supplier B",
    product: "Filter Blend",
} satisfies CommoditySource;

const cocoaNode = {
    __typename: "CommoditySource" as const,
    id: "id-3",
    uid: "uid-3",
    identifier: "GHA-COCOA-1",
    commodityCode: "COCOA_CODE",
    commodityType: "Cocoa",
    commoditySubgroup: "Cocoa",
    yearPurchased: 2023,
    sourcingCountry: "Ghana",
    sourcingRegion: null,
    quantityKilograms: 200_000,
    spend: 2000,
    supplier: "Supplier C",
    product: "Dark Blend",
} satisfies CommoditySource;

/** The nodes of the "with data" mocks, for the `commoditySources` prop. */
export const mockCommoditySourceNodes: CommoditySource[] = [
    coffeeNodeBrazil,
    coffeeNodeColombia,
    cocoaNode,
];

const makeConnection = (nodes: CommoditySource[]) => ({
    __typename: "CommoditySourcesConnection" as const,
    edges: nodes.map((node, i) => ({
        __typename: "CommoditySourceEdge" as const,
        cursor: `cursor-${i}`,
        node,
    })),
    pageInfo: {
        __typename: "PageInfo" as const,
        endCursor: null,
        hasNextPage: false,
        hasPreviousPage: false,
        startCursor: null,
        totalCount: nodes.length,
    },
});

const makeResult = (
    nodes: CommoditySource[],
): FetchResult<OrganisationCommoditySourcesQuery> => ({
    data: {
        organisationByUuid: {
            __typename: "Organisation" as const,
            id: "org-id",
            commoditySourceSummary: {
                __typename: "CommoditySourceSummary" as const,
                totalCommodities: nodes.length,
                totalSuppliers: nodes.length,
                totalLocations: nodes.length,
                totalSpend: nodes.reduce((s, n) => s + (n.spend ?? 0), 0),
                totalQuantity: nodes.reduce(
                    (s, n) => s + (n.quantityKilograms ?? 0),
                    0,
                ),
                commoditySubgroups: Array.from(
                    new Set(
                        nodes
                            .map((n) => n.commoditySubgroup)
                            .filter((s): s is string => Boolean(s)),
                    ),
                ),
            },
            commoditySources: makeConnection(nodes),
        },
    },
});

// ---------------------------------------------------------------------------
// Exported mocks
// ---------------------------------------------------------------------------

export const mockCommoditySourcesEmpty: MockCommoditySourcesResponse = {
    request: {
        query: OrganisationCommoditySourcesDocument,
        variables: summaryVariables,
    },
    result: makeResult([]),
};

export const mockCommoditySourcesSummaryWithData: MockCommoditySourcesResponse =
    {
        request: {
            query: OrganisationCommoditySourcesDocument,
            variables: summaryVariables,
        },
        result: makeResult([coffeeNodeBrazil, coffeeNodeColombia, cocoaNode]),
    };

export const mockCommoditySourcesDetailedWithData: MockCommoditySourcesResponse =
    {
        request: {
            query: OrganisationCommoditySourcesDocument,
            variables: detailedVariables,
        },
        result: makeResult([coffeeNodeBrazil, coffeeNodeColombia, cocoaNode]),
    };
