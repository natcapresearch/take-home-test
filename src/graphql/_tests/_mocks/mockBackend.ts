import {
    ChangeSetRead,
    OrganisationRead,
    PermissionSetRead,
} from "../../__generated__/backend";

export const mockOrgUuid = "mock-org-uid";

export const mockOrganisationByUuid: Pick<
    OrganisationRead,
    "uid" | "name" | "config" | "defaultChangeSetUid"
> = {
    uid: mockOrgUuid,
    name: "Mock Organisation",
    config: {
        hasCommodityImpacts: true,
    },
    defaultChangeSetUid: "default-change-set",
};

export const mockChangeSet: ChangeSetRead = {
    uid: "change-set-1",
    orgUid: mockOrgUuid,
    state: "published",
    name: "Version 1",
    description: "First version",
    parentUid: null,
    parentChangeSet: null,
    isLatest: true,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-02T00:00:00Z",
    processedAt: "2026-01-01T12:00:00Z",
    publishedAt: "2026-01-02T00:00:00Z",
    unpublishedAt: null,
    commoditySpendCoverage: "FULL",
};

export const mockPermissionSet: PermissionSetRead = {
    object: "root",
    roles: ["organisation:admin"],
    scopes: ["update:change_set:publish"],
};

/**
 * A `BackendApi` stand-in whose methods are jest mocks, so a test can
 * override any one of them with `mockResolvedValue` / `mockRejectedValue`.
 */
export const mockBackend = {
    BackendApi: jest.fn().mockImplementation(() => ({
        getOrganisation: jest.fn().mockResolvedValue(mockOrganisationByUuid),
        getCurrentUser: jest
            .fn()
            .mockResolvedValue({ uid: "user-1", email: "demo@example.com" }),
        getRootPermissionSet: jest.fn().mockResolvedValue(mockPermissionSet),
        getObjectPermissionSet: jest.fn().mockResolvedValue(mockPermissionSet),
        getChangeSets: jest.fn().mockResolvedValue({
            response: [mockChangeSet],
            headers: { totalCount: 1 },
        }),
        getChangeSet: jest.fn().mockResolvedValue(mockChangeSet),
        patchChangeSet: jest.fn().mockResolvedValue(mockChangeSet),
        getChangeSetSummary: jest.fn(),
        getChangeSetCommoditySummary: jest.fn(),
        getChangeSetCommoditySources: jest.fn(),
        getAggregatedCommoditySourceRegions: jest.fn(),
    })),
};
