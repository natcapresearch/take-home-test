import { InputMaybe, SortOrder } from "../../__generated__/resolvers-types";

export interface BackendPagination {
    nextCursor?: string;
    prevCursor?: string;
    totalCount: number;
}

export interface PaginationArgs {
    first?: InputMaybe<number>;
    after?: InputMaybe<string>;
    before?: InputMaybe<string>;
}

export interface SortArgs {
    sortOn?: InputMaybe<string>;
    sortOrder?: InputMaybe<SortOrder>;
}

export function indexCursorFromIndex(index: number): string {
    return Buffer.from(index.toString()).toString("base64");
}

export function paginationToPageInfo(
    edges: { cursor: string }[],
    pagination: BackendPagination,
) {
    return {
        hasNextPage:
            !!pagination.nextCursor && pagination.totalCount > edges.length,
        hasPreviousPage:
            !!pagination.prevCursor && pagination.totalCount > edges.length,
        startCursor: edges.at(0)?.cursor,
        endCursor: edges.at(-1)?.cursor,
        totalCount: pagination.totalCount,
    };
}

/**
 * The page cursors from the backend's own natcap-next-cursor /
 * natcap-prev-cursor headers, NOT paginationToPageInfo, which derives them
 * from `edges`. For rows with no per-row cursor the edge cursors are Relay
 * node ids; feeding one back as ?after= is not a cursor the backend can
 * decode and the next page comes back empty.
 */
export function pageInfoFromBackendPagination(pagination: BackendPagination) {
    return {
        hasNextPage: !!pagination.nextCursor,
        hasPreviousPage: !!pagination.prevCursor,
        startCursor: pagination.prevCursor,
        endCursor: pagination.nextCursor,
        totalCount: pagination.totalCount,
    };
}
