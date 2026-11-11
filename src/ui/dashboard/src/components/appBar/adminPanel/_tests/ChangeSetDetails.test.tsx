import { render, screen, within } from "@testing-library/react";
import {
    ChangeSet,
    ChangeSetState,
    ChangeSetSummary as ChangeSetSummaryType,
} from "../../../../../../common/__generated__/client-types";
import { BasenameProvider } from "../../../../contexts/BasenameContext";
import {
    MockApolloProvider,
    MockBase,
    mockOrganisation,
    MockOrganisationProvider,
    MockRouter,
} from "../../../../helpers/testHelpers/testHelpers";
import ChangeSetDetails from "../ChangeSetDetails";

const baseChangeSet: ChangeSet = {
    __typename: "ChangeSet",
    id: "change-set-id",
    uid: "change-set-1",
    orgUid: mockOrganisation.uuid,
    permissionSet: {
        __typename: "PermissionSet",
        scopes: ["update:change_set:publish"],
    },
    state: ChangeSetState.Draft,
    isLatest: true,
    name: "Version 1",
    description: null,
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-02T00:00:00.000Z",
    processedAt: null,
    publishedAt: null,
    unpublishedAt: null,
    parentUid: null,
    parentChangeSet: null,
};

const baseChangeSetSummary: ChangeSetSummaryType = {
    __typename: "ChangeSetSummary",
    orgUid: mockOrganisation.uuid,
    changeSetUid: "change-set-1",
    state: "draft",
    name: "Version 1",
    description: null,
    commoditySourceUnitOfAnalysisSummaries: {
        __typename: "UnitOfAnalysisChangeSummaryBreakdown",
        regions: [
            {
                __typename: "UnitOfAnalysisChangeSummary",
                value: 1,
                text: "Brazil",
            },
            {
                __typename: "UnitOfAnalysisChangeSummary",
                value: 1,
                text: "Ghana",
            },
        ],
        commodities: [],
        suppliers: [
            {
                __typename: "UnitOfAnalysisChangeSummary",
                value: 1,
                text: "Acme",
            },
        ],
        products: [],
    },
};

interface RenderOptions {
    changeSet?: Partial<ChangeSet>;
    commoditiesCount?: number | null;
    totalCommoditySources?: number | null;
    missingQuantityCount?: number | null;
    missingSpendCount?: number | null;
}

function renderChangeSetDetails({
    changeSet,
    commoditiesCount = 2,
    totalCommoditySources = 4,
    missingQuantityCount = 0,
    missingSpendCount = 0,
}: RenderOptions = {}) {
    return render(
        <MockBase>
            <MockRouter>
                <BasenameProvider basename="/o/test-org">
                    <MockApolloProvider mocks={[]}>
                        <MockOrganisationProvider>
                            <ChangeSetDetails
                                accessibleChangeSetUids={
                                    new Set(["change-set-1"])
                                }
                                changeSet={{ ...baseChangeSet, ...changeSet }}
                                changeSetSummary={baseChangeSetSummary}
                                commoditiesCount={commoditiesCount}
                                totalCommoditySources={totalCommoditySources}
                                missingQuantityCount={missingQuantityCount}
                                missingSpendCount={missingSpendCount}
                                onSelectChangeSet={async () => undefined}
                            />
                        </MockOrganisationProvider>
                    </MockApolloProvider>
                </BasenameProvider>
            </MockRouter>
        </MockBase>,
    );
}

function getStatCard(label: string) {
    const labelElement = screen.getByText(label);
    const card = labelElement.parentElement;
    if (!card) {
        throw new Error(`Could not find stat card for "${label}"`);
    }
    return within(card);
}

