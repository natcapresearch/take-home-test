import { ChangeSetRead } from "../../../__generated__/backend";
import {
    ChangeSetState,
    DataCoverage,
    SortOrder,
} from "../../../__generated__/resolvers-types";
import { base64Encode } from "../../service";
import {
    backendChangeSetToGraphqlChangeSet,
    backendOrganisationToGraphqlOrganisation,
    changeSetCommoditySourcesToGraphqlConnection,
    paramsToBackendParams,
} from "../backendApiHelpers";

const changeSet: ChangeSetRead = {
    uid: "cs-1",
    orgUid: "org-1",
    state: "done",
    name: null,
    description: "desc",
    parentUid: "cs-0",
    parentChangeSet: { uid: "cs-0", name: "Previous" },
    isLatest: false,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-02T00:00:00Z",
    processedAt: null,
    publishedAt: null,
    unpublishedAt: null,
    commoditySpendCoverage: "PARTIAL",
};

describe("backendOrganisationToGraphqlOrganisation", () => {
    it("maps the organisation and its three feature flags", () => {
        expect(
            backendOrganisationToGraphqlOrganisation({
                uid: "org-1",
                name: "Org",
                config: { hasCommodityRisks: true },
                defaultChangeSetUid: "cs-1",
            }),
        ).toEqual({
            __typename: "Organisation",
            id: base64Encode("Organisation:byUid", "org-1"),
            uuid: "org-1",
            name: "Org",
            defaultChangeSetUid: "cs-1",
            config: {
                __typename: "OrganisationConfig",
                id: base64Encode("OrganisationConfig:byOrgUuid", "org-1"),
                hasCommodityImpacts: false,
                hasCommodityDependencies: false,
                hasCommodityRisks: true,
            },
        });
    });
});

describe("backendChangeSetToGraphqlChangeSet", () => {
    it("maps state and coverage enums and names an unnamed version", () => {
        const mapped = backendChangeSetToGraphqlChangeSet(changeSet);

        expect(mapped).toMatchObject({
            __typename: "ChangeSet",
            uid: "cs-1",
            state: ChangeSetState.Done,
            name: "Version 2026-01-01T00:00:00Z",
            parentChangeSet: {
                __typename: "ParentChangeSet",
                uid: "cs-0",
                name: "Previous",
            },
            commoditySpendCoverage: DataCoverage.Partial,
        });
    });

    it("rejects an unknown state", () => {
        expect(() =>
            backendChangeSetToGraphqlChangeSet({
                ...changeSet,
                state: "archived" as ChangeSetRead["state"],
            }),
        ).toThrow("Unsupported ChangeSetState from backend: archived");
    });
});

describe("changeSetCommoditySourcesToGraphqlConnection", () => {
    it("uses the backend's header cursors for pageInfo", () => {
        const connection = changeSetCommoditySourcesToGraphqlConnection(
            [
                {
                    entityUid: "e-1",
                    orgUid: "org-1",
                    identifier: "CL-1",
                    commodityType: "Crop",
                    commoditySubgroup: "Cereals",
                    commodityCode: "1001",
                    yearPurchased: 2024,
                    sourcingCountry: null,
                    sourcingRegion: "",
                    supplier: "",
                    aliveInChangeSet: false,
                },
            ],
            { totalCount: 3, nextCursor: "next", prevCursor: undefined },
        );

        expect(connection.pageInfo).toEqual({
            hasNextPage: true,
            hasPreviousPage: false,
            startCursor: undefined,
            endCursor: "next",
            totalCount: 3,
        });
        expect(connection.edges[0]?.node).toMatchObject({
            uid: "e-1",
            aliveInChangeSet: false,
            sourcingCountry: "",
            sourcingRegion: null,
            supplier: null,
            quantityKilograms: null,
        });
    });
});

describe("paramsToBackendParams", () => {
    it("lowercases the sort order and repeats list filters", () => {
        const params = paramsToBackendParams(
            { sortOn: "spend", sortOrder: SortOrder.Desc },
            {
                commoditySubgroup: "Cereals",
                countries: ["BR", "AR"],
                productNames: [],
            },
            { change_set_uid: "cs-1", limit: "50", scope: undefined },
        );

        expect(params.toString()).toEqual(
            new URLSearchParams([
                ["sort_on", "spend"],
                ["sort_order", "desc"],
                ["commodity_subgroup", "Cereals"],
                ["countries", "BR"],
                ["countries", "AR"],
                ["change_set_uid", "cs-1"],
                ["limit", "50"],
            ]).toString(),
        );
    });

    it("repeats list-valued extra params", () => {
        const params = paramsToBackendParams(undefined, undefined, {
            commodity_subgroups: ["Cereals", "Oilseeds"],
            include_geometry: true,
        });

        expect(params.getAll("commodity_subgroups")).toEqual([
            "Cereals",
            "Oilseeds",
        ]);
        expect(params.get("include_geometry")).toEqual("true");
    });
});
