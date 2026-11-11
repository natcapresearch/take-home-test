import {
    Error,
    Maybe,
    PageInfo,
} from "../../../common/__generated__/client-types";

type Edge<T> = {
    node?: T;
    cursor: string;
};

type Connection<T> = {
    pageInfo: PageInfo;
    edges?: Maybe<Maybe<Edge<Maybe<T>>>[]>;
};

/**
 * Extracts the innert nodes from any Connection object that has pageInfo and edges.
 *
 * @param connection The connection to extract nodes from
 * @returns The nodes from the connection
 */
export function nodesFromConnection<T>(
    connection?: Maybe<Connection<T> | Error>,
): T[] {
    if (!connection) {
        return [];
    }

    // If it don't quack like a connection, it ain't a connection
    if (!("pageInfo" in connection)) {
        return [];
    }

    if (!connection.edges) {
        return [];
    }

    return connection.edges
        .filter((edge): edge is Edge<T> => !!edge)
        .map((edge) => edge.node)
        .filter((node): node is T => !!node);
}

export function valueFromResult<
    V extends { __typename?: string },
    T extends string = string,
>(
    typename: T,
    value?: V | { __typename?: string } | null,
): Extract<V, { __typename?: T }> | undefined {
    if (!value) {
        return undefined;
    }

    if (value.__typename !== typename) {
        return undefined;
    }

    return value as Extract<V, { __typename?: T }>;
}

export function valuesFromResultArray<T extends { __typename?: string }>(
    typename: string,
    list?: Maybe<ReadonlyArray<Maybe<{ __typename?: string }>>>,
): T[] {
    return arrayFromMaybe(list)
        .map((v) => valueFromResult<T>(typename, v))
        .filter(
            (v): v is Extract<T, { __typename?: string }> => v != undefined,
        );
}

/**
 * Normalises a GraphQL list that may contain nulls at both the array
 * and item level into a safe, non-nullable array.
 *
 * This is useful because GraphQL codegen often types list fields as
 * `Maybe<Maybe<T>[]>`, which means both the array itself and each
 * element may be `null` or `undefined`.
 *
 * @param list The list to normalise (possibly null or containing nulls).
 * @returns A new array containing only defined items.
 */
export function arrayFromMaybe<T>(
    list?: Maybe<ReadonlyArray<Maybe<T>>> | ReadonlyArray<Maybe<T>> | null,
): T[] {
    return (list ?? []).filter((x): x is T => x != null);
}

/**
 * Normalises a GraphQL list of strings that may contain nulls/undefined
 * into a safe `string[]`, discarding any non-string values.
 *
 * Useful for fields typed like `Maybe<Maybe<string>[]>`.
 */
export function stringArrayFromMaybe(
    list?:
        | Maybe<ReadonlyArray<Maybe<string>>>
        | ReadonlyArray<Maybe<string>>
        | null,
): string[] {
    return (list ?? []).filter((x): x is string => typeof x === "string");
}
