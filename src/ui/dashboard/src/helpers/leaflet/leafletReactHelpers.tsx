// leafletHelpers.tsx
import { Box } from "@twilio-paste/core";
import L from "leaflet";
import { defer } from "lodash";
import { JSX, useEffect } from "react";
import { createRoot, Root } from "react-dom/client";
import { useMap } from "react-leaflet";
import Base, { natcapTheme } from "../../../../common/theme/base";
import { hexToRgba } from "../stringHelpers";

type PopupCapableLayer = L.Layer & {
    bindPopup: (content: HTMLElement, options?: L.PopupOptions) => L.Layer;
    getPopup: () => L.Popup | undefined;
};

export const popupRoots = new WeakMap<PopupCapableLayer, Root>();

/**
 * Helper to render a React component into a Leaflet popup.
 *
 * Leaflet’s bindPopup only accepts strings or raw HTMLElements.
 * We want to render Twilio Paste React components (e.g. <Button>, <Text>).
 *
 * Paste components rely on React context and CSS-in-JS for theming and styling.
 *
 * The solution is to:
 * 1. Create a <div> container.
 * 2. Bind that container as the popup’s content.
 * 3. When the popup opens, mount a React root (createRoot) into the container
 * and render our React JSX.
 * 4. On close, unmount the React root (deferred) to avoid React 18 sync-unmount issues.
 *
 * This ensures the popup content is part of the React tree, so Paste theming
 * and styles load correctly, while still using Leaflet’s popup API.
 */
export function bindReactPopup(
    layer: PopupCapableLayer,
    jsx: JSX.Element,
    options?: L.PopupOptions,
) {
    const container = document.createElement("div");
    container.style.width = "max-content";
    container.style.display = "block";

    layer.bindPopup(container, {
        closeButton: false,
        autoPan: true,
        ...options,
    });

    layer.on("popupopen", () => {
        const popupRoot = layer.getPopup()?.getElement();
        popupRoot?.setAttribute("data-paste-element", "LEAFLET_TOOLTIP");

        const contentEl = popupRoot?.querySelector<HTMLElement>(
            ".leaflet-popup-content",
        );
        contentEl?.style.setProperty("width", "max-content");
        contentEl?.style.setProperty("margin", "10px");

        let root = popupRoots.get(layer);
        if (!root) {
            root = createRoot(container);
            popupRoots.set(layer, root);
        }
        root.render(<Base>{jsx}</Base>);
    });

    const deferredUnmount = () => {
        const root = popupRoots.get(layer);
        if (!root) return;

        defer(() => {
            try {
                root.unmount();
            } finally {
                popupRoots.delete(layer);
            }
        });
    };

    layer.on("popupclose", deferredUnmount);

    layer.getPopup()?.on("remove", deferredUnmount);
    layer.on("remove", deferredUnmount);
}

export interface ClusterContainer extends HTMLDivElement {
    __reactRoot?: Root;
}

/**
 * Cleanup for a mounted React cluster icon container.
 * Call on Leaflet cluster lifecycle events (e.g., `layerremove`) to prevent leaks.
 */
export function unmountReactClusterIcon(container?: Element | null): void {
    if (!container) return;
    const clusterContainer = container as ClusterContainer;
    const root = clusterContainer.__reactRoot;
    if (!root) return;

    defer(() => {
        try {
            root.unmount();
        } finally {
            delete clusterContainer.__reactRoot;
        }
    });
}

interface ClusterIconProps {
    count: number;
    size?: number;
    colour?: string;
}

export const ClusterIcon = ({
    count,
    size = 30,
    colour = "colorBackgroundPrimaryStrong",
}: ClusterIconProps) => {
    const fontSize =
        size >= 62 ? "fontSize40" : size >= 46 ? "fontSize30" : "fontSize20";

    const ringPx = Math.round(size * 0.18);

    return (
        <Box
            width={`${size}px`}
            height={`${size}px`}
            display="flex"
            alignItems="center"
            justifyContent="center"
            borderRadius="borderRadiusCircle"
            fontSize={fontSize}
            color="colorTextBrandInverse"
            // @ts-expect-error - we can send computed colours so can't type strictly
            backgroundColor={colour}
            borderColor="colorBorderDecorative10Weaker"
            borderWidth="borderWidth10"
            borderStyle="solid"
            // @ts-expect-error - boxShadow token isn't in Paste's typed props
            boxShadow={`0 0 0 ${ringPx}px ${hexToRgba(
                natcapTheme.backgroundColors.colorBackgroundPrimary,
                0.3,
            )}`}
        >
            {count}
        </Box>
    );
};

/**
 * Cleans up any React popup root associated with a Leaflet marker layer.
 *
 * React popups are mounted outside React’s lifecycle and stored in `popupRoots`,
 * so they must be explicitly unmounted when the marker is removed.
 */
export const cleanupPopupRootForLayer = (layer: L.Layer) => {
    if (!("getPopup" in layer)) return;

    const popupLayer = layer as PopupCapableLayer;
    const root = popupRoots.get(popupLayer);
    if (!root) return;

    defer(() => {
        try {
            root.unmount();
        } finally {
            popupRoots.delete(popupLayer);
        }
    });
};

/**
 * Fits the map to the given Leaflet bounds whenever they change.
 * Must be rendered inside a <MapContainer>.
 */
export const FitBounds = ({
    bounds,
    options,
}: {
    bounds: L.LatLngBounds | null | undefined;
    options?: L.FitBoundsOptions;
}) => {
    const map = useMap();

    useEffect(() => {
        const coords = bounds
            ? [
                  bounds.getSouth(),
                  bounds.getNorth(),
                  bounds.getEast(),
                  bounds.getWest(),
              ]
            : [];
        if (bounds?.isValid() && coords.every(Number.isFinite)) {
            const mapSize = map.getSize();
            // Clamp padding so it never exceeds half the container dimension.
            // If padding >= container size / 2, Leaflet computes a negative scale
            // which produces NaN zoom and throws "Invalid LatLng object: (NaN, NaN)".
            const rawPadding = options?.padding;
            const safeOptions =
                rawPadding && Array.isArray(rawPadding)
                    ? {
                          ...options,
                          padding: [
                              Math.min(
                                  rawPadding[0] as number,
                                  Math.floor(mapSize.x / 2) - 1,
                              ),
                              Math.min(
                                  rawPadding[1] as number,
                                  Math.floor(mapSize.y / 2) - 1,
                              ),
                          ] as L.PointExpression,
                      }
                    : options;
            map.fitBounds(bounds, safeOptions);
        }
        // options is static config — intentionally excluded from deps
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [bounds, map]);

    return null;
};

// Leaflet only re-measures on window resize; this also catches layout-driven
// container size changes. Render inside a <MapContainer>.
export const MapResizeHandler = () => {
    const map = useMap();

    useEffect(() => {
        const container = map.getContainer();
        const observer = new ResizeObserver(() => {
            map.invalidateSize({ debounceMoveend: true });
        });
        observer.observe(container);

        return () => observer.disconnect();
    }, [map]);

    return null;
};
