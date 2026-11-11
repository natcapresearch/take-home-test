import { Card, RadioButton, RadioButtonGroup } from "@twilio-paste/core";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { SankeyChart } from "echarts/charts";
import {
    GraphicComponent,
    TitleComponent,
    TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef, useState } from "react";

import { ApolloError } from "@apollo/client";
import { CommoditySource } from "../../../../../common/__generated__/client-types";
import { natcapTheme } from "../../../../../common/theme/base";
import { dashboardChartColours } from "../../../../../common/theme/colours";
import {
    calculatePercent,
    formatNumberCompact,
    formatNumberToZeroDecimalPlaces,
    formatWeightFromKg,
} from "../../../helpers/numberHelpers";
import { ComponentId } from "../../../types/uiIdentifiers";
import CardHeading from "../../layout/typography/CardHeading";
import LoaderAndErrorHandler from "../../LoaderAndErrorHandler";

echarts.use([
    SankeyChart,
    TooltipComponent,
    GraphicComponent,
    TitleComponent,
    CanvasRenderer,
]);

interface SankeyNode {
    name: string;
    value: number;
}

interface SankeyLink {
    source: string;
    target: string;
    value: number;
    percentage: number;
}

enum FlowWeightingMethod {
    Quantity = "quantity",
    Spend = "spend",
}

interface SankeyData {
    nodes: SankeyNode[];
    links: SankeyLink[];
    weightingMethod: FlowWeightingMethod;
}

function getFlowWeightingMethod(
    hasAnyQuantityData: boolean,
    hasAnySpendData: boolean,
): FlowWeightingMethod {
    if (hasAnyQuantityData) {
        return FlowWeightingMethod.Quantity;
    }

    if (hasAnySpendData) {
        return FlowWeightingMethod.Spend;
    }

    return FlowWeightingMethod.Quantity;
}

function getFlowValue(
    item: CommoditySource,
    weightingMethod: FlowWeightingMethod,
): number {
    if (weightingMethod === FlowWeightingMethod.Spend) {
        return item.spend ?? 0;
    }

    if (weightingMethod === FlowWeightingMethod.Quantity) {
        return item.quantityKilograms ?? 0;
    }

    return 0;
}

function getValueLabel(
    value: number,
    weightingMethod: FlowWeightingMethod,
): string {
    if (weightingMethod === FlowWeightingMethod.Spend) {
        return formatNumberCompact(value);
    }

    return formatWeightFromKg(value);
}

function getFlowChartTagLine(weightingMethod: FlowWeightingMethod): string {
    if (weightingMethod === FlowWeightingMethod.Quantity) {
        return "How analysed commodities flow into associated products, showing quantity contributions.";
    }

    if (weightingMethod === FlowWeightingMethod.Spend) {
        return "How analysed commodities flow into associated products, showing spend contributions.";
    }

    return "How analysed commodities flow into associated products, showing quantity contributions.";
}

const COMMODITY_PREFIX = "commodity::";
const PRODUCT_PREFIX = "product::";

function stripNodePrefix(name: string): string {
    if (name.startsWith(COMMODITY_PREFIX)) {
        return name.slice(COMMODITY_PREFIX.length);
    }
    if (name.startsWith(PRODUCT_PREFIX)) {
        return name.slice(PRODUCT_PREFIX.length);
    }
    return name;
}

function toSankeyData(
    commoditySources: CommoditySource[],
    selectedWeightingMethod: FlowWeightingMethod,
): SankeyData {
    const nodeTotals = new Map<string, number>();
    const linkTotals = new Map<
        string,
        { source: string; target: string; value: number }
    >();

    const commodityProductRows = commoditySources.filter(
        (item) => item.commoditySubgroup && item.product,
    );

    commodityProductRows
        .filter((item) => {
            if (selectedWeightingMethod === FlowWeightingMethod.Quantity) {
                return (
                    item.quantityKilograms != null && item.quantityKilograms > 0
                );
            }

            if (selectedWeightingMethod === FlowWeightingMethod.Spend) {
                return item.spend != null && item.spend > 0;
            }

            return false;
        })
        .forEach((item) => {
            const source = `${COMMODITY_PREFIX}${item.commoditySubgroup!}`;
            const target = `${PRODUCT_PREFIX}${item.product!}`;
            const value = getFlowValue(item, selectedWeightingMethod);
            const linkKey = `${source}---${target}`;

            nodeTotals.set(source, (nodeTotals.get(source) ?? 0) + value);
            nodeTotals.set(target, (nodeTotals.get(target) ?? 0) + value);

            const existingLink = linkTotals.get(linkKey);

            if (existingLink) {
                existingLink.value += value;
            } else {
                linkTotals.set(linkKey, { source, target, value });
            }
        });

    const rawLinks = Array.from(linkTotals.values());

    const totalLinkValue = rawLinks.reduce((sum, link) => sum + link.value, 0);

    const links: SankeyLink[] = rawLinks.map((link) => ({
        ...link,
        percentage:
            totalLinkValue > 0
                ? calculatePercent(link.value, totalLinkValue)
                : 0,
    }));

    // Commodities first, then products, each ordered by value (highest first).
    // The chart renders nodes in this order (see layoutIterations in buildOption).
    const nodes: SankeyNode[] = Array.from(nodeTotals.entries())
        .map(([name, value]) => ({
            name,
            value,
        }))
        .sort((a, b) => {
            const aIsCommodity = a.name.startsWith(COMMODITY_PREFIX);
            const bIsCommodity = b.name.startsWith(COMMODITY_PREFIX);

            if (aIsCommodity !== bIsCommodity) {
                return aIsCommodity ? -1 : 1;
            }

            return b.value - a.value;
        });

    return { nodes, links, weightingMethod: selectedWeightingMethod };
}

