import { Box, Tooltip } from "@twilio-paste/core";
import * as echarts from "echarts/core";
import { createElement, useEffect, useRef, useState } from "react";
import sanitizeHtml from "sanitize-html";
import { createGlobalStyle } from "styled-components";
import { natcapTheme } from "../../../common/theme/base";
import { colours } from "../../../common/theme/colours";

export interface XYPoint {
    x: number;
    y: number;
}

export type JitteredXYPoint<T extends XYPoint> = T & {
    value: [number, number];
    symbolOffset?: [string, string];
};

export function applyJitterToPoints<T extends XYPoint>(
    points: T[],
): JitteredXYPoint<T>[] {
    const jitterPercent = 50;
    const counts = new Map<string, number>();

    return points.map((p) => {
        const key = `${p.x}-${p.y}`;
        const index = counts.get(key) ?? 0;
        counts.set(key, index + 1);

        return {
            ...p,
            value: [p.x, p.y],
            ...(index > 0 && {
                symbolOffset: [
                    `${(Math.random() * 2 - 1) * jitterPercent}%`,
                    `${(Math.random() * 2 - 1) * jitterPercent}%`,
                ],
            }),
        };
    });
}

const natcapEchartsTheme = {
    textStyle: {
        fontFamily: natcapTheme.fonts.fontFamilyText,
        color: natcapTheme.textColors.colorTextWeak,
        fontSize: 14,
    },
    categoryAxis: {
        axisTick: {
            show: false,
        },
        axisLine: {
            lineStyle: {
                color: natcapTheme.borderColors.colorBorderWeaker,
            },
        },
        axisLabel: {
            fontFamily: natcapTheme.fonts.fontFamilyText,
            color: natcapTheme.textColors.colorTextWeak,
            fontSize: 14,
        },
        nameTextStyle: {
            fontFamily: natcapTheme.fonts.fontFamilyText,
            fontSize: 12,
        },
    },
    valueAxis: {
        axisTick: {
            show: false,
        },
        axisLine: {
            lineStyle: {
                color: natcapTheme.borderColors.colorBorderWeaker,
            },
        },
        axisLabel: {
            fontFamily: natcapTheme.fonts.fontFamilyText,
            color: natcapTheme.textColors.colorTextWeak,
            fontSize: 14,
        },
        nameTextStyle: {
            fontFamily: natcapTheme.fonts.fontFamilyText,
            fontSize: 12,
        },
    },
    legend: {
        textStyle: {
            fontFamily: natcapTheme.fonts.fontFamilyText,
            color: natcapTheme.textColors.colorTextWeak,
            fontSize: 12,
        },
        itemWidth: 12,
        itemHeight: 12,
    },
    tooltip: {
        backgroundColor:
            natcapTheme.backgroundColors.colorBackgroundPrimaryStrongest,
        textStyle: {
            color: natcapTheme.textColors.colorTextInverse,
            fontSize: 12,
        },
        borderRadius: 10,
        borderColor: "transparent",
        padding: 20,
    },
    label: {
        color: natcapTheme.textColors.colorTextWeak,
        fontFamily: natcapTheme.fonts.fontFamilyText,
        fontSize: 10,
    },
};

export function registerNatcapEchartsTheme() {
    echarts.registerTheme("natcap", natcapEchartsTheme);
}

export interface StackedShareTooltipRow {
    label: string;
    percent: string;
    total: string;
    color?: string;
    isTotalRow?: boolean;
}

interface BuildStackedShareTooltipHtmlArgs {
    heading: string;
    rows: StackedShareTooltipRow[];
}

interface TooltipRowArgs {
    label: string;
    markerColor?: string;
    values?: Array<string | null | undefined>;
    markerPatternColor?: string;
    isHighlighted?: boolean;
    isSectionHeading?: boolean;
    hasBorderTop?: boolean;
    hasMarginBottom?: boolean;
    indentLevel?: number;
    noteText?: string;
}

interface TooltipContainerArgs {
    heading?: string;
    headingMarkerColor?: string;
    headingMarkerPatternColor?: string;
    headingSuffix?: string;
    headingNote?: string;
    hideHeadingNoteLine?: boolean;
    rowsHtml: string[];
}

const tooltipTextSanitizeOptions = {
    allowedTags: [],
    allowedAttributes: {},
};

