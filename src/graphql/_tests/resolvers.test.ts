import { getBaseSettings } from "./_mocks/mockSettings";
jest.mock<typeof import("../src/settings")>("../src/settings", () => ({
    settings: getBaseSettings(),
}));

import {
    mockBackend,
    mockChangeSet,
    mockOrganisationByUuid,
    mockOrgUuid,
    mockPermissionSet,
} from "./_mocks/mockBackend";

jest.mock("../src/dataSources/backendApi", () => mockBackend);

import { ApolloServer, GraphQLResponse } from "@apollo/server";
import { InMemoryLRUCache } from "@apollo/utils.keyvaluecache";
import assert from "assert";
import { readFileSync } from "fs";
import { GraphQLError } from "graphql";
import gql from "graphql-tag";
import { Mutation, Query } from "../__generated__/resolvers-types";
import { Context } from "../src/app";
import { BackendApi } from "../src/dataSources/backendApi";
import { resolvers } from "../src/resolvers";
import { base64Encode } from "../src/service";
import { settings } from "../src/settings";

const typeDefs = gql(
    readFileSync(`src/graphql/resources/schema.graphql`, {
        encoding: "utf-8",
    }),
);

const testContext: Context = {
    dataSources: {
        backendApi: new BackendApi({ cache: new InMemoryLRUCache() }),
    },
};

/** The mocked backend, typed so a test can override any method. */
const backendApi = testContext.dataSources.backendApi as unknown as Record<
    string,
    jest.Mock
>;

const testServer = new ApolloServer<Context>({ typeDefs, resolvers });

function expectNoErrors<T>(responseBody: GraphQLResponse<T>["body"]): T {
    // Node's assert narrows the type of `body`; Jest's expect does not.
    assert(responseBody.kind === "single");
    expect(responseBody.singleResult.errors).toBeUndefined();
    return responseBody.singleResult.data as T;
}

async function runQuery(
    query: ReturnType<typeof gql>,
    variables: Record<string, unknown> = {},
): Promise<Query> {
    const response = await testServer.executeOperation<Query>(
        { query, variables },
        { contextValue: testContext },
    );
    return expectNoErrors(response.body);
}

const orgWithoutChangeSet = {
    ...mockOrganisationByUuid,
    defaultChangeSetUid: null,
};

