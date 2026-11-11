import { Box, Spinner, Text } from "@twilio-paste/core";
import { FeatureCollection, Geometry } from "geojson";
import { geoJSON, LatLngBounds, Layer, LeafletMouseEvent } from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useState } from "react";
import {
    GeoJSON,
    MapContainer,
    ScaleControl,
    TileLayer,
    useMap,
} from "react-leaflet";
import tc from "tinycolor2";
import { mapColours } from "../../../../common/theme/colours";
import {
    FitBounds,
    MapResizeHandler,
} from "../../helpers/leaflet/leafletReactHelpers";
import { worldBounds } from "../../helpers/mapHelpers";

export type BaseRegionProperties = {
    countryName: string;
    regionName: string;
};

type HoverPosition = { x: number; y: number };

export function getRegionKey(props: BaseRegionProperties) {
    return `${props.countryName}-${props.regionName}`;
}

export function buildFeatureCollection<T extends BaseRegionProperties>(
    regions: T[],
    getGeometry: (region: T) => Geometry | null,
): FeatureCollection<Geometry, T> {
    return buildMappedFeatureCollection(regions, (region) => ({
        properties: region,
        geometry: getGeometry(region),
    }));
}

export function buildMappedFeatureCollection<
    TSource,
    TProps extends BaseRegionProperties,
>(
    source: TSource[],
    mapSource: (
        item: TSource,
    ) => { properties: TProps; geometry: Geometry | null } | null,
): FeatureCollection<Geometry, TProps> {
    const grouped = new Map<string, { geometry: Geometry; props: TProps }>();

    source.forEach((item) => {
        const mapped = mapSource(item);
        if (!mapped || !mapped.geometry) {
            return;
        }

        const key = getRegionKey(mapped.properties);
        if (grouped.has(key)) {
            return;
        }

        grouped.set(key, {
            geometry: mapped.geometry,
            props: mapped.properties,
        });
    });

    return {
        type: "FeatureCollection",
        features: Array.from(grouped.values()).map(({ geometry, props }) => ({
            type: "Feature",
            properties: props,
            geometry,
        })),
    };
}

interface ChoroplethLayerProps<T extends BaseRegionProperties> {
    featureCollection: FeatureCollection<Geometry, T>;
    layerKey: string;
    hoveredRegion: T | undefined;
    setHoveredRegion: (region: T | undefined) => void;
    setHoverPosition: (position: HoverPosition | undefined) => void;
    getFillColor: (region: T) => string;
}

function ChoroplethLayer<T extends BaseRegionProperties>({
    featureCollection,
    layerKey,
    hoveredRegion,
    setHoveredRegion,
    setHoverPosition,
    getFillColor,
}: ChoroplethLayerProps<T>) {
    const map = useMap();
    const hoveredRegionKey = hoveredRegion ? getRegionKey(hoveredRegion) : null;

    const updateHoverPosition = (event: LeafletMouseEvent) => {
        const bounds = map.getContainer().getBoundingClientRect();

        setHoverPosition({
            x: event.originalEvent.clientX - bounds.left + 16,
            y: event.originalEvent.clientY - bounds.top - 16,
        });
    };
    return (
        <GeoJSON
            key={layerKey}
            data={featureCollection}
            onEachFeature={(feature, layer: Layer) => {
                const props = feature.properties as T;
                layer.on({
                    mouseover: (event: LeafletMouseEvent) => {
                        setHoveredRegion(props);
                        updateHoverPosition(event);
                    },
                    mousemove: updateHoverPosition,
                    mouseout: () => {
                        setHoveredRegion(undefined);
                        setHoverPosition(undefined);
                    },
                });
            }}
            style={(feature) => {
                const props = feature?.properties as T;
                const fillColor = getFillColor(props);
                const isHovered = getRegionKey(props) === hoveredRegionKey;

                return {
                    stroke: true,
                    color: tc(fillColor)
                        .darken(isHovered ? 30 : 20)
                        .toString(),
                    weight: isHovered ? 2 : 1,
                    fillColor,
                    fillOpacity: 1,
                };
            }}
        />
    );
}

