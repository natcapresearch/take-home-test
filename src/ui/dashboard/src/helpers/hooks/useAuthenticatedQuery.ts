import { OperationVariables, QueryHookOptions, useQuery } from "@apollo/client";
import { TypedDocumentNode } from "@graphql-typed-document-node/core";
import { useState } from "react";
import { Direction } from "../../types/tableTypes";

interface PaginationVariables extends OperationVariables {
    after?: string;
    before?: string;
}

export default function useAuthenticatedQuery<
    TData,
    TVariables extends OperationVariables = OperationVariables,
>(
    query: TypedDocumentNode<TData, TVariables>,
    options: QueryHookOptions<TData, TVariables> = {},
) {
    // TODO: This should be removed and replaced with the loadXPage being async, and returning the call to loadPage,
    // so the component can manage its own paginaton state rather than it being done here.
    const [isPaginating, setIsPaginating] = useState(false);

    const response = useQuery<TData, TVariables>(query, {
        errorPolicy: "all",
        ...options,
    });

    const isShowingPreviousData =
        response.loading && response.previousData != null;
    const displayedData = isShowingPreviousData
        ? response.previousData
        : response.data;

    const loadPage = async (direction: Direction, cursor: string) => {
        setIsPaginating(true);
        const variables: PaginationVariables =
            direction === "next" ? { after: cursor } : { before: cursor };

        try {
            await response.fetchMore({
                variables,
                updateQuery: (prev, { fetchMoreResult }) => {
                    if (!fetchMoreResult) return prev;
                    return fetchMoreResult;
                },
            });
        } finally {
            setIsPaginating(false);
        }
    };

    const loadNextPage = (endCursor: string) => {
        loadPage(Direction.NEXT, endCursor);
    };

    const loadPreviousPage = (startCursor: string) => {
        loadPage(Direction.PREVIOUS, startCursor);
    };

    return {
        ...response,
        displayedData,
        isShowingPreviousData,
        loadPreviousPage,
        loadNextPage,
        loading: response.loading || isPaginating,
    };
}
