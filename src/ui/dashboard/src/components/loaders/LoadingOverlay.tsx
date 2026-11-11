import { Box } from "@twilio-paste/core";
import { keyframes, styled } from "styled-components";
import { colours } from "../../../../common/theme/colours";

/**
 * Overlay spinner shown when a table re-fetches (e.g. on sort change).
 *
 * We use a native keyframe spinner instead of Paste's Spinner because:
 *   1. Paste's Spinner returns null on first render (Safari detection via
 *      useEffect), so it is invisible during short-lived conditional mounts.
 *   2. Paste's @keyframes omit keyframe selectors (e.g. `to {}`), which
 *      Safari rejects — causing the SVG to render but never rotate.
 *
 * The ring uses styled.div (not styled(Box)) to avoid a CSS injection conflict
 * where Emotion's border-color class overrides the styled-components
 * border-top-color override, making all four sides the same colour and the
 * rotation invisible.
 */

// Sticky so it stays on screen when the table is taller than its scroll
// container (or the page): centred as usual while the table's centre is in
// view, otherwise held just inside the visible edge.
const SpinnerRing = styled.div`
    position: sticky;
    top: 1rem;
    bottom: 1rem;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    border: 2px solid rgba(0, 0, 0, 0.12);
    border-top-color: ${colours.gray100};
    animation: ${keyframes`to { transform: rotate(360deg); }`} 0.75s linear
        infinite;
`;

// The same ring at checkbox size, for a control that is busy in place. Not
// sticky, and fixed so a narrow flex cell cannot squash it into an oval.
export const InlineSpinnerRing = styled(SpinnerRing)`
    position: static;
    width: 1.25rem;
    height: 1.25rem;
    flex-shrink: 0;
    box-sizing: border-box;
`;

// For a table that is the content of its own fixed-height scroll container,
// starting at its top: holds the spinner no lower than the middle of the
// visible area, where the default would leave it at the bottom edge. Sticky
// percentage insets resolve against the scroll container's height.
const ScrollContainerSpinnerRing = styled(SpinnerRing)`
    bottom: calc(50% - 0.75rem);
`;

interface LoadingOverlayProps {
    inScrollContainer?: boolean;
}

const LoadingOverlay = ({ inScrollContainer = false }: LoadingOverlayProps) => (
    <Box
        position="absolute"
        top="0"
        left="0"
        width="100%"
        height="100%"
        display="flex"
        alignItems="center"
        justifyContent="center"
        zIndex="zIndex90"
        backgroundColor="colorBackgroundBusy"
    >
        {inScrollContainer ? <ScrollContainerSpinnerRing /> : <SpinnerRing />}
    </Box>
);

export default LoadingOverlay;
