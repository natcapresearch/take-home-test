import { ApolloError } from "@apollo/client";
import { Card, RadioButton, RadioButtonGroup } from "@twilio-paste/core";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { BarChart } from "echarts/charts";
import {
    GridComponent,
    LegendComponent,
    TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useState } from "react";
import { CommoditySource } from "../../../../../common/__generated__/client-types";
import { eChartColours } from "../../../../../common/theme/colours";
import { pushIfDefined } from "../../../helpers/arrayHelpers";
import {
    convertKgToKilotonnes,
    formatNumberCompact,
    formatWeightFromKilotonnes,
} from "../../../helpers/numberHelpers";
import { ComponentId } from "../../../types/uiIdentifiers";
import CardHeading from "../../layout/typography/CardHeading";
import LoaderAndErrorHandler from "../../LoaderAndErrorHandler";

enum ChartType {
    Spend = "spend",
    Quantity = "quantity",
}

echarts.use([
    GridComponent,
    LegendComponent,
    TooltipComponent,
    BarChart,
    CanvasRenderer,
]);

const getCommodityCountryKey = (commodity: string, country: string) =>
    `${commodity}-${country}`;

interface BuildChartDataResult {
    commodityLabels: string[];
    countries: string[];
    valuesByCommodityAndCountry: Map<string, number>;
}

function buildChartData(
    data: CommoditySource[],
    chartType: ChartType,
): BuildChartDataResult {
    const commodityLabels: string[] = [];
    const countries: string[] = [];
    const valuesByCommodityAndCountry = new Map<string, number>();

    data.forEach((item) => {
        const { commoditySubgroup, sourcingCountry, spend, quantityKilograms } =
            item;

        let value: number;

        if (chartType === ChartType.Spend) {
            if (spend == null || spend < 0) return;
            value = spend;
        } else if (chartType === ChartType.Quantity) {
            if (quantityKilograms == null || quantityKilograms < 0) return;
            value = convertKgToKilotonnes(quantityKilograms);
        } else {
            return;
        }

        pushIfDefined(commodityLabels, commoditySubgroup);
        pushIfDefined(countries, sourcingCountry);

        const key = getCommodityCountryKey(commoditySubgroup, sourcingCountry);
        const existingValue = valuesByCommodityAndCountry.get(key);

        valuesByCommodityAndCountry.set(
            key,
            existingValue === undefined ? value : existingValue + value,
        );
    });

    // Order bars by commodity total, highest on the left
    const totalsByCommodity = new Map<string, number>(
        commodityLabels.map((commodityLabel) => [
            commodityLabel,
            countries.reduce(
                (sum, country) =>
                    sum +
                    (valuesByCommodityAndCountry.get(
                        getCommodityCountryKey(commodityLabel, country),
                    ) ?? 0),
                0,
            ),
        ]),
    );

    commodityLabels.sort(
        (a, b) =>
            (totalsByCommodity.get(b) ?? 0) - (totalsByCommodity.get(a) ?? 0),
    );

    return {
        commodityLabels,
        countries,
        valuesByCommodityAndCountry,
    };
}

function buildOption(
    chartData: BuildChartDataResult,
    chartType: ChartType,
    hoveredDataIndex?: number,
    hoveredCountries?: string[],
) {
    const { commodityLabels, countries, valuesByCommodityAndCountry } =
        chartData;

    const formatValue = (value: number) =>
        chartType === ChartType.Spend
            ? formatNumberCompact(value)
            : formatWeightFromKilotonnes(value);

    const series = countries.map((country, countryIndex) => {
        const countryColour =
            eChartColours[countryIndex % eChartColours.length];

        return {
            name: country,
            type: "bar",
            stack: "total",
            color: countryColour,
            itemStyle: {
                color: countryColour,
            },
            emphasis: {
                disabled: true,
            },
            data: commodityLabels.map((commodityLabel, index) => ({
                value: valuesByCommodityAndCountry.get(
                    getCommodityCountryKey(commodityLabel, country),
                ),
                itemStyle: {
                    opacity:
                        hoveredDataIndex == null || hoveredDataIndex === index
                            ? 1
                            : 0.3,
                },
            })),
        };
    });

    return {
        animation: false,
        grid: {
            left: 20,
            right: 20,
            top: 20,
            bottom: 80,
            containLabel: true,
        },
        legend: {
            bottom: 0,
            data: countries,
            textStyle: {
                rich: {
                    inactive: {
                        opacity: 0.3,
                    },
                },
            },
            formatter: (name: string) =>
                hoveredCountries == null || hoveredCountries.includes(name)
                    ? name
                    : `{inactive|${name}}`,
        },
        tooltip: {
            trigger: "axis",
            axisPointer: {
                type: "shadow",
            },
            formatter: (
                params: Array<{
                    seriesName: string;
                    value: number;
                    dataIndex: number;
                }>,
            ) => {
                if (!params.length) return "";

                const commodityName = `<strong>${
                    commodityLabels[params[0].dataIndex]
                }</strong>`;

                return [
                    commodityName,
                    ...params
                        .filter((item) => item.value > 0)
                        .map(
                            (item) =>
                                `${item.seriesName}: ${formatValue(
                                    item.value,
                                )}`,
                        ),
                ].join("<br/>");
            },
        },
        xAxis: {
            type: "category",
            data: commodityLabels,
            axisLabel: {
                rotate: 45,
            },
        },
        yAxis: {
            type: "value",
            nameGap: 40,
            axisLabel: {
                formatter: (value: number) =>
                    chartType === ChartType.Spend
                        ? formatNumberCompact(value)
                        : formatWeightFromKilotonnes(value),
            },
        },
        series,
    };
}

