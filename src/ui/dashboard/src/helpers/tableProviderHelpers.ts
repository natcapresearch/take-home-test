import { Dispatch, SetStateAction, useCallback, useState } from "react";
import { PageInfo } from "../../../common/__generated__/client-types";
import { PaginationProps } from "../types/tableTypes";
import { shallowEqual, typedKeys } from "./objectHelpers";
import { getNewSortDirection, TableSort } from "./tableHelpers";

/**
 * Represents the minimal shape of a Twilio Paste multiselect combobox state
 * needed to clear it. `never[]` (rather than a concrete item type) lets this
 * accept multiselect states regardless of what item shape they hold.
 */
interface MultiSelectState {
    setSelectedItems: (items: never[]) => void;
}

/**
 * React hook that returns a stable `applyFilters` function for updating
 * a table's filter state based on selected multiselect values.
 *
 * The hook merges:
 *  - The previous filter state (`prev`)
 *  - The current selected values from multiselects (`selectStates`)
 *  - Any optional overrides (`overrides`)
 *
 * It uses a shallow equality check (`shallowEqual`) to detect when the
 * resulting `next` filter object is structurally identical to the previous
 * state. If so, it returns the existing state instead of setting a new one.
 *
 * This optimization prevents unnecessary re-renders and stops infinite
 * render loops that can occur when a component re-applies identical filters
 * inside a `useEffect` (e.g., when `applyFilters()` is called automatically
 * on mount or after user input).
 *
 * The optional `onApply` callback is only fired when the filter state
 * actually changes.
 *
 * @template TFilter - Any object-shaped filter state.
 * @param setFilterState - React state setter for the filter object.
 * @param selectStates - Current selected filter values (e.g. from multiselects). Can be partial.
 * @param onApply - Optional callback executed after filters are applied (and changed).
 * @returns A memoized function that applies filters.
 */
export function useApplyFilters<TFilter extends object>(
    setFilterState: Dispatch<SetStateAction<TFilter>>,
    selectStates: Partial<TFilter>,
    onApply?: () => void,
) {
    return useCallback(
        (overrides?: Partial<TFilter>) => {
            setFilterState((prev) => {
                const next = { ...prev, ...selectStates, ...(overrides ?? {}) };

                if (shallowEqual(prev, next)) return prev;

                onApply?.();
                return next;
            });
        },
        [setFilterState, selectStates, onApply],
    );
}

/**
 * React hook that provides a stable `handleSort` function for managing
 * column sorting logic in table components.
 *
 * Determines the next sort direction for a given column and updates
 * the table's sort state accordingly.
 *
 * @param sortState - Current sorting state of the table.
 * @param setSortState - React state setter for updating the table's sort state.
 * @returns A memoized function to toggle sort direction for a column.
 */
export function useHandleSort(
    sortState: TableSort,
    setSortState: (
        updater: TableSort | ((prev: TableSort) => TableSort),
    ) => void,
    onSort?: () => void,
) {
    const handleSort = useCallback(
        (columnName: string) => {
            const newSortDirection = getNewSortDirection(columnName, sortState);
            setSortState({ columnName, sortDirection: newSortDirection });
            onSort?.();
        },
        [sortState, setSortState, onSort],
    );

    return handleSort;
}

/**
 * React hook that returns a `clearFilters` function to reset selected filters
 * and clear associated multiselect combobox states.
 *
 * It:
 *  - Clears all provided multiselect states.
 *  - Resets all filter keys **not** listed in `preserveKeys`.
 *      • Array values are reset to [].
 *      • Non-array values are reset to an empty string "".
 *  - Preserves only the specified keys as-is (useful for free-text search).
 *
 * @template TFilter - Any object-shaped filter state.
 * @param setFilterState - React state setter for the filter object.
 * @param multiSelects - Map of multiselects to clear; each must implement `setSelectedItems`.
 * @param preserveKeys - Keys in the filter state to preserve as-is.
 * @returns A memoized function that clears all filters except those preserved.
 */
export function useClearFilters<TFilter extends object>(
    setFilterState: (updater: TFilter | ((prev: TFilter) => TFilter)) => void,
    multiSelects: Record<string, MultiSelectState>,
    preserveKeys?: (keyof TFilter)[],
) {
    const clearFilters = useCallback(() => {
        Object.values(multiSelects).forEach((ms) => ms.setSelectedItems([]));

        setFilterState((prev) => {
            const next = { ...prev };

            typedKeys(prev).forEach((k) => {
                if (preserveKeys?.includes(k)) {
                    next[k] = prev[k];
                } else {
                    const value = prev[k];
                    next[k] = (
                        Array.isArray(value) ? [] : ""
                    ) as TFilter[typeof k];
                }
            });

            return next;
        });
    }, [multiSelects, preserveKeys, setFilterState]);

    return clearFilters;
}