export const EchartsTooltipGlobalStyle = createGlobalStyle`
    .natcap-echarts-tooltip {
        padding: 0;
        margin: 0;
    }

    .natcap-echarts-tooltip__heading {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: bold;
        margin-bottom: 12px;
        font-size: 14px;
        padding-bottom: 8px;
        border-bottom: 1px solid ${natcapTheme.borderColors.colorBorder};
    }

    .natcap-echarts-tooltip__heading .natcap-echarts-tooltip__marker {
        width: 12px;
        height: 12px;
    }

    .natcap-echarts-tooltip__heading-suffix {
        font-weight: normal;
        font-size: 12px;
    }

    .natcap-echarts-tooltip__heading-note {
        font-size: 10px;
        color: ${natcapTheme.textColors.colorTextInverseWeaker};
        margin-top: -10px;
        margin-bottom: 6px;
        padding-bottom: 6px;
        border-bottom: 1px solid ${natcapTheme.borderColors.colorBorder};
    }

    .natcap-echarts-tooltip__heading-note--no-line {
        border-bottom: none;
        padding-bottom: 0;
        margin-bottom: 12px;
    }

    .natcap-echarts-tooltip__note-link {
        color: ${natcapTheme.textColors.colorTextInverse};
        text-decoration: underline;
        font-weight: bold;
    }

    .natcap-echarts-tooltip__row {
        display: block;
        width: 100%;
        margin: 0;
    }

    .natcap-echarts-tooltip__row--border-top {
        border-top: 1px solid ${natcapTheme.borderColors.colorBorder};
        padding-top: 8px;
        margin-top: 6px;
    }

    .natcap-echarts-tooltip__row--highlighted {
        border-bottom: 1px solid ${natcapTheme.borderColors.colorBorder};
        padding-bottom: 8px;
        margin-bottom: 8px;
    }

    .natcap-echarts-tooltip__row--highlighted .natcap-echarts-tooltip__label-block {
        font-size: 13px;
        font-weight: bold;
    }

    .natcap-echarts-tooltip__row--highlighted .natcap-echarts-tooltip__value {
        font-size: 13px;
    }

    .natcap-echarts-tooltip__row--margin-bottom {
        margin-bottom: 8px;
    }

    .natcap-echarts-tooltip__row--section-heading {
        font-weight: bold;
        color: ${natcapTheme.textColors.colorTextInverse};
    }

    .natcap-echarts-tooltip__row--section-heading .natcap-echarts-tooltip__label-block {
        font-size: 13px;
    }

    .natcap-echarts-tooltip__row--section-heading .natcap-echarts-tooltip__value {
        font-size: 13px;
    }

    .natcap-echarts-tooltip__row--indent-1 .natcap-echarts-tooltip__values,
    .natcap-echarts-tooltip__row--indent-2 .natcap-echarts-tooltip__values {
        font-weight: normal;
    }

    .natcap-echarts-tooltip__row--indent-1 .natcap-echarts-tooltip__label-block {
        margin-left: 12px;
    }

    .natcap-echarts-tooltip__row--indent-2 .natcap-echarts-tooltip__label-block {
        margin-left: 24px;
    }

    .natcap-echarts-tooltip__line {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        width: 100%;
    }

    .natcap-echarts-tooltip__label-block {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1 1 auto;
        min-width: 0;
    }

    .natcap-echarts-tooltip__label--highlighted {
        font-weight: bold;
    }

    .natcap-echarts-tooltip__values {
        display: flex;
        gap: 24px;
        font-weight: bold;
        flex-shrink: 0;
        white-space: nowrap;
    }

    .natcap-echarts-tooltip__value {
        min-width: 64px;
        text-align: right;
    }

    .natcap-echarts-tooltip__note {
        font-size: 10px;
        color: ${natcapTheme.textColors.colorTextInverseWeaker};
        margin-top: 4px;
    }

    .natcap-echarts-tooltip__marker {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 20%;
        background: var(--natcap-tooltip-marker-color);
        background-image: repeating-linear-gradient(
            45deg,
            var(--natcap-tooltip-marker-pattern-color, transparent) 0,
            var(--natcap-tooltip-marker-pattern-color, transparent) 2px,
            transparent 2px,
            transparent 4px
        );
        flex-shrink: 0;
    }
`;

function buildTooltipMarkerHtml({
    color,
    patternColor,
}: {
    color: string;
    patternColor?: string;
}) {
    return `
        <span
            class="natcap-echarts-tooltip__marker"
            style="
                --natcap-tooltip-marker-color:${color};
                ${
                    patternColor
                        ? `--natcap-tooltip-marker-pattern-color:${patternColor};`
                        : ""
                }
            "
        ></span>
    `;
}

