import { ResultError } from "../../../common/__generated__/client-types";
import { getErrorMessage } from "./errorHelpers";

export const UNKNOWN_MUTATION_ERROR = "Something went wrong, please try again.";

/** The parts of an Apollo mutation result that `runMutation` inspects. */
interface MutationResponse<TData> {
    data?: TData | null;
    errors?: ReadonlyArray<{ message: string }>;
}

/**
 * The root field of a mutation result. Every mutation document selects exactly
 * one root field, so this is the one key besides `__typename`.
 */
export type MutationField<TData> = Exclude<keyof TData, "__typename">;

/** A mutation field's value with null and `ResultError` removed. */
export type MutationSuccess<V> = Exclude<
    NonNullable<V>,
    { __typename?: "ResultError" }
>;

interface MutationFailure {
    success: false;
    error: string;
    /** Set when the failure was a `ResultError`, for callers that map its `code` or `detail`. */
    resultError?: ResultError;
}

export type MutationOutcome<T> = { success: true; data: T } | MutationFailure;

/** The success value of a mutation whose result type is `TData`. */
export type MutationData<TData> = MutationSuccess<TData[MutationField<TData>]>;

/** The outcome of running a mutation whose result type is `TData`. */
export type MutationOutcomeOf<TData> = MutationOutcome<MutationData<TData>>;

/** A `MutationOutcome` for callers that do not need the success data. */
export type MutationStatus = { success: true } | MutationFailure;

/**
 * Turns a `MutationOutcome` into an error message prefixed with
 * `failurePrefix`, or null on success.
 */
export function errorMessageFromOutcome<T>(
    outcome: MutationOutcome<T>,
    failurePrefix: string,
): string | null {
    return outcome.success ? null : `${failurePrefix}: ${outcome.error}`;
}

function isResultError(value: unknown): value is ResultError {
    return (
        typeof value === "object" &&
        value !== null &&
        "__typename" in value &&
        value.__typename === "ResultError"
    );
}

function rootFieldValue<TData>(data: TData | null | undefined) {
    if (!data) {
        return undefined;
    }
    return Object.entries(data).find(([key]) => key !== "__typename")?.[1];
}

/**
 * Runs a mutation and normalises every way it can fail into
 * `{ success: false, error }`:
 *
 * - the request throws (network or runtime error);
 * - the response carries GraphQL `errors` (with `errorPolicy: "all"` these do
 *   not throw, and the field comes back null);
 * - the root field is null or undefined;
 * - the root field is a `ResultError`.
 *
 * On success, `data` is the root field's value narrowed to its success
 * type(s). `useAuthenticatedMutation` calls this for every mutation.
 *
 * @param operationName Identifies the mutation in error messages.
 * @param request Calls the mutate function.
 */
export async function runMutation<TData>(
    operationName: string,
    request: () => Promise<MutationResponse<TData>>,
): Promise<MutationOutcomeOf<TData>> {
    const fail = (
        error: string,
        cause: unknown,
        resultError?: ResultError,
    ): MutationFailure => {
        console.error(`${operationName} failed: ${error}`, cause);
        return { success: false, error, resultError };
    };

    try {
        const response = await request();
        const value = rootFieldValue(response.data);

        if (isResultError(value)) {
            return fail(
                value.message || UNKNOWN_MUTATION_ERROR,
                new Error(`${operationName}: ${value.message}`),
                value,
            );
        }

        const graphQLError = response.errors?.[0]?.message;
        if (graphQLError) {
            return fail(
                graphQLError,
                new Error(`${operationName}: ${graphQLError}`),
            );
        }

        if (value == null) {
            return fail(
                UNKNOWN_MUTATION_ERROR,
                new Error(`${operationName}: no data returned`),
            );
        }

        return {
            success: true,
            data: value as MutationData<TData>,
        };
    } catch (err) {
        return fail(getErrorMessage(err) || UNKNOWN_MUTATION_ERROR, err);
    }
}