const targetColourFamilies = dashboardChartColours.map((colour) => ({
    shades: [colour.tint, colour.shade],
    end: colour.base,
}));

function getLinksGroupedByTarget(links: SankeyLink[]) {
    return links.reduce<Record<string, SankeyLink[]>>((acc, link) => {
        if (!acc[link.target]) {
            acc[link.target] = [];
        }
        acc[link.target].push(link);
        return acc;
    }, {});
}

function getColourMaps(links: SankeyLink[]) {
    const linksByTarget = getLinksGroupedByTarget(links);
    const orderedTargets = [...new Set(links.map((link) => link.target))];

    const linkColourMap: Record<string, string> = {};
    const sourceColourMap: Record<string, string> = {};
    const targetColourMap: Record<string, string> = {};

    orderedTargets.forEach((target, targetIndex) => {
        const family =
            targetColourFamilies[targetIndex % targetColourFamilies.length];
        const targetLinks = linksByTarget[target];

        targetColourMap[target] = family.end;

        targetLinks.forEach((link, linkIndex) => {
            const shade = family.shades[linkIndex % family.shades.length];
            const linkKey = `${link.source}-${link.target}`;

            linkColourMap[linkKey] = shade;
            sourceColourMap[link.source] = shade;
        });
    });

    return {
        linkColourMap,
        sourceColourMap,
        targetColourMap,
        targetNames: new Set(orderedTargets),
    };
}

interface TooltipParams {
    dataType?: "edge" | "node";
    data: SankeyLink | SankeyNode;
}

function formatTooltip(
    { dataType, data }: TooltipParams,
    weightingMethod: FlowWeightingMethod,
): string {
    if (dataType === "edge") {
        const { source, target } = data as SankeyLink;

        const { value, percentage } = data as SankeyLink;

        const valueLabel = getValueLabel(value, weightingMethod);

        return `
            <div>
                <div><strong>${stripNodePrefix(source)} -> ${stripNodePrefix(
                    target,
                )}</strong></div>
              <div>${valueLabel} (${formatNumberToZeroDecimalPlaces(
                  percentage,
              )}%)</div>
            </div>
        `;
    }

    if (dataType === "node") {
        const { name, value } = data as SankeyNode;

        const valueLabel = getValueLabel(value, weightingMethod);

        return `
            <div>
                <div><strong>${stripNodePrefix(name)}</strong></div>
                <div>${valueLabel}</div>
            </div>
        `;
    }

    return "";
}

function buildOption(sankeyData: SankeyData) {
    const { linkColourMap, sourceColourMap, targetColourMap, targetNames } =
        getColourMaps(sankeyData.links);

    const nodes = sankeyData.nodes.map((node) => {
        const isTarget = targetNames.has(node.name);

        return {
            ...node,
            itemStyle: {
                color: isTarget
                    ? targetColourMap[node.name]
                    : sourceColourMap[node.name],
            },
            label: {
                color: natcapTheme.textColors.colorText,
                fontFamily: natcapTheme.fonts.fontFamilyText,
                fontSize: 12,
                distance: 10,
                position: isTarget ? "right" : "left",
                align: isTarget ? "left" : "right",
                verticalAlign: "middle",
                overflow: "truncate",
                width: 140,
                formatter: (params: { name: string }) =>
                    stripNodePrefix(params.name),
            },
        };
    });

    const links = sankeyData.links.map((link) => ({
        ...link,
        lineStyle: {
            color: linkColourMap[`${link.source}-${link.target}`],
            curveness: 0.5,
        },
    }));

    return {
        animation: true,
        tooltip: {
            trigger: "item",
            formatter: (params: TooltipParams) =>
                formatTooltip(params, sankeyData.weightingMethod),
        },
        series: [
            {
                type: "sankey",
                left: 150,
                right: 150,
                data: nodes,
                links,
                nodeAlign: "justify",
                // Keep nodes in data order (sorted by value) instead of letting
                // ECharts reorder them to reduce link crossings
                layoutIterations: 0,
                draggable: false,
                emphasis: {
                    focus: "adjacency",
                },
                nodeGap: 16,
                lineStyle: {
                    color: "source",
                    opacity: 0.75,
                },
            },
        ],
    };
}

interface CommoditiesToProductFlowChartProps {
    commoditySources: CommoditySource[];
    isLoading: boolean;
    error?: ApolloError;
}