interface CommodityAnalysisBarChartProps {
    commoditySources: CommoditySource[];
    chartType: ChartType;
    isLoading: boolean;
    error?: ApolloError;
}

const CommodityAnalysisBarChart = ({
    commoditySources,
    chartType,
    isLoading,
    error,
}: CommodityAnalysisBarChartProps) => {
    const [hoveredDataIndex, setHoveredDataIndex] = useState<number>();
    const [hoveredCountries, setHoveredCountries] = useState<string[]>();

    const chartData = useMemo(
        () => buildChartData(commoditySources, chartType),
        [commoditySources, chartType],
    );

    const option = useMemo(
        () =>
            buildOption(
                chartData,
                chartType,
                hoveredDataIndex,
                hoveredCountries,
            ),
        [chartData, chartType, hoveredDataIndex, hoveredCountries],
    );

    const countriesByCommodity = useMemo(() => {
        const map = new Map<string, string[]>();

        chartData.commodityLabels.forEach((commodityLabel) => {
            const countries = chartData.countries.filter((country) => {
                return chartData.valuesByCommodityAndCountry.get(
                    getCommodityCountryKey(commodityLabel, country),
                );
            });

            map.set(commodityLabel, countries);
        });

        return map;
    }, [chartData]);

    const clearHover = () => {
        setHoveredDataIndex(undefined);
        setHoveredCountries(undefined);
    };

    return (
        <LoaderAndErrorHandler
            hasData={chartData.commodityLabels.length > 0}
            isLoading={isLoading}
            error={error}
            errorCategory={ComponentId.CommodityAnalysisBarChart}
            loadedWrapperBoxProps={{ height: "100%" }}
        >
            <ReactEChartsCore
                theme="natcap"
                echarts={echarts}
                option={option}
                notMerge
                style={{
                    height: "100%",
                    width: "100%",
                    aspectRatio: "2 / 1",
                }}
                onEvents={{
                    mouseover: (params: { componentType?: string }) => {
                        if (params.componentType !== "series") {
                            clearHover();
                        }
                    },
                    mouseout: () => {
                        clearHover();
                    },
                    updateAxisPointer: (params: {
                        axesInfo?: Array<{
                            axisDim?: string;
                            value?: number;
                        }>;
                    }) => {
                        const xAxisInfo = params.axesInfo?.find(
                            (axisInfo) => axisInfo.axisDim === "x",
                        );

                        if (xAxisInfo?.value == null) {
                            clearHover();
                            return;
                        }

                        setHoveredDataIndex(xAxisInfo.value);
                        setHoveredCountries(
                            countriesByCommodity.get(
                                chartData.commodityLabels[xAxisInfo.value],
                            ) ?? [],
                        );
                    },
                }}
            />
        </LoaderAndErrorHandler>
    );
};

interface CommodityAnalysisCardProps {
    commoditySources: CommoditySource[];
    isLoading: boolean;
    error?: ApolloError;
}

const CommodityAnalysisCard = ({
    commoditySources,
    isLoading,
    error,
}: CommodityAnalysisCardProps) => {
    const hasQuantityData = useMemo(
        () =>
            commoditySources.some(
                (commoditySource) =>
                    commoditySource.quantityKilograms != null &&
                    commoditySource.quantityKilograms > 0,
            ),
        [commoditySources],
    );

    const hasSpendData = useMemo(
        () =>
            commoditySources.some(
                (commoditySource) =>
                    commoditySource.spend != null && commoditySource.spend > 0,
            ),
        [commoditySources],
    );

    const hasAnyData = hasQuantityData || hasSpendData;

    const defaultChartType = useMemo(() => {
        if (hasQuantityData) return ChartType.Quantity;
        if (hasSpendData) return ChartType.Spend;

        return ChartType.Quantity;
    }, [hasQuantityData, hasSpendData]);

    const showChartTypeSelector = hasQuantityData && hasSpendData;

    const [selectedChartType, setSelectedChartType] =
        useState(defaultChartType);

    useEffect(() => {
        const quantitySelectedButUnavailable =
            selectedChartType === ChartType.Quantity && !hasQuantityData;
        const spendSelectedButUnavailable =
            selectedChartType === ChartType.Spend && !hasSpendData;

        if (quantitySelectedButUnavailable || spendSelectedButUnavailable) {
            setSelectedChartType(defaultChartType);
        }
    }, [defaultChartType, hasQuantityData, hasSpendData, selectedChartType]);

    if (!hasAnyData) {
        return null;
    }

    return (
        <Card element="PADDED_CARD">
            <CardHeading
                tagLine={
                    selectedChartType === ChartType.Spend
                        ? "Total spend by commodity, showing distribution across countries."
                        : "Total quantity by commodity, showing distribution across countries."
                }
                buttons={
                    showChartTypeSelector ? (
                        <RadioButtonGroup
                            name="chart-type"
                            legend=""
                            value={selectedChartType}
                            onChange={(item) =>
                                setSelectedChartType(item as ChartType)
                            }
                            attached
                        >
                            <RadioButton value={ChartType.Quantity}>
                                Quantity
                            </RadioButton>
                            <RadioButton value={ChartType.Spend}>
                                Spend
                            </RadioButton>
                        </RadioButtonGroup>
                    ) : undefined
                }
            >
                Commodity Analysis
            </CardHeading>

            <CommodityAnalysisBarChart
                commoditySources={commoditySources}
                chartType={selectedChartType}
                isLoading={isLoading}
                error={error}
            />
        </Card>
    );
};

export default CommodityAnalysisCard;