/**
 * Build a shape of only `selectedItems` from a map of multiselect states.
 *
 * @template T - Map of keys to objects that contain a `selectedItems` field
 * (item shape varies per state, e.g. `string` or `MultiSelectFilterItem`).
 * @param states - Record of multiselect states.
 * @returns A record mapping each key to its `selectedItems` array.
 */
export function buildSelectedItemsMap<
    T extends Record<string, { selectedItems: unknown[] }>,
>(states: T) {
    const entries = typedKeys(states).map((k) => [k, states[k].selectedItems]);
    return Object.fromEntries(entries) as {
        [K in keyof T]: T[K]["selectedItems"];
    };
}

/**
 * Returns true if every entry in the given selected-items map is empty.
 *
 * Intended to quickly derive `isFilterEmpty` from a `buildSelectedItemsMap` result.
 *
 * @param selected - A record of arrays (e.g., `{ regions: [], tags: [] }`).
 * @returns `true` if all arrays are empty; otherwise `false`.
 */
export function isSelectedItemsEmpty(
    selected: Record<string, unknown[]>,
): boolean {
    for (const k in selected) {
        if ((selected[k]?.length ?? 0) > 0) return false;
    }
    return true;
}

/**
 * Updates a single `PaginationProps` state from a GraphQL `PageInfo`.
 *
 * - Only writes when cursors/flags/count actually change (avoids loops).
 * - Also wires `showPagination`, `loadNextPage`, and `loadPreviousPage`.
 *
 * @param setPagination React state setter for the full PaginationProps object.
 * @param pageInfo GraphQL PageInfo slice (cursors, flags, totalCount).
 * @param pageSize Used to compute `showPagination`.
 * @param loadNextPage Function that fetches the next page when given `endCursor`.
 * @param loadPreviousPage Function that fetches the previous page when given `startCursor`.
 */
export function syncPaginationFromPageInfo(
    setPagination: Dispatch<SetStateAction<PaginationProps>>,
    pageInfo: PageInfo,
    pageSize: number,
    loadNextPage: (cursor: string) => void,
    loadPreviousPage: (cursor: string) => void,
) {
    setPagination((prev) => {
        const same =
            prev?.startCursor === pageInfo.startCursor &&
            prev?.endCursor === pageInfo.endCursor &&
            prev?.hasNextPage === pageInfo.hasNextPage &&
            prev?.hasPreviousPage === pageInfo.hasPreviousPage &&
            prev?.totalCount === (pageInfo.totalCount ?? undefined);

        if (same) {
            return prev;
        }

        return {
            ...prev,
            startCursor: pageInfo.startCursor,
            endCursor: pageInfo.endCursor,
            hasNextPage: pageInfo.hasNextPage,
            hasPreviousPage: pageInfo.hasPreviousPage,
            totalCount: pageInfo.totalCount,
            showPagination: (pageInfo.totalCount ?? 0) > pageSize,
            loadNextPage: () => {
                if (pageInfo.endCursor) {
                    loadNextPage(pageInfo.endCursor);
                }
            },
            loadPreviousPage: () => {
                if (pageInfo.startCursor) {
                    loadPreviousPage(pageInfo.startCursor);
                }
            },
        };
    });
}

/**
 * Pages an in-memory list for `Paginator`, which otherwise expects a
 * cursor-paginated query behind it.
 *
 * The page is clamped to the list's current length, so removing items from
 * the last page moves back a page rather than showing an empty one.
 */
export function useClientSidePagination<TItem>(
    items: TItem[],
    pageSize: number,
): { pageItems: TItem[]; paginationProps: PaginationProps } {
    const [requestedPage, setRequestedPage] = useState(1);
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    const currentPage = Math.min(requestedPage, totalPages);

    const setCurrentPage: PaginationProps["setCurrentPage"] = (page) => {
        setRequestedPage((prev) => {
            const clampedPrev = Math.min(prev, totalPages);
            return typeof page === "function" ? page(clampedPrev) : page;
        });
    };

    return {
        pageItems: items.slice(
            (currentPage - 1) * pageSize,
            currentPage * pageSize,
        ),
        paginationProps: {
            totalCount: items.length,
            hasNextPage: currentPage < totalPages,
            hasPreviousPage: currentPage > 1,
            // Paginator moves the page through setCurrentPage; there is no
            // query to fetch the next page from.
            loadNextPage: () => {},
            loadPreviousPage: () => {},
            currentPage,
            setCurrentPage,
            showPagination: items.length > pageSize,
        },
    };
}