interface RegionMapProps<T extends BaseRegionProperties> {
    featureCollection: FeatureCollection<Geometry, T>;
    getFillColor: (region: T) => string;
    renderPopupContent: (region: T) => React.ReactNode;
    layerKey: string;
    legend: React.ReactNode;
    legendTitle: string;
    isLoading?: boolean;
    // Stretch to the container's height instead of the fixed 35rem.
    fillHeight?: boolean;
}

export function RegionMap<T extends BaseRegionProperties>({
    featureCollection,
    getFillColor,
    renderPopupContent,
    layerKey,
    legend,
    legendTitle,
    isLoading = false,
    fillHeight = false,
}: RegionMapProps<T>) {
    const [hoveredRegion, setHoveredRegion] = useState<T>();
    const [hoverPosition, setHoverPosition] = useState<HoverPosition>();

    const regionBounds = useMemo<LatLngBounds | null>(() => {
        const bounds = geoJSON(featureCollection).getBounds();
        return bounds.isValid() ? bounds : null;
    }, [featureCollection]);
    const hasFeatures = featureCollection.features.length > 0;

    useEffect(() => {
        setHoveredRegion(undefined);
        setHoverPosition(undefined);
    }, [layerKey]);

    return (
        <>
            <Box
                height={fillHeight ? undefined : "35rem"}
                flex={fillHeight ? "1" : undefined}
                display={fillHeight ? "flex" : undefined}
                flexDirection={fillHeight ? "column" : undefined}
                minHeight={fillHeight ? "400px" : undefined}
                position="relative"
            >
                {!hasFeatures && (
                    <Box
                        position="absolute"
                        top="50%"
                        left="50%"
                        transform="translate(-50%, -50%)"
                        zIndex="zIndex10"
                    >
                        <Text as="p" fontStyle="italic" element="TEXT_WEAK">
                            No regional boundaries available.
                        </Text>
                    </Box>
                )}

                {hoveredRegion && hoverPosition && (
                    <Box
                        position="absolute"
                        top={`${hoverPosition.y}px`}
                        left={`${hoverPosition.x}px`}
                        zIndex="zIndex90"
                        style={{ zIndex: 1001 }}
                    >
                        <Box
                            minWidth="size30"
                            maxWidth="size50"
                            backgroundColor="colorBackgroundPrimaryStrongest"
                            color="colorTextInverse"
                            borderRadius="borderRadius40"
                            padding="space60"
                            fontSize="fontSize20"
                        >
                            {renderPopupContent(hoveredRegion)}
                        </Box>
                    </Box>
                )}

                <MapContainer
                    center={[15, 0]}
                    zoom={2}
                    maxBounds={worldBounds}
                    style={{
                        height: "100%",
                        flex: fillHeight ? "1" : undefined,
                        minHeight: fillHeight ? "400px" : undefined,
                        width: "100%",
                        background: mapColours.water,
                    }}
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        noWrap={true}
                        bounds={worldBounds}
                    />

                    <FitBounds
                        bounds={regionBounds}
                        options={{ padding: [24, 24], maxZoom: 5 }}
                    />

                    {fillHeight && <MapResizeHandler />}

                    <ScaleControl position="bottomleft" />

                    <ChoroplethLayer<T>
                        featureCollection={featureCollection}
                        layerKey={layerKey}
                        hoveredRegion={hoveredRegion}
                        setHoveredRegion={setHoveredRegion}
                        setHoverPosition={setHoverPosition}
                        getFillColor={getFillColor}
                    />
                </MapContainer>

                {hasFeatures && (
                    <Box element="MAP_LEGEND">
                        <Box element="MAP_LEGEND_TITLE">{legendTitle}</Box>
                        {legend}
                    </Box>
                )}

                {isLoading && (
                    <Box element="LOADER_OVERLAY">
                        <Box opacity={1}>
                            <Spinner decorative={true} title="Loading" />
                        </Box>
                    </Box>
                )}
            </Box>
        </>
    );
}
