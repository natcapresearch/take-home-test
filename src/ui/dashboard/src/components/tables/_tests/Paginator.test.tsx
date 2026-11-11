import { fireEvent, render, screen } from "@testing-library/react";
import { MockBase } from "../../../helpers/testHelpers/testHelpers";
import Paginator from "../Paginator";

const loadNextPage = jest.fn();
const loadPreviousPage = jest.fn();
const tableName = "test_table";
const setCurrentPage = jest.fn();

interface PaginatorProps {
    currentPage?: number;
    showPagination?: boolean;
}

const renderPaginator = ({
    showPagination = true,
    currentPage = 1,
}: PaginatorProps) => {
    return render(
        <MockBase>
            <Paginator
                paginationProps={{
                    loadNextPage,
                    loadPreviousPage,
                    hasNextPage: true,
                    hasPreviousPage: true,
                    totalCount: 100,
                    currentPage: currentPage,
                    setCurrentPage: setCurrentPage,
                    showPagination: showPagination,
                }}
                tableName={tableName}
            />
        </MockBase>,
    );
};

describe("Paginator", () => {
    beforeEach(() => {
        setCurrentPage.mockClear();
        loadNextPage.mockClear();
        loadPreviousPage.mockClear();
    });

    it("Should render paginator is showPagination is true", async () => {
        renderPaginator({});
        expect(screen.getByTestId("paginator")).toBeDefined();
    });

    it("Should not render if showPagination is false", async () => {
        renderPaginator({ showPagination: false });
        expect(screen.queryByTestId("paginator")).toBeNull();
    });

    it("Go to next page should trigger fn", async () => {
        renderPaginator({ currentPage: 1 });

        const nextPage = screen.getByTestId("next-page");
        fireEvent.click(nextPage);

        expect(setCurrentPage).toHaveBeenCalledWith(expect.any(Function));
        const setPageFunction = setCurrentPage.mock.calls[0][0];
        const newPageNumber = setPageFunction(1);
        expect(newPageNumber).toBe(2);

        expect(loadNextPage).toHaveBeenCalled();
    });

    it("Go to previous page should trigger fn", async () => {
        renderPaginator({ currentPage: 2 });

        const previousPage = screen.getByTestId("previous-page");
        fireEvent.click(previousPage);

        expect(setCurrentPage).toHaveBeenCalledWith(expect.any(Function));
        const setPageFunction = setCurrentPage.mock.calls[0][0];
        const newPageNumber = setPageFunction(2);
        expect(newPageNumber).toBe(1);

        expect(loadPreviousPage).toHaveBeenCalled();
    });
});
