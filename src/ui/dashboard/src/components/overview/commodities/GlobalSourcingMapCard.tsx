import {
    Alert,
    Box,
    Card,
    Combobox,
    DetailText,
    RadioButton,
    RadioButtonGroup,
    Separator,
} from "@twilio-paste/core";
import { Geometry } from "geojson";
import { useMemo, useState } from "react";
import {
    AggregatedCommoditySourceRegionsDocument,
    AggregatedCommoditySourceRegionsList,
} from "../../../../../common/__generated__/client-types";
import { purpleScale } from "../../../../../common/theme/colours";
import {
    arrayFromMaybe,
    valueFromResult,
} from "../../../helpers/graphqlHelpers";
import useAuthenticatedQuery from "../../../helpers/hooks/useAuthenticatedQuery";
import {
    formatNumberCompact,
    formatWeightFromKg,
} from "../../../helpers/numberHelpers";
import { PageId } from "../../../types/uiIdentifiers";
import CardHeading from "../../layout/typography/CardHeading";
import LoaderAndErrorHandler from "../../LoaderAndErrorHandler";
import { buildMappedFeatureCollection, RegionMap } from "../../maps/RegionMap";

export enum WeightingMethod {
    Quantity = "QUANTITY",
    Spend = "SPEND",
}

type CommodityBreakdownEntry = {
    commodity: string;
    quantity: number;
    spend: number;
};

type RegionProperties = {
    countryName: string;
    regionName: string;
    totalQuantity: number;
    totalSpend: number;
    commodityBreakdown: CommodityBreakdownEntry[];
};

type MetricConfig = {
    label: string;
    getRegionValue: (region: RegionProperties) => number;
    getCommodityValue: (entry: CommodityBreakdownEntry) => number;
    formatValue: (value: number) => string;
};

const allCommoditiesLabel = "All commodities";

const metricConfigs: Record<WeightingMethod, MetricConfig> = {
    [WeightingMethod.Quantity]: {
        label: "Quantity",
        getRegionValue: ({ totalQuantity }) => totalQuantity ?? 0,
        getCommodityValue: ({ quantity }) => quantity,
        formatValue: (value) => formatWeightFromKg(value),
    },
    [WeightingMethod.Spend]: {
        label: "Spend",
        getRegionValue: ({ totalSpend }) => totalSpend ?? 0,
        getCommodityValue: ({ spend }) => spend,
        formatValue: formatNumberCompact,
    },
};

interface RegionPopupProps {
    region: RegionProperties;
    metricConfig: MetricConfig;
}

const renderRegionPopup = ({ region, metricConfig }: RegionPopupProps) => {
    const sortedCommodityBreakdown = [...region.commodityBreakdown].sort(
        (a, b) =>
            metricConfig.getCommodityValue(b) -
            metricConfig.getCommodityValue(a),
    );

    const getTitle = () => {
        // Country is mandatory in the data template, but region may be missing
        // We default to country name if region name is not available
        // This ensures we don't repeat the country name twice
        if (region.regionName === region.countryName) {
            return region.countryName;
        }

        return `${region.regionName}, ${region.countryName}`;
    };

    return (
        <>
            <Box marginBottom="space40">
                <Box
                    fontWeight="fontWeightSemibold"
                    marginBottom="space40"
                    fontSize="fontSize30"
                >
                    {getTitle()}
                </Box>
                <Box display="flex" justifyContent="space-between">
                    <Box>{`Total ${metricConfig.label}`}</Box>
                    <Box>
                        {metricConfig.formatValue(
                            metricConfig.getRegionValue(region),
                        )}
                    </Box>
                </Box>
            </Box>

            <Separator
                orientation="horizontal"
                verticalSpacing="space0"
                element="SEPARATOR_INVERSE"
            />

            <Box marginTop="space40">
                {sortedCommodityBreakdown.map((entry, index) => (
                    <Box
                        key={`${entry.commodity}-${index}`}
                        marginBottom={
                            index < sortedCommodityBreakdown.length - 1
                                ? "space20"
                                : "space0"
                        }
                        display="flex"
                        justifyContent="space-between"
                    >
                        <Box>{entry.commodity}</Box>
                        <Box>
                            {metricConfig.formatValue(
                                metricConfig.getCommodityValue(entry),
                            )}
                        </Box>
                    </Box>
                ))}
            </Box>
        </>
    );
};

