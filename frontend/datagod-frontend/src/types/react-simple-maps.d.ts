// Type declarations for third-party modules without types

declare module 'react-simple-maps' {
    import { ComponentType, ReactNode } from 'react';

    export interface ComposableMapProps {
        projection?: string;
        projectionConfig?: {
            scale?: number;
            center?: [number, number];
            rotate?: [number, number, number];
        };
        width?: number;
        height?: number;
        children?: ReactNode;
        style?: React.CSSProperties;
        className?: string;
    }

    export interface GeographiesProps {
        geography: string | object;
        children: (props: { geographies: any[] }) => ReactNode;
    }

    export interface GeographyProps {
        geography: any;
        style?: {
            default?: React.CSSProperties;
            hover?: React.CSSProperties;
            pressed?: React.CSSProperties;
        };
        onMouseEnter?: (event: React.MouseEvent) => void;
        onMouseLeave?: (event: React.MouseEvent) => void;
        onClick?: (event: React.MouseEvent) => void;
    }

    export interface ZoomableGroupProps {
        center?: [number, number];
        zoom?: number;
        minZoom?: number;
        maxZoom?: number;
        onMoveStart?: () => void;
        onMove?: (position: { x: number; y: number; zoom: number }) => void;
        onMoveEnd?: () => void;
        children?: ReactNode;
    }

    export interface MarkerProps {
        coordinates: [number, number];
        children?: ReactNode;
        style?: React.CSSProperties;
        onClick?: (event: React.MouseEvent) => void;
        onMouseEnter?: (event: React.MouseEvent) => void;
        onMouseLeave?: (event: React.MouseEvent) => void;
    }

    export interface AnnotationProps {
        subject?: [number, number];
        dx?: number;
        dy?: number;
        connectorProps?: object;
        children?: ReactNode;
    }

    export interface LineProps {
        from?: [number, number];
        to?: [number, number];
        stroke?: string;
        strokeWidth?: number;
        strokeLinecap?: string;
    }

    export interface SphereProps {
        stroke?: string;
        strokeWidth?: number;
        fill?: string;
    }

    export interface GraticuleProps {
        stroke?: string;
        strokeWidth?: number;
    }

    export const ComposableMap: ComponentType<ComposableMapProps>;
    export const Geographies: ComponentType<GeographiesProps>;
    export const Geography: ComponentType<GeographyProps>;
    export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
    export const Marker: ComponentType<MarkerProps>;
    export const Annotation: ComponentType<AnnotationProps>;
    export const Line: ComponentType<LineProps>;
    export const Sphere: ComponentType<SphereProps>;
    export const Graticule: ComponentType<GraticuleProps>;
}
