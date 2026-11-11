import { ApolloError } from "@apollo/client";
import {
    Alert,
    Box,
    Tab,
    TabList,
    TabPanel,
    TabPanels,
    Tabs,
    useTabState,
} from "@twilio-paste/core";
import {
    CommoditySource,
    CommoditySourceSummary,
    Organisation,
    OrganisationCommoditySourcesDocument,
} from "../../../../common/__generated__/client-types";
import { TabItem } from "../../../types";
import PageWrapper from "../../components/layout/PageWrapper";
import PageHeading from "../../components/layout/typography/PageHeading";
import LoaderAndErrorHandler from "../../components/LoaderAndErrorHandler";
import PageBreadcrumbs from "../../components/navigation/PageBreadcrumbs";
import CommoditiesStatsCards from "../../components/overview/commodities/CommoditiesStatsCards";
import CommoditiesToProductCard from "../../components/overview/commodities/CommoditiesToProductCard";
import CommodityAnalysisCard from "../../components/overview/commodities/CommodityAnalysisCard";
import GlobalSourcingMap from "../../components/overview/commodities/GlobalSourcingMapCard";
import { useOrganisation } from "../../contexts/OrganisationProvider";
import {
    nodesFromConnection,
    valueFromResult,
} from "../../helpers/graphqlHelpers";
import useAuthenticatedQuery from "../../helpers/hooks/useAuthenticatedQuery";
import { useChangeSetPageRedirect } from "../../helpers/hooks/useChangeSetPageRedirect";
import { PageId } from "../../types/uiIdentifiers";

export enum CommoditiesOverviewTabId {
    MapView = "map_view",
}

const commoditiesOverviewTabs: TabItem<CommoditiesOverviewTabId>[] = [
    {
        id: CommoditiesOverviewTabId.MapView,
        name: "Map View",
        disabled: false,
    },
];

interface OverviewContentProps {
    commoditySources: CommoditySource[];
    isLoading: boolean;
    error?: ApolloError;
    orgUid: string;
}

const InsightsContent = ({
    commoditySources,
    isLoading,
    error,
}: OverviewContentProps) => (
    <>
        <Box marginBottom="space50">
            <CommoditiesToProductCard
                commoditySources={commoditySources}
                isLoading={isLoading}
                error={error}
            />
        </Box>

        <CommodityAnalysisCard
            commoditySources={commoditySources}
            isLoading={isLoading}
            error={error}
        />
    </>
);

const MapContent = ({
    commoditySources,
    isLoading,
    error,
    orgUid,
    changeSetUid,
    commoditySubgroups,
    showInsightsTab,
}: OverviewContentProps & {
    changeSetUid?: string;
    commoditySubgroups: string[];
    showInsightsTab: boolean;
}) => (
    <>
        <Box marginBottom="space50">
            <GlobalSourcingMap
                orgUuid={orgUid}
                changeSetUid={changeSetUid}
                commoditySubgroups={commoditySubgroups}
            />
        </Box>

        {showInsightsTab && (
            <InsightsContent
                commoditySources={commoditySources}
                isLoading={isLoading}
                error={error}
                orgUid={orgUid}
            />
        )}
    </>
);

const CommoditiesOverview = () => {
    const pageName = "Commodities Overview";

    const { uuid: orgUid, selectedChangeSetUid: changeSetUid } =
        useOrganisation();
    useChangeSetPageRedirect();

    const { data, loading, error } = useAuthenticatedQuery(
        OrganisationCommoditySourcesDocument,
        {
            variables: {
                orgUuid: orgUid,
                changeSetUid: changeSetUid ?? null,
                // Grouping is done in the frontend, so every commodity source
                // is needed to group them correctly.
                first: 8000,
            },
            fetchPolicy: "no-cache",
        },
    );

    const organisation = valueFromResult<Organisation>(
        "Organisation",
        data?.organisationByUuid,
    );

    const commoditySourceSummary = valueFromResult<CommoditySourceSummary>(
        "CommoditySourceSummary",
        organisation?.commoditySourceSummary,
    );

    const commoditySources = nodesFromConnection<CommoditySource>(
        organisation?.commoditySources,
    );

    const commoditySubgroups = commoditySourceSummary?.commoditySubgroups ?? [];

    const hasCommoditiesToProductFlowChart = commoditySources.some(
        ({ commoditySubgroup, product }) =>
            Boolean(commoditySubgroup) && Boolean(product),
    );

    const hasCommodityAnalysisChart =
        (commoditySourceSummary?.totalQuantity ?? 0) > 0 ||
        (commoditySourceSummary?.totalSpend ?? 0) > 0;

    const showInsightsTab =
        hasCommoditiesToProductFlowChart || hasCommodityAnalysisChart;

    const tabState = useTabState({
        selectedId: CommoditiesOverviewTabId.MapView,
    });

    return (
        <PageWrapper isFullWidth>
            <PageBreadcrumbs items={[]} currentPage="Commodities overview" />
            <PageHeading
                hasBreadcrumbs
                tagLine="Explore your commodity data, from sourcing locations to end-products."
            >
                {pageName}
            </PageHeading>

            <LoaderAndErrorHandler
                errorCategory={PageId.CommoditiesOverview}
                isLoading={loading}
                error={error}
                hasData={
                    commoditySourceSummary !== undefined &&
                    commoditySources !== undefined
                }
            >
                {commoditySourceSummary?.allCommoditiesHaveQuantity ===
                    false && (
                    <Box marginBottom="space50">
                        <Alert variant="warning">
                            Upload quantity data to unlock quantity-based
                            insights and analysis across your commodities.
                        </Alert>
                    </Box>
                )}

                <Box marginBottom="space50">
                    <CommoditiesStatsCards
                        commoditySourceSummary={commoditySourceSummary!}
                        commoditySources={commoditySources}
                    />
                </Box>

                <Tabs state={tabState}>
                    <TabList aria-label="commodities overview tabs">
                        {commoditiesOverviewTabs.map((tab) => (
                            <Tab
                                key={tab.id}
                                id={tab.id}
                                onClick={() => tabState.select(tab.id)}
                            >
                                {tab.name}
                            </Tab>
                        ))}
                    </TabList>

                    <TabPanels>
                        <TabPanel tabId={CommoditiesOverviewTabId.MapView}>
                            <MapContent
                                commoditySources={commoditySources}
                                isLoading={loading}
                                error={error}
                                orgUid={orgUid}
                                changeSetUid={changeSetUid ?? undefined}
                                commoditySubgroups={commoditySubgroups}
                                showInsightsTab={showInsightsTab}
                            />
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </LoaderAndErrorHandler>
        </PageWrapper>
    );
};

export default CommoditiesOverview;