describe("ChangeSetDetails", () => {
    it("expands Version summary by default and shows the commodity counts", () => {
        renderChangeSetDetails({ commoditiesCount: 42 });

        expect(
            screen.getByRole("button", { name: /Version summary/ }),
        ).toHaveAttribute("aria-expanded", "true");
        const card = getStatCard("Commodities uploaded");
        expect(card.getByText("42")).toBeInTheDocument();
        expect(card.getByText("2 regions")).toBeInTheDocument();
        expect(card.getByText("1 suppliers")).toBeInTheDocument();
        expect(card.getByText("0 products")).toBeInTheDocument();
    });

    it("shows 'processed' wording once a version is out of draft", () => {
        renderChangeSetDetails({ changeSet: { state: ChangeSetState.Done } });

        expect(screen.getByText("Commodities processed")).toBeInTheDocument();
    });

    it("offers Publish on a finished version and Unpublish on a published one", () => {
        const { rerender } = renderChangeSetDetails({
            changeSet: { state: ChangeSetState.Done },
        });
        expect(
            screen.getByRole("button", { name: "Publish" }),
        ).toBeInTheDocument();

        rerender(
            <MockBase>
                <MockRouter>
                    <BasenameProvider basename="/o/test-org">
                        <MockApolloProvider mocks={[]}>
                            <MockOrganisationProvider>
                                <ChangeSetDetails
                                    accessibleChangeSetUids={
                                        new Set(["change-set-1"])
                                    }
                                    changeSet={{
                                        ...baseChangeSet,
                                        state: ChangeSetState.Published,
                                        publishedAt: "2026-02-01T00:00:00.000Z",
                                    }}
                                    changeSetSummary={baseChangeSetSummary}
                                    commoditiesCount={2}
                                    totalCommoditySources={4}
                                    missingQuantityCount={0}
                                    missingSpendCount={0}
                                    onSelectChangeSet={async () => undefined}
                                />
                            </MockOrganisationProvider>
                        </MockApolloProvider>
                    </BasenameProvider>
                </MockRouter>
            </MockBase>,
        );

        expect(
            screen.getByRole("button", { name: "Unpublish" }),
        ).toBeInTheDocument();
    });

    it("hides Publish without the publish permission", () => {
        renderChangeSetDetails({
            changeSet: { state: ChangeSetState.Done, permissionSet: null },
        });

        expect(
            screen.queryByRole("button", { name: "Publish" }),
        ).not.toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Edit" }),
        ).toBeInTheDocument();
    });

    it("shows the Unpublished date only when the version has been unpublished", () => {
        renderChangeSetDetails();
        expect(screen.queryByText("Unpublished")).not.toBeInTheDocument();
    });

    it("hides the Missing information card entirely when nothing is missing", () => {
        renderChangeSetDetails();

        expect(
            screen.queryByText("Missing information"),
        ).not.toBeInTheDocument();
    });

    it("labels a field 'Incomplete' when only some rows are missing it", () => {
        // 1 of 4 commodity sources missing spend, 1 of 4 missing quantity:
        // partial, not "no data at all".
        renderChangeSetDetails({
            missingSpendCount: 1,
            missingQuantityCount: 1,
            totalCommoditySources: 4,
        });

        expect(
            screen.getByText("Commodity quantity, Commodity spend"),
        ).toBeInTheDocument();
        expect(screen.getByText("Incomplete")).toBeInTheDocument();
        expect(screen.queryByText("No data")).not.toBeInTheDocument();
    });

    it("labels a field 'No data' when every row is missing it", () => {
        // All 4 commodity sources missing spend: none have it at all.
        renderChangeSetDetails({
            missingSpendCount: 4,
            totalCommoditySources: 4,
        });

        expect(screen.getByText("Commodity spend")).toBeInTheDocument();
        expect(screen.getByText("No data")).toBeInTheDocument();
        expect(screen.queryByText("Incomplete")).not.toBeInTheDocument();
    });

    it("shows No data and Incomplete rows together when both apply", () => {
        renderChangeSetDetails({
            missingSpendCount: 4,
            missingQuantityCount: 1,
            totalCommoditySources: 4,
        });

        expect(screen.getByText("Commodity spend")).toBeInTheDocument();
        expect(screen.getByText("No data")).toBeInTheDocument();
        expect(screen.getByText("Commodity quantity")).toBeInTheDocument();
        expect(screen.getByText("Incomplete")).toBeInTheDocument();
    });
});
