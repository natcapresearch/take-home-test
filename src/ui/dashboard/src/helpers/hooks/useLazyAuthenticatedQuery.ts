import {
    ApolloError,
    OperationVariables,
    QueryHookOptions,
    useLazyQuery,
} from "@apollo/client";
import { TypedDocumentNode } from "@graphql-typed-document-node/core";
import { useCallback } from "react";

type LazyQueryResult<TData> = {
    loading: boolean;
    data?: TData;
    error?: ApolloError;
};

export default function useLazyAuthenticatedQuery<
    TData,
    TVariables extends OperationVariables = OperationVariables,
>(
    query: TypedDocumentNode<TData, TVariables>,
    options: QueryHookOptions<TData, TVariables> = {},
): [
    (variables?: TVariables) => Promise<TData | undefined>,
    LazyQueryResult<TData>,
] {
    const [executeQuery, response] = useLazyQuery<TData, TVariables>(query, {
        errorPolicy: "all",
        ...options,
    });

    const fetchData = useCallback(
        async (variables?: TVariables): Promise<TData | undefined> => {
            const result = await executeQuery({ variables });
            return result.data;
        },
        [executeQuery],
    );

    return [
        fetchData,
        {
            loading: response.loading,
            data: response.data,
            error: response.error,
        },
    ];
}