const CommoditiesToProductFlowChart = ({
    sankeyData,
    isLoading,
    error,
}: {
    sankeyData: SankeyData;
    isLoading: boolean;
    error?: ApolloError;
}) => {
    const option = useMemo(() => buildOption(sankeyData), [sankeyData]);

    // ECharts crashes (matrix inversion of a zero-size view rect) if it computes
    // its layout while the container has zero width or height — e.g. before the
    // CSS aspect-ratio/height has settled on first mount, or after the container
    // is hidden (Paste keeps inactive tab panels mounted, so this chart stays
    // mounted with a zero-size container when its tab isn't active). Track the
    // measured state both ways so the chart unmounts whenever the container has
    // no size, instead of latching "measured" permanently after first mount.
    const containerRef = useRef<HTMLDivElement>(null);
    const [hasMeasuredSize, setHasMeasuredSize] = useState(false);

    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;

        const observer = new ResizeObserver(([entry]) => {
            const { width, height } = entry.contentRect;
            setHasMeasuredSize(width > 0 && height > 0);
        });
        observer.observe(el);

        return () => observer.disconnect();
    }, []);

    return (
        <LoaderAndErrorHandler
            hasData={sankeyData.links.length > 0}
            isLoading={isLoading}
            error={error}
            errorCategory={ComponentId.CommoditiesToProductsSankeyChart}
            // Force wrapper to take up 100% of the card height, effectively
            // "passing through" the height to Echarts
            loadedWrapperBoxProps={{ height: "100%" }}
        >
            <div
                ref={containerRef}
                style={{
                    height: "100%",
                    width: "100%",
                    aspectRatio: "2 / 1",
                }}
            >
                {hasMeasuredSize && (
                    <ReactEChartsCore
                        echarts={echarts}
                        theme="natcap"
                        option={option}
                        style={{ height: "100%", width: "100%" }}
                    />
                )}
            </div>
        </LoaderAndErrorHandler>
    );
};

const CommoditiesToProductCard = ({
    commoditySources,
    isLoading,
    error,
}: CommoditiesToProductFlowChartProps) => {
    // Filter to commodity-product rows once for reuse
    const commodityProductRows = useMemo(
        () =>
            commoditySources.filter(
                (item) => item.commoditySubgroup && item.product,
            ),
        [commoditySources],
    );

    // Determine data availability and default weighting method
    const { hasQuantityData, hasSpendData, defaultWeightingMethod } =
        useMemo(() => {
            const hasQuantity = commodityProductRows.some(
                (item) =>
                    item.quantityKilograms != null &&
                    item.quantityKilograms > 0,
            );
            const hasSpend = commodityProductRows.some(
                (item) => item.spend != null && item.spend > 0,
            );
            return {
                hasQuantityData: hasQuantity,
                hasSpendData: hasSpend,
                defaultWeightingMethod: getFlowWeightingMethod(
                    hasQuantity,
                    hasSpend,
                ),
            };
        }, [commodityProductRows]);

    const hasAnyData = hasQuantityData || hasSpendData;

    // State for selected weighting method
    const [selectedWeightingMethod, setSelectedWeightingMethod] = useState(
        defaultWeightingMethod,
    );

    // Show toggle only when both data types exist
    const showWeightingToggle = hasQuantityData && hasSpendData;

    // Reset selection if the selected type becomes unavailable
    useEffect(() => {
        if (
            selectedWeightingMethod === FlowWeightingMethod.Quantity &&
            !hasQuantityData
        ) {
            setSelectedWeightingMethod(defaultWeightingMethod);
        }

        if (
            selectedWeightingMethod === FlowWeightingMethod.Spend &&
            !hasSpendData
        ) {
            setSelectedWeightingMethod(defaultWeightingMethod);
        }
    }, [
        defaultWeightingMethod,
        hasQuantityData,
        hasSpendData,
        selectedWeightingMethod,
    ]);

    const sankeyData = useMemo(
        () => toSankeyData(commoditySources, selectedWeightingMethod),
        [commoditySources, selectedWeightingMethod],
    );

    if (!hasAnyData || sankeyData.links.length === 0) {
        return null;
    }

    const chartTagLine = getFlowChartTagLine(sankeyData.weightingMethod);

    return (
        <Card element="PADDED_CARD">
            <CardHeading
                tagLine={chartTagLine}
                buttons={
                    showWeightingToggle ? (
                        <RadioButtonGroup
                            name="weighting-method"
                            legend=""
                            value={selectedWeightingMethod}
                            onChange={(item) =>
                                setSelectedWeightingMethod(
                                    item as FlowWeightingMethod,
                                )
                            }
                            attached
                        >
                            <RadioButton value={FlowWeightingMethod.Quantity}>
                                Quantity
                            </RadioButton>
                            <RadioButton value={FlowWeightingMethod.Spend}>
                                Spend
                            </RadioButton>
                        </RadioButtonGroup>
                    ) : undefined
                }
            >
                Commodities to Products Flow
            </CardHeading>
            <CommoditiesToProductFlowChart
                sankeyData={sankeyData}
                isLoading={isLoading}
                error={error}
            />
        </Card>
    );
};

export default CommoditiesToProductCard;
