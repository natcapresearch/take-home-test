import { SortDirection } from "@twilio-paste/core";
import { SortOrder } from "../../../common/__generated__/client-types";

export interface TableSort {
    columnName: string;
    sortDirection: SortOrder;
}

export const getPasteSortDirection = (
    columnName: string,
    tableSort: TableSort,
): SortDirection => {
    if (tableSort.columnName !== columnName) {
        return "none";
    }

    if (tableSort.sortDirection === SortOrder.Asc) {
        return "ascending";
    }

    return "descending";
};

export const getNewSortDirection = (
    columnName: string,
    tableSort: TableSort,
): SortOrder => {
    return tableSort.columnName === columnName &&
        tableSort.sortDirection === SortOrder.Desc
        ? SortOrder.Asc
        : SortOrder.Desc;
};

export const defaultItemsPerPage = 50;