describe("Query", () => {
    it("returns the organisation for a uuid", async () => {
        const data = await runQuery(
            gql`
                query Query($uuid: String!) {
                    organisationByUuid(uuid: $uuid) {
                        id
                        uuid
                        name
                        defaultChangeSetUid
                        config {
                            hasCommodityImpacts
                            hasCommodityRisks
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid },
        );

        expect(data.organisationByUuid).toEqual({
            id: base64Encode("Organisation:byUid", mockOrgUuid),
            uuid: mockOrgUuid,
            name: "Mock Organisation",
            defaultChangeSetUid: "default-change-set",
            config: { hasCommodityImpacts: true, hasCommodityRisks: false },
        });
    });

    it("returns null when the organisation is not found", async () => {
        backendApi.getOrganisation.mockRejectedValueOnce(
            new GraphQLError("Not found", {
                extensions: { response: { status: 404 } },
            }),
        );

        const data = await runQuery(gql`
            query Query {
                organisationByUuid(uuid: "missing") {
                    id
                }
            }
        `);

        expect(data.organisationByUuid).toBeNull();
    });

    it("answers the viewer from the backend's current user", async () => {
        const data = await runQuery(gql`
            query Query {
                viewer {
                    id
                    email
                }
            }
        `);

        expect(data.viewer).toEqual({
            id: "user-1",
            email: "demo@example.com",
        });
    });

    it("exposes the configured default organisation", async () => {
        settings.DEFAULT_ORG_UID = "configured-org";
        try {
            const data = await runQuery(gql`
                query Query {
                    config {
                        ... on ApplicationConfig {
                            defaultOrgUid
                        }
                    }
                }
            `);

            expect(data.config).toEqual({ defaultOrgUid: "configured-org" });
        } finally {
            settings.DEFAULT_ORG_UID = undefined;
        }
    });

    it("returns the root permission set", async () => {
        const data = await runQuery(gql`
            query Query {
                permissionSet {
                    __typename
                    ... on PermissionSet {
                        scopes
                    }
                }
            }
        `);

        expect(data.permissionSet).toEqual({
            __typename: "PermissionSet",
            scopes: mockPermissionSet.scopes,
        });
    });
});

describe("Organisation", () => {
    it("returns changeSetSummary for a given change set", async () => {
        backendApi.getChangeSetSummary.mockResolvedValueOnce({
            orgUid: mockOrgUuid,
            changeSetUid: "change-set-123",
            state: "draft",
            name: "Draft Set",
            description: "Summary text",
            unitOfAnalysisSummaries: {
                commodity_source: {
                    regions: [{ value: 2, text: "regions" }],
                    commodities: [{ value: 1, text: "commodity" }],
                    suppliers: [],
                    products: [],
                },
            },
        });

        const data = await runQuery(
            gql`
                query Query($uuid: String!, $changeSetUid: String!) {
                    organisationByUuid(uuid: $uuid) {
                        changeSetSummary(changeSetUid: $changeSetUid) {
                            __typename
                            ... on ChangeSetSummary {
                                changeSetUid
                                state
                                commoditySourceUnitOfAnalysisSummaries {
                                    regions {
                                        value
                                        text
                                    }
                                    commodities {
                                        text
                                    }
                                    suppliers {
                                        text
                                    }
                                }
                            }
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid, changeSetUid: "change-set-123" },
        );

        expect(data.organisationByUuid?.changeSetSummary).toEqual({
            __typename: "ChangeSetSummary",
            changeSetUid: "change-set-123",
            state: "draft",
            commoditySourceUnitOfAnalysisSummaries: {
                regions: [{ value: 2, text: "regions" }],
                commodities: [{ text: "commodity" }],
                suppliers: [],
            },
        });
        expect(backendApi.getChangeSetSummary).toHaveBeenCalledWith(
            mockOrgUuid,
            "change-set-123",
        );
    });

    it("returns ResultError when changeSetSummary is not found", async () => {
        backendApi.getChangeSetSummary.mockRejectedValueOnce(
            new GraphQLError("Change set not found", {
                extensions: {
                    response: {
                        status: 404,
                        body: { detail: "Change set not found" },
                    },
                },
            }),
        );

        const data = await runQuery(
            gql`
                query Query($uuid: String!) {
                    organisationByUuid(uuid: $uuid) {
                        changeSetSummary(changeSetUid: "missing") {
                            __typename
                            ... on ResultError {
                                message
                                code
                            }
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid },
        );

        expect(data.organisationByUuid?.changeSetSummary).toEqual({
            __typename: "ResultError",
            code: "NOT_FOUND",
            message: "Change set not found: Change set not found",
        });
    });

    it("lists change sets with their permission set", async () => {
        const data = await runQuery(
            gql`
                query Query($uuid: String!) {
                    organisationByUuid(uuid: $uuid) {
                        changeSets(sortOrder: DESC, sortOn: "created_at") {
                            ... on ChangeSetsConnection {
                                edges {
                                    node {
                                        uid
                                        state
                                        name
                                        commoditySpendCoverage
                                        permissionSet {
                                            ... on PermissionSet {
                                                scopes
                                            }
                                        }
                                    }
                                }
                                pageInfo {
                                    totalCount
                                }
                            }
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid },
        );

        expect(data.organisationByUuid?.changeSets).toEqual({
            edges: [
                {
                    node: {
                        uid: "change-set-1",
                        state: "PUBLISHED",
                        name: "Version 1",
                        commoditySpendCoverage: "FULL",
                        permissionSet: { scopes: mockPermissionSet.scopes },
                    },
                },
            ],
            pageInfo: { totalCount: 1 },
        });
        expect(backendApi.getChangeSets).toHaveBeenCalledWith(
            mockOrgUuid,
            { first: undefined, after: undefined, before: undefined },
            { sortOn: "created_at", sortOrder: "DESC" },
            undefined,
        );
        expect(backendApi.getObjectPermissionSet).toHaveBeenCalledWith(
            "change_set",
            "change-set-1",
            mockOrgUuid,
        );
    });

    describe("commoditySourceSummary without a changeSetUid", () => {
        const query = gql`
            query Query($uuid: String!, $changeSetUid: String) {
                organisationByUuid(uuid: $uuid) {
                    commoditySourceSummary(changeSetUid: $changeSetUid) {
                        __typename
                        ... on CommoditySourceSummary {
                            totalCommodities
                        }
                    }
                }
            }
        `;

        it("answers zero when the org has no version yet", async () => {
            backendApi.getOrganisation.mockResolvedValueOnce({
                ...orgWithoutChangeSet,
                uid: mockOrgUuid,
            });

            const data = await runQuery(query, {
                uuid: mockOrgUuid,
                changeSetUid: null,
            });

            expect(data.organisationByUuid?.commoditySourceSummary).toEqual({
                __typename: "CommoditySourceSummary",
                totalCommodities: 0,
            });
            expect(
                backendApi.getChangeSetCommoditySummary,
            ).not.toHaveBeenCalled();
        });

        it("answers for the org's default version", async () => {
            backendApi.getChangeSetCommoditySummary.mockResolvedValueOnce({
                totalCommodities: 7,
            });

            const data = await runQuery(query, {
                uuid: mockOrgUuid,
                changeSetUid: null,
            });

            expect(data.organisationByUuid?.commoditySourceSummary).toEqual({
                __typename: "CommoditySourceSummary",
                totalCommodities: 7,
            });
            expect(
                backendApi.getChangeSetCommoditySummary,
            ).toHaveBeenCalledWith(
                mockOrgUuid,
                "default-change-set",
                undefined,
            );
        });
    });

    // The commodities overview map reads the change-set-aware regions: the
    // named version, else the org's default, else no regions.
    describe("aggregatedCommoditySourceRegions", () => {
        const query = gql`
            query Query($uuid: String!, $changeSetUid: String) {
                organisationByUuid(uuid: $uuid) {
                    aggregatedCommoditySourceRegions(
                        changeSetUid: $changeSetUid
                        includeGeometry: true
                        groupByCountry: true
                    ) {
                        __typename
                        ... on AggregatedCommoditySourceRegionsList {
                            regions {
                                countryName
                                totalSpend
                                geometry {
                                    type
                                }
                                commodityBreakdown {
                                    commoditySubgroup
                                }
                            }
                        }
                    }
                }
            }
        `;

        it.each([
            ["the named version", "named-change-set", "named-change-set"],
            ["the org's default version", null, "default-change-set"],
        ])(
            "answers for %s",
            async (_label, changeSetUid, expectedChangeSetUid) => {
                backendApi.getAggregatedCommoditySourceRegions.mockResolvedValueOnce(
                    [
                        {
                            countryName: "Brazil",
                            sourcingAdministrativeLevel1Name: null,
                            totalSpend: 10,
                            totalQuantity: 1,
                            geometry: { type: "Polygon", coordinates: [] },
                            commodityBreakdown: [
                                {
                                    commoditySubgroup: "Soy",
                                    totalSpend: 10,
                                    totalQuantity: 1,
                                },
                            ],
                        },
                    ],
                );

                const data = await runQuery(query, {
                    uuid: mockOrgUuid,
                    changeSetUid,
                });

                expect(
                    data.organisationByUuid?.aggregatedCommoditySourceRegions,
                ).toEqual({
                    __typename: "AggregatedCommoditySourceRegionsList",
                    regions: [
                        {
                            countryName: "Brazil",
                            totalSpend: 10,
                            geometry: { type: "Polygon" },
                            commodityBreakdown: [{ commoditySubgroup: "Soy" }],
                        },
                    ],
                });
                expect(
                    backendApi.getAggregatedCommoditySourceRegions,
                ).toHaveBeenCalledWith(
                    mockOrgUuid,
                    expectedChangeSetUid,
                    undefined,
                    true,
                    true,
                );
            },
        );

        it("answers no regions when the org has no version yet", async () => {
            backendApi.getOrganisation.mockResolvedValueOnce({
                ...orgWithoutChangeSet,
                uid: mockOrgUuid,
            });

            const data = await runQuery(query, {
                uuid: mockOrgUuid,
                changeSetUid: null,
            });

            expect(
                data.organisationByUuid?.aggregatedCommoditySourceRegions,
            ).toEqual({
                __typename: "AggregatedCommoditySourceRegionsList",
                regions: [],
            });
            expect(
                backendApi.getAggregatedCommoditySourceRegions,
            ).not.toHaveBeenCalled();
        });
    });

    // Regression: pageInfo cursors must be the backend's header cursors, not
    // the edges' Relay node ids: the UI paginates on pageInfo.endCursor and
    // the backend cannot decode a node id as a cursor.
    it("puts the backend's header cursors in commoditySources pageInfo, not edge node ids", async () => {
        backendApi.getChangeSetCommoditySources.mockResolvedValueOnce({
            response: [
                {
                    entityUid: "cl-entity-1",
                    orgUid: mockOrgUuid,
                    identifier: "CL-1",
                    commodityType: "Crop",
                    commoditySubgroup: "Cereals",
                    commodityCode: "1001",
                    yearPurchased: 2024,
                    aliveInChangeSet: true,
                },
            ],
            headers: {
                totalCount: 75,
                nextCursor: "BACKEND_NEXT_CURSOR",
                prevCursor: "BACKEND_PREV_CURSOR",
            },
        });

        const data = await runQuery(
            gql`
                query Query($uuid: String!, $changeSetUid: String) {
                    organisationByUuid(uuid: $uuid) {
                        commoditySources(
                            first: 1
                            changeSetUid: $changeSetUid
                            filter: { commoditySubgroups: ["Cereals"] }
                        ) {
                            __typename
                            ... on CommoditySourcesConnection {
                                edges {
                                    cursor
                                    node {
                                        uid
                                        sourcingCountry
                                    }
                                }
                                pageInfo {
                                    hasNextPage
                                    hasPreviousPage
                                    startCursor
                                    endCursor
                                    totalCount
                                }
                            }
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid, changeSetUid: "change-set-123" },
        );

        const connection = data.organisationByUuid?.commoditySources;
        assert(connection?.__typename === "CommoditySourcesConnection");
        expect(connection.pageInfo).toEqual({
            hasNextPage: true,
            hasPreviousPage: true,
            startCursor: "BACKEND_PREV_CURSOR",
            endCursor: "BACKEND_NEXT_CURSOR",
            totalCount: 75,
        });
        expect(connection.edges).toEqual([
            {
                cursor: base64Encode(
                    "CommoditySource",
                    "byEntityUid:cl-entity-1",
                ),
                node: { uid: "cl-entity-1", sourcingCountry: "" },
            },
        ]);
        expect(backendApi.getChangeSetCommoditySources).toHaveBeenCalledWith(
            mockOrgUuid,
            "change-set-123",
            { first: 1, after: undefined, before: undefined },
            { sortOn: undefined, sortOrder: undefined },
            { commoditySubgroups: ["Cereals"] },
            undefined,
        );
    });

    it("returns ResultError for commoditySources without a changeSetUid", async () => {
        const data = await runQuery(
            gql`
                query Query($uuid: String!) {
                    organisationByUuid(uuid: $uuid) {
                        commoditySources(first: 1) {
                            __typename
                            ... on ResultError {
                                message
                                code
                            }
                        }
                    }
                }
            `,
            { uuid: mockOrgUuid },
        );

        expect(data.organisationByUuid?.commoditySources).toEqual({
            __typename: "ResultError",
            code: "NOT_FOUND",
            message: "Missing required field: changeSetUid",
        });
        expect(backendApi.getChangeSetCommoditySources).not.toHaveBeenCalled();
    });
});

describe("Mutation", () => {
    it("trims the name and description before patching the change set", async () => {
        backendApi.patchChangeSet.mockResolvedValueOnce({
            ...mockChangeSet,
            name: "Renamed",
            description: "Trimmed",
        });

        const response = await testServer.executeOperation<Mutation>(
            {
                query: gql`
                    mutation UpdateChangeSet(
                        $orgUid: String!
                        $changeSetUid: String!
                    ) {
                        updateChangeSet(
                            orgUid: $orgUid
                            changeSetUid: $changeSetUid
                            name: "  Renamed  "
                            description: " Trimmed "
                            state: PUBLISHED
                        ) {
                            ... on ChangeSet {
                                uid
                                name
                                description
                                state
                            }
                        }
                    }
                `,
                variables: {
                    orgUid: mockOrgUuid,
                    changeSetUid: "change-set-1",
                },
            },
            { contextValue: testContext },
        );

        const data = expectNoErrors(response.body);
        expect(data.updateChangeSet).toEqual({
            uid: "change-set-1",
            name: "Renamed",
            description: "Trimmed",
            state: "PUBLISHED",
        });
        expect(backendApi.patchChangeSet).toHaveBeenCalledWith(
            mockOrgUuid,
            "change-set-1",
            { state: "published", name: "Renamed", description: "Trimmed" },
        );
    });

    it("rejects an empty name", async () => {
        const response = await testServer.executeOperation<Mutation>(
            {
                query: gql`
                    mutation UpdateChangeSet($orgUid: String!) {
                        updateChangeSet(
                            orgUid: $orgUid
                            changeSetUid: "change-set-1"
                            name: "   "
                        ) {
                            ... on ResultError {
                                message
                            }
                        }
                    }
                `,
                variables: { orgUid: mockOrgUuid },
            },
            { contextValue: testContext },
        );

        const data = expectNoErrors(response.body);
        expect(data.updateChangeSet).toEqual({
            message: "updateChangeSet name cannot be empty",
        });
        expect(backendApi.patchChangeSet).not.toHaveBeenCalled();
    });
});