export function buildTooltipRowHtml({
    label,
    markerColor,
    values,
    markerPatternColor,
    isHighlighted,
    isSectionHeading,
    hasBorderTop,
    hasMarginBottom,
    indentLevel,
    noteText,
}: TooltipRowArgs): string {
    const marker = markerColor
        ? buildTooltipMarkerHtml({
              color: markerColor,
              patternColor: markerPatternColor,
          })
        : "";

    const sanitizedLabel = sanitizeHtml(label, tooltipTextSanitizeOptions);
    const sanitizedValues = (values ?? [])
        .map((value) => {
            if (value === null || value === undefined) {
                return "";
            }

            return sanitizeHtml(String(value), tooltipTextSanitizeOptions);
        })
        .filter((value) => value.trim().length > 0);
    const sanitizedNoteText = noteText
        ? sanitizeHtml(noteText, tooltipTextSanitizeOptions)
        : "";

    const rightColumnsHtml = sanitizedValues
        .map((value) => {
            return `<span class="natcap-echarts-tooltip__value">${value}</span>`;
        })
        .join("");
    const rowClasses = ["natcap-echarts-tooltip__row"];
    const hasValueColumns = sanitizedValues.length > 0;

    if (!hasValueColumns && !sanitizedNoteText && !sanitizedLabel) {
        return "";
    }

    if (hasBorderTop) {
        rowClasses.push("natcap-echarts-tooltip__row--border-top");
    }
    if (isHighlighted) {
        rowClasses.push("natcap-echarts-tooltip__row--highlighted");
    }
    if (isSectionHeading) {
        rowClasses.push("natcap-echarts-tooltip__row--section-heading");
    }
    if (hasMarginBottom) {
        rowClasses.push("natcap-echarts-tooltip__row--margin-bottom");
    }
    if (indentLevel && indentLevel > 0) {
        rowClasses.push(
            `natcap-echarts-tooltip__row--indent-${Math.min(
                Math.floor(indentLevel),
                2,
            )}`,
        );
    }

    return `
        <div class="${rowClasses.join(" ")}">
            <div class="natcap-echarts-tooltip__line">
                <div class="natcap-echarts-tooltip__label-block">
                    ${marker}
                    <span class="${
                        isHighlighted
                            ? "natcap-echarts-tooltip__label--highlighted"
                            : ""
                    }">${sanitizedLabel}</span>
                </div>
                ${
                    hasValueColumns
                        ? `<div class="natcap-echarts-tooltip__values">${rightColumnsHtml}</div>`
                        : ""
                }
            </div>
            ${
                sanitizedNoteText
                    ? `<div class="natcap-echarts-tooltip__note">${sanitizedNoteText}</div>`
                    : ""
            }
        </div>
    `;
}

