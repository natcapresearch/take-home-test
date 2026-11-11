import {
    Badge,
    Box,
    BoxProps,
    Popover,
    PopoverButton,
    PopoverContainer,
    Tooltip,
    usePopoverState,
    useTooltipState,
} from "@twilio-paste/core";
import { InformationIcon } from "@twilio-paste/icons/esm/InformationIcon";
import { WarningIcon } from "@twilio-paste/icons/esm/WarningIcon";
import { ReactNode, useId } from "react";

// Styled like the no-score ScoreBadge.
const NO_DATA_BADGE_ELEMENT = "COMPONENT_SCORE_BADGE_NO_SCORE";

export const NO_DATA_BADGE_TOOLTIP =
    "Click to learn why this data is unavailable.";

interface NoDataBadgeProps {
    label?: string;
    icon: "info" | "warning";
    explanation?: ReactNode;
}

function StaticBadge({
    label,
    icon,
}: Required<Pick<NoDataBadgeProps, "label" | "icon">>) {
    return (
        <Badge
            as="span"
            size="small"
            variant="decorative10"
            element={NO_DATA_BADGE_ELEMENT}
            data-testid="no-data-badge"
        >
            {icon === "warning" ? (
                <WarningIcon decorative size="sizeIcon10" />
            ) : (
                <InformationIcon decorative size="sizeIcon10" />
            )}
            {label}
        </Badge>
    );
}

// Paste popovers focus their trigger whenever their state updates while
// closed, including on page load and when closing, which also opens the
// trigger's tooltip. Spread `popoverProps` onto the Popover, which hands them
// to its dialog primitive. Pass `tooltipState` to the trigger's Tooltip, which
// stays hidden while the popover is open.
export function useNoFocusPopoverState() {
    const baseId = useId();
    const popover = usePopoverState({ baseId, modal: true });
    const tooltip = useTooltipState({ baseId: `${baseId}-tooltip` });

    return {
        popover,
        tooltipState: {
            ...tooltip,
            visible: tooltip.visible && !popover.visible,
        },
        popoverProps: {
            unstable_autoFocusOnShow: false,
            unstable_autoFocusOnHide: false,
        },
    };
}

function BadgeWrapper(props: BoxProps) {
    return (
        <Box
            as="span"
            display="inline-flex"
            width="max-content"
            marginY="spaceNegative10"
            {...props}
        />
    );
}

export default function NoDataBadge({
    label = "No data",
    icon,
    explanation,
}: NoDataBadgeProps) {
    const { popover, tooltipState, popoverProps } = useNoFocusPopoverState();

    if (!explanation) {
        return (
            <BadgeWrapper>
                <StaticBadge label={label} icon={icon} />
            </BadgeWrapper>
        );
    }

    // Stops clicks reaching a clickable parent, e.g. a selectable card. React
    // events from the popover bubble here too, despite its portal.
    return (
        <BadgeWrapper
            fontWeight="fontWeightNormal"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
        >
            <PopoverContainer state={popover}>
                <Tooltip text={NO_DATA_BADGE_TOOLTIP} state={tooltipState}>
                    <Box as="span" display="inline-flex">
                        {/* A reset button around a static badge, as Paste's
                            badge button shifts down on hover and focus. */}
                        <PopoverButton variant="reset" size="reset">
                            <StaticBadge label={label} icon={icon} />
                        </PopoverButton>
                    </Box>
                </Tooltip>
                <Popover aria-label={label} {...popoverProps}>
                    {explanation}
                </Popover>
            </PopoverContainer>
        </BadgeWrapper>
    );
}
