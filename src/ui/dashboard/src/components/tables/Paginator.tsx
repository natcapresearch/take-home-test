import {
    Pagination,
    PaginationArrow,
    PaginationItems,
    PaginationLabel,
} from "@twilio-paste/core";
import { defaultItemsPerPage } from "../../helpers/tableHelpers";
import { PaginationProps } from "../../types/tableTypes";

interface PaginatorProps {
    paginationProps: PaginationProps;
    tableName: string;
    itemsPerPage?: number;
}

const Paginator = ({
    paginationProps,
    itemsPerPage = defaultItemsPerPage,
}: PaginatorProps) => {
    const {
        totalCount,
        hasNextPage,
        hasPreviousPage,
        loadNextPage,
        loadPreviousPage,
        currentPage,
        setCurrentPage,
        showPagination,
    } = paginationProps;

    if (!showPagination) {
        return;
    }

    const totalPages = Math.ceil((totalCount as number) / itemsPerPage);

    const goToNextPage = () => {
        setCurrentPage((page) => Math.min(page + 1, totalPages));
        loadNextPage();
    };

    const goToPreviousPage = () => {
        setCurrentPage((page) => Math.max(page - 1, 1));
        loadPreviousPage();
    };

    return (
        <Pagination label="pagination" data-testid="paginator">
            <PaginationItems>
                {/* Paste renders the arrows as untyped buttons, which default
                to submit: inside a form, Enter in any input would click one
                and submit the form. Paste's `disabled` only hides the arrow,
                so it does not stop that either. */}
                <PaginationArrow
                    type="button"
                    label="previous-page"
                    variant="back"
                    onClick={goToPreviousPage}
                    data-testid="previous-page"
                    disabled={!hasPreviousPage}
                />

                <PaginationLabel>
                    {currentPage} of {totalPages}
                </PaginationLabel>

                <PaginationArrow
                    type="button"
                    label="next-page"
                    variant="forward"
                    onClick={goToNextPage}
                    data-testid="next-page"
                    disabled={!hasNextPage}
                />
            </PaginationItems>
        </Pagination>
    );
};

export default Paginator;