interface GlobalSourcingMapCardProps {
    orgUuid: string;
    // Which change set the map reads; the org's default when omitted.
    changeSetUid?: string;
    commoditySubgroups?: string[];
    initialCommoditySubgroup?: string;
    initialMetric?: WeightingMethod;
    // Just the map and legend, filling the container's height, without the
    // card, heading or Quantity/Spend toggle.
    isInline?: boolean;
}

const GlobalSourcingMapCard = ({
    orgUuid,
    changeSetUid,
    commoditySubgroups,
    initialCommoditySubgroup,
    initialMetric = WeightingMethod.Quantity,
    isInline = false,
}: GlobalSourcingMapCardProps) => {
    const normalizedCommoditySubgroups = useMemo(
        () => (Array.isArray(commoditySubgroups) ? commoditySubgroups : []),
        [commoditySubgroups],
    );

    const uniqueCommoditySubgroups = useMemo(
        () => Array.from(new Set(normalizedCommoditySubgroups.filter(Boolean))),
        [normalizedCommoditySubgroups],
    );

    const [selectedCommoditySubgroup, setSelectedCommoditySubgroup] = useState<
        string | undefined
    >(initialCommoditySubgroup);

    const [selectedMetric, setSelectedMetric] = useState(initialMetric);

    const hasCommodityDropdown = uniqueCommoditySubgroups.length > 0;

    const shouldQueryRegions =
        hasCommodityDropdown || selectedCommoditySubgroup != null;

    const {
        displayedData: aggregatedData,
        isShowingPreviousData,
        loading,
        error,
    } = useAuthenticatedQuery(AggregatedCommoditySourceRegionsDocument, {
        skip: !shouldQueryRegions,
        variables: {
            orgUuid,
            changeSetUid,
            commoditySubgroups: selectedCommoditySubgroup
                ? [selectedCommoditySubgroup]
                : undefined,
            includeGeometry: true,
            // "All commodities" shows countries only, each summing its
            // admin-1 regions.
            groupByCountry: !selectedCommoditySubgroup,
        },
    });

    const featureCollection = useMemo(() => {
        const aggregatedRegions =
            valueFromResult<AggregatedCommoditySourceRegionsList>(
                "AggregatedCommoditySourceRegionsList",
                aggregatedData?.organisationByUuid
                    ?.aggregatedCommoditySourceRegions,
            );
        const regions = arrayFromMaybe(aggregatedRegions?.regions);
        return buildMappedFeatureCollection(regions, (region) => {
            if (!region.geometry) return null;
            const regionName =
                region.sourcingAdministrativeLevel1Name || region.countryName;
            return {
                properties: {
                    countryName: region.countryName,
                    regionName,
                    totalQuantity: region.totalQuantity ?? 0,
                    totalSpend: region.totalSpend ?? 0,
                    commodityBreakdown: (region.commodityBreakdown ?? []).map(
                        (entry) => ({
                            commodity: entry.commoditySubgroup,
                            quantity: entry.totalQuantity ?? 0,
                            spend: entry.totalSpend ?? 0,
                        }),
                    ),
                },
                geometry: {
                    type: region.geometry.type,
                    coordinates: region.geometry.coordinates,
                } as Geometry,
            };
        });
    }, [aggregatedData]);

    const metricConfig = metricConfigs[selectedMetric];
    const hasFeatures = featureCollection.features.length > 0;

    const allCountriesUnknown = useMemo(() => {
        const aggregatedRegions =
            valueFromResult<AggregatedCommoditySourceRegionsList>(
                "AggregatedCommoditySourceRegionsList",
                aggregatedData?.organisationByUuid
                    ?.aggregatedCommoditySourceRegions,
            );
        const regions = arrayFromMaybe(aggregatedRegions?.regions);
        return (
            regions.length > 0 &&
            regions.every(
                (r) => r.countryName.trim().toLowerCase() === "unknown",
            )
        );
    }, [aggregatedData]);
    const isInitialMapLoad =
        shouldQueryRegions && loading && !isShowingPreviousData && !hasFeatures;

    const { minMetricValue, maxMetricValue } = useMemo(() => {
        if (!hasFeatures) {
            return { minMetricValue: 0, maxMetricValue: 0 };
        }

        return featureCollection.features.reduce(
            (range, feature) => {
                const value = metricConfig.getRegionValue(feature.properties);

                return {
                    minMetricValue: Math.min(range.minMetricValue, value),
                    maxMetricValue: Math.max(range.maxMetricValue, value),
                };
            },
            {
                minMetricValue: Number.POSITIVE_INFINITY,
                maxMetricValue: 0,
            },
        );
    }, [featureCollection.features, hasFeatures, metricConfig]);

    const metricRadioButtons = (
        <RadioButtonGroup
            name="map-metric"
            legend="Sourcing metric"
            element="RADIO_BUTTON_GROUP_VISUALLY_HIDDEN_LABEL"
            value={selectedMetric}
            onChange={(item) => setSelectedMetric(item as WeightingMethod)}
            attached
        >
            <RadioButton value={WeightingMethod.Quantity}>Quantity</RadioButton>
            <RadioButton value={WeightingMethod.Spend}>Spend</RadioButton>
        </RadioButtonGroup>
    );

    const mapContent = (
        <LoaderAndErrorHandler
            errorCategory={PageId.CommoditiesOverview}
            isLoading={isInitialMapLoad}
            error={error}
            hasData={true}
            loadedWrapperBoxProps={
                isInline
                    ? { display: "flex", flexDirection: "column", flex: "1" }
                    : undefined
            }
        >
            {allCountriesUnknown ? (
                <Alert variant="warning">
                    Upload location data to see insights about your sourcing
                    locations.
                </Alert>
            ) : (
                <RegionMap
                    featureCollection={featureCollection}
                    fillHeight={isInline}
                    layerKey={
                        isShowingPreviousData
                            ? "global-sourcing-map-loading"
                            : `${changeSetUid ?? "default"}-${
                                  selectedCommoditySubgroup ?? "all"
                              }-${selectedMetric}`
                    }
                    getFillColor={(region) => {
                        const value = metricConfig.getRegionValue(region);
                        const colorIndex =
                            maxMetricValue > 0
                                ? Math.round(
                                      (value / maxMetricValue) *
                                          (purpleScale.length - 1),
                                  )
                                : 0;
                        return purpleScale[colorIndex];
                    }}
                    renderPopupContent={(region) =>
                        renderRegionPopup({ region, metricConfig })
                    }
                    isLoading={loading}
                    legendTitle={`Sourcing ${metricConfig.label}`}
                    legend={
                        <>
                            <Box display="flex" justifyContent="space-between">
                                <DetailText>Low</DetailText>
                                <DetailText>High</DetailText>
                            </Box>
                            <Box element="MAP_LEGEND_GRADIENT" />
                            <Box display="flex" justifyContent="space-between">
                                <DetailText element="DETAIL_TEXT_NO_MARGIN">
                                    {metricConfig.formatValue(minMetricValue)}
                                </DetailText>
                                <DetailText element="DETAIL_TEXT_NO_MARGIN">
                                    {metricConfig.formatValue(maxMetricValue)}
                                </DetailText>
                            </Box>
                        </>
                    }
                />
            )}
        </LoaderAndErrorHandler>
    );

    if (isInline) {
        return mapContent;
    }

    return (
        <Card element="PADDED_CARD">
            <CardHeading
                tagLine={
                    initialCommoditySubgroup
                        ? `Countries where ${initialCommoditySubgroup} is sourced.`
                        : "Where commodities in your portfolio are sourced, based on uploaded data."
                }
                buttons={
                    <Box display="flex" columnGap="space40">
                        {hasCommodityDropdown && (
                            <Box minWidth="size30">
                                <Combobox
                                    selectedItem={
                                        selectedCommoditySubgroup ??
                                        allCommoditiesLabel
                                    }
                                    data-testid="single-select-filter-Commodity"
                                    labelText="Commodity"
                                    items={[
                                        allCommoditiesLabel,
                                        ...uniqueCommoditySubgroups,
                                    ]}
                                    onSelectedItemChange={({
                                        selectedItem,
                                    }) => {
                                        if (!selectedItem) return;

                                        setSelectedCommoditySubgroup(
                                            selectedItem === allCommoditiesLabel
                                                ? undefined
                                                : selectedItem,
                                        );
                                    }}
                                    hideVisibleLabel
                                />
                            </Box>
                        )}

                        {metricRadioButtons}
                    </Box>
                }
            >
                Global Sourcing Map
            </CardHeading>

            {mapContent}
        </Card>
    );
};

export default GlobalSourcingMapCard;
