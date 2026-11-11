import {
    Box,
    Card,
    Column,
    DetailText,
    Grid,
    Separator,
} from "@twilio-paste/core";
import {
    CommoditySource,
    CommoditySourceSummary,
} from "../../../../../common/__generated__/client-types";
import {
    formatNumberCompact,
    formatWeightFromKg,
} from "../../../helpers/numberHelpers";
import SubCardHeading from "../../layout/typography/SubCardHeading";
import { ReactNode } from "react";
import NoDataBadge from "../../NoDataBadge";

interface OverviewStatCardProps {
    title: string;
    value: ReactNode;
    description: string;
    dataInfo?: string;
}

const OverviewStatCard = ({
    title,
    value,
    description,
    dataInfo,
}: OverviewStatCardProps) => (
    <Card element="FULL_WIDTH_CARD">
        <Box
            display="flex"
            flexDirection="column"
            justifyContent="space-between"
            height="100%"
        >
            <Box>
                <SubCardHeading margin="space0">{title}</SubCardHeading>

                <Box marginTop="space30" marginBottom="space80">
                    <DetailText>{description}</DetailText>
                </Box>

                <Box
                    fontSize="fontSize70"
                    fontWeight="fontWeightBold"
                    marginBottom={dataInfo ? "space60" : "space80"}
                >
                    {value}
                </Box>
            </Box>

            <Box>
                {dataInfo && (
                    <>
                        <Separator
                            orientation="horizontal"
                            verticalSpacing="space30"
                        />
                        <DetailText element="SMALL_DETAIL_TEXT">
                            {dataInfo}
                        </DetailText>
                    </>
                )}
            </Box>
        </Box>
    </Card>
);

const formatStat = (value: number | undefined | null) =>
    formatNumberCompact(value ?? 0);

interface CommoditiesStatsCardsProps {
    commoditySourceSummary: CommoditySourceSummary;
    commoditySources: CommoditySource[];
}

const CommoditiesStatsCards = ({
    commoditySourceSummary,
    commoditySources,
}: CommoditiesStatsCardsProps) => {
    const {
        totalCommodities,
        totalQuantity,
        totalLocations,
        totalSuppliers,
        totalSpend,
    } = commoditySourceSummary || {};

    const commoditiesWithSpend = commoditySources.filter(
        (source) => source.spend != null,
    );

    const commoditiesWithQuantity = commoditySources.filter(
        (source) => source.quantityKilograms != null,
    );

    const commoditiesStats = [
        {
            title: "Number of Commodities",
            value: formatStat(totalCommodities),
            description: "Number of commodities assessed.",
        },
        {
            title: "Sourcing Countries",
            value: formatStat(totalLocations),
            description: "Number of sourcing countries.",
        },
        {
            title: "Quantity Sourced",
            value:
                totalQuantity != null ? (
                    formatWeightFromKg(totalQuantity)
                ) : (
                    <NoDataBadge icon="info" label="Not provided" />
                ),
            description: "Total quantity across all commodities.",
            dataInfo: `Quantity data provided for ${commoditiesWithQuantity.length}/${commoditySources.length} commodity sources.`,
        },
        {
            title: "Spend",
            value:
                totalSpend != null ? (
                    formatNumberCompact(totalSpend)
                ) : (
                    <NoDataBadge icon="info" label="Not provided" />
                ),
            description: "Total spend across all commodities.",
            dataInfo: `Spend data provided for ${commoditiesWithSpend.length}/${commoditySources.length} commodity sources.`,
        },
        {
            title: "Suppliers",
            value: formatStat(totalSuppliers),
            description: "Number of suppliers linked to commodities.",
        },
    ];

    return (
        <Grid gutter="space30" marginBottom="space50" equalColumnHeights>
            {commoditiesStats.map((stat) => (
                <Column key={stat.title}>
                    <OverviewStatCard
                        title={stat.title}
                        value={stat.value}
                        description={stat.description}
                        dataInfo={stat.dataInfo}
                    />
                </Column>
            ))}
        </Grid>
    );
};

export default CommoditiesStatsCards;