export function buildTooltipContainerHtml({
    heading,
    headingMarkerColor,
    headingMarkerPatternColor,
    headingSuffix,
    headingNote,
    hideHeadingNoteLine,
    rowsHtml,
}: TooltipContainerArgs): string {
    const sanitizedHeading =
        heading !== undefined && heading !== null
            ? sanitizeHtml(heading, tooltipTextSanitizeOptions)
            : "";
    const sanitizedHeadingSuffix =
        headingSuffix !== undefined && headingSuffix !== null
            ? sanitizeHtml(headingSuffix, tooltipTextSanitizeOptions)
            : "";
    const sanitizedHeadingNote =
        headingNote !== undefined && headingNote !== null
            ? sanitizeHtml(headingNote, tooltipTextSanitizeOptions)
            : "";
    const nonEmptyRowsHtml = rowsHtml.filter((row) => row.trim().length > 0);
    const headingMarkerHtml = headingMarkerColor
        ? buildTooltipMarkerHtml({
              color: headingMarkerColor,
              patternColor: headingMarkerPatternColor,
          })
        : "";

    return `
        <div class="natcap-echarts-tooltip">
            ${
                sanitizedHeading
                    ? `<div class="natcap-echarts-tooltip__heading">${headingMarkerHtml}${sanitizedHeading}${
                          sanitizedHeadingSuffix
                              ? ` <span class="natcap-echarts-tooltip__heading-suffix">${sanitizedHeadingSuffix}</span>`
                              : ""
                      }</div>`
                    : ""
            }
            ${
                sanitizedHeadingNote
                    ? `<div class="natcap-echarts-tooltip__heading-note${
                          hideHeadingNoteLine
                              ? " natcap-echarts-tooltip__heading-note--no-line"
                              : ""
                      }">${sanitizedHeadingNote}</div>`
                    : ""
            }
            ${nonEmptyRowsHtml.join("")}
        </div>
    `;
}

export function buildStackedShareTooltipHtml({
    heading,
    rows,
}: BuildStackedShareTooltipHtmlArgs): string {
    const rowsWithContent = rows.filter((row) => {
        const hasPercent = row.percent.trim().length > 0;
        const hasTotal = row.total.trim().length > 0;

        return hasPercent || hasTotal;
    });

    const rowsHtml = rowsWithContent.map((row, index) => {
        const hasPreviousRow = index > 0;

        return buildTooltipRowHtml({
            label: row.label,
            markerColor: row.color,
            values: [row.percent, row.total],
            hasBorderTop: Boolean(row.isTotalRow && hasPreviousRow),
        });
    });

    return buildTooltipContainerHtml({
        heading,
        rowsHtml,
    });
}

export function buildCommodityShareTooltipHtml({
    commodityName,
    commoditySharePercent,
    otherSharePercent,
    commodityTotal,
    otherTotal,
    totalTotal,
    commodityColor,
    otherColor,
    formatter,
}: {
    commodityName: string;
    commoditySharePercent: number;
    otherSharePercent: number;
    commodityTotal: number;
    otherTotal: number;
    totalTotal: number;
    commodityColor: string;
    otherColor: string;
    formatter: (value: number) => string;
}): string {
    return buildStackedShareTooltipHtml({
        heading: commodityName,
        rows: [
            {
                label: commodityName,
                percent: `${commoditySharePercent.toFixed(1)}%`,
                total: formatter(commodityTotal),
                color: commodityColor,
            },
            {
                label: "Other commodities",
                percent: `${otherSharePercent.toFixed(1)}%`,
                total: formatter(otherTotal),
                color: otherColor,
            },
            {
                label: "All commodities",
                percent: "100.0%",
                total: formatter(totalTotal),
                isTotalRow: true,
            },
        ],
    });
}

export const BAR_CATEGORY_GAP = "20%";
export const CHART_GRID_BOTTOM = 70;
export const SINGLE_BAR_WIDTH = 64;

export const OTHER_CATEGORY_COLOUR = colours.gray20;
export const SINGLE_BAR_COLOUR = colours.blue60;
export const CHART_GRID_TOP = 40;
export const CHART_GRID_RIGHT = 0;

// Segments narrower than this share of a stacked bar don't have room to fit
// the value label without it overflowing outside the segment. Below this
// threshold the label is hidden; the value is still visible in the tooltip.
export const MIN_STACKED_BAR_LABEL_PERCENT = 6;

export function shouldShowStackedBarLabel(percent: number) {
    return percent >= MIN_STACKED_BAR_LABEL_PERCENT;
}

interface TruncatedAxisLabelProps {
    label: string;
}

export const TruncatedAxisLabel = ({ label }: TruncatedAxisLabelProps) => {
    const labelRef = useRef<HTMLSpanElement | null>(null);
    const [isTruncated, setIsTruncated] = useState(false);

    useEffect(() => {
        const measureOverflow = () => {
            const element = labelRef.current;

            if (!element) {
                return;
            }

            setIsTruncated(element.scrollWidth > element.clientWidth);
        };

        measureOverflow();
        window.addEventListener("resize", measureOverflow);

        return () => window.removeEventListener("resize", measureOverflow);
    }, [label]);

    const content = createElement(
        Box,
        {
            as: "span",
            ref: labelRef,
            display: "block",
            width: "100%",
            minWidth: 0,
            overflow: "hidden",
            whiteSpace: "nowrap",
            textAlign: "right",
            color: "colorTextWeak",
            fontSize: "fontSize20",
            style: { textOverflow: "ellipsis" },
        },
        label,
    );

    if (!isTruncated) {
        return content;
    }

    return createElement(Tooltip, {
        text: label,
        placement: "top",
        children: createElement(
            Box,
            {
                as: "span",
                tabIndex: 0,
                display: "block",
                width: "100%",
                minWidth: 0,
            },
            content,
        ),
    });
};
