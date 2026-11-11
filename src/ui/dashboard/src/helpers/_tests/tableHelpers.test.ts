import { SortOrder } from "../../../../common/__generated__/client-types";
import { getNewSortDirection, getPasteSortDirection } from "../tableHelpers";

describe("tableHelpers - getPasteSortDirection", () => {
    const columnName = "test column";

    it("Should return the sortorder correctly for desc", () => {
        const sortDirection = SortOrder.Desc;
        const sortOrder = {
            columnName: columnName,
            sortDirection: sortDirection,
        };
        expect(getPasteSortDirection(columnName, sortOrder)).toBe("descending");
    });

    it("Should return the sortorder correctly for asc", () => {
        const sortDirection = SortOrder.Asc;
        const sortOrder = {
            columnName: columnName,
            sortDirection: sortDirection,
        };
        expect(getPasteSortDirection(columnName, sortOrder)).toBe("ascending");
    });

    it("Should return none if there isn't a sortorder", () => {
        const sortOrder = {
            columnName: "other column",
            sortDirection: SortOrder.Desc,
        };
        expect(getPasteSortDirection(columnName, sortOrder)).toBe("none");
    });
});

describe("tableHelpers - getNewSortDirection", () => {
    const columnName = "test column";

    it("Should return ascending if currently descending", () => {
        const sortOrder = {
            columnName: columnName,
            sortDirection: SortOrder.Desc,
        };
        expect(getNewSortDirection(columnName, sortOrder)).toBe(SortOrder.Asc);
    });

    it("Should return descending if currently ascending", () => {
        const sortOrder = {
            columnName: columnName,
            sortDirection: SortOrder.Asc,
        };
        expect(getNewSortDirection(columnName, sortOrder)).toBe(SortOrder.Desc);
    });
});
