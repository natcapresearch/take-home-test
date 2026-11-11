import { PageInfo } from "../../../common/__generated__/client-types";

export enum Direction {
    NEXT = "next",
    PREVIOUS = "previous",
}

export type MetricSort = "metric" | "concern_value" | "commodity_concern_value";
export interface PaginationProps extends PageInfo {
    loadNextPage: () => void;
    loadPreviousPage: () => void;
    currentPage: number;
    setCurrentPage: (page: number | ((prevPage: number) => number)) => void;
    showPagination: boolean;
}
