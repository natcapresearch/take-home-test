import { GraphQLError } from "graphql";
import { ErrorCode, ResultError } from "../__generated__/resolvers-types";
import { logger } from "./logging";

export function base64Encode(type: string, id: string): string {
    return Buffer.from(`${type}:${id}`).toString("base64");
}

/**
 * The default GraphQL error type is poorly typed and the RESTDataSource doesn't
 * provide a type for the extensions it adds. This type corrects that.
 */
type ExtendedGraphQLError = GraphQLError & {
    extensions: {
        code?: string;
        response?: {
            url?: string;
            status?: number;
            statusText?: string;
            body?: {
                detail?: object;
                status?: "error" | "success";
                status_code?: number;
                body?: object;
                [key: string]: unknown;
            };
        };
    };
};

/**
 * Normalize an unknown thrown value into a standard Error or ExtendedGraphQLError.
 */
function errorFromCatch(unknownError: unknown): ExtendedGraphQLError | Error {
    if (unknownError instanceof GraphQLError)
        return unknownError as ExtendedGraphQLError;
    if (unknownError instanceof Error) return unknownError;
    return new Error(`${unknownError}`);
}

const ERROR_STATUS_TO_CODE: Record<string, ErrorCode> = {
    "400": ErrorCode.BadRequest,
    "401": ErrorCode.Unauthorised,
    "403": ErrorCode.Forbidden,
    "404": ErrorCode.NotFound,
    "405": ErrorCode.MethodNotAllowed,
    "406": ErrorCode.NotAcceptable,
    "409": ErrorCode.Conflict,
    "422": ErrorCode.UnprocessableEntity,
    "429": ErrorCode.TooManyRequests,
    "500": ErrorCode.InternalServerError,
    "501": ErrorCode.NotImplemented,
    "502": ErrorCode.BadGateway,
    "503": ErrorCode.ServiceUnavailable,
    "504": ErrorCode.GatewayTimeout,
};

const statusFrom = (err: ExtendedGraphQLError | Error): number | undefined =>
    err instanceof GraphQLError
        ? (err as ExtendedGraphQLError).extensions?.response?.status
        : undefined;

function statusToErrorCode(code: unknown): ErrorCode {
    return ERROR_STATUS_TO_CODE[`${code ?? ""}`] ?? ErrorCode.Unknown;
}

function errorToErrorCode(error: ExtendedGraphQLError | Error): ErrorCode {
    return statusToErrorCode(statusFrom(error));
}

/** Only 5XX-style errors are logged. */
function logError(error: ExtendedGraphQLError | Error): void {
    if ((statusFrom(error) ?? 0) >= 500) logger.error(error);
}

function errorDetailFromBackendError(
    error: ExtendedGraphQLError | Error,
): { detail: unknown } | null {
    if (!(error instanceof GraphQLError)) return null;
    const detail = (error as ExtendedGraphQLError).extensions?.response?.body
        ?.detail;
    return detail ? { detail } : null;
}

/**
 * Convert an unknown thrown value into a schema-compatible ResultError.
 * - Normalizes the error.
 * - Maps HTTP status to ErrorCode.
 * - Logs 5xx errors.
 * - Propagates backend `detail` if present.
 */
function schemaErrorFromCatch(unknownError: unknown): ResultError {
    const normalizedError = errorFromCatch(unknownError);
    const code = errorToErrorCode(normalizedError);
    logError(normalizedError);
    const detail = errorDetailFromBackendError(normalizedError);
    const message =
        detail?.detail && typeof detail.detail === "string"
            ? `${normalizedError.message}: ${detail.detail}`
            : normalizedError.message;
    return {
        __typename: "ResultError",
        message,
        code,
        ...detail,
    };
}

/** Construct a ResultError with NotFound code and a custom message. */
export function schemaErrorFromNotFound(message: string): ResultError {
    return {
        __typename: "ResultError",
        message,
        code: ErrorCode.NotFound,
    };
}

/** Construct a ResultError for a missing required field. */
export function schemaErrorFromMissingField(field: string): ResultError {
    return schemaErrorFromNotFound(`Missing required field: ${field}`);
}

function isResultError(value: unknown): value is ResultError {
    return (
        !!value &&
        typeof value === "object" &&
        "__typename" in value &&
        (value as { __typename?: unknown }).__typename === "ResultError"
    );
}

/**
 * Enumeration of supported error-handling policies for `asResult`.
 *
 * - RESULT_ERROR: Wrap errors as a GraphQL `ResultError` object.
 * - NULL: Return `null` on error.
 * - EMPTY_LIST: Return an empty list on error (for list-shaped results).
 * - THROW: Re-throw the error after normalization.
 */
export enum OnErrorPolicy {
    ResultError = "RESULT_ERROR",
    Null = "NULL",
    EmptyList = "EMPTY_LIST",
    Throw = "THROW",
}

/**
 * Utility type that makes all properties of an input shape required
 * and excludes `null`, `undefined` and empty string `""` from each value.
 */
type NonEmpty<InputShape> = {
    [Key in keyof InputShape]-?: Exclude<
        InputShape[Key],
        null | undefined | ""
    >;
};

type WithRequiredResult<
    ErrorPolicy extends OnErrorPolicy,
    SuccessType,
> = ErrorPolicy extends OnErrorPolicy.ResultError
    ? SuccessType | ResultError
    : ErrorPolicy extends OnErrorPolicy.Null
    ? SuccessType | null
    : SuccessType;

/**
 * Validate a fields object and ensure that none of its properties are
 * `null`, `undefined` or an empty string `""`.
 */
function expectFields<F extends Record<string, unknown>>(obj: F): NonEmpty<F> {
    for (const [name, value] of Object.entries(obj)) {
        if (value === undefined || value === null || value === "") {
            throw schemaErrorFromMissingField(name);
        }
    }
    return obj as NonEmpty<F>;
}

type AsResultConfig<
    SuccessType,
    Policy extends OnErrorPolicy,
    InputShape extends Record<string, unknown> | undefined,
> = {
    onError?: Policy;
} & (InputShape extends Record<string, unknown>
    ? {
          requiredFields: InputShape;
          resolver: (narrowed: NonEmpty<InputShape>) => Promise<SuccessType>;
      }
    : {
          resolver: () => Promise<SuccessType>;
          requiredFields?: undefined;
      });

/**
 * Unified executor that wraps async resolver logic with:
 * - Optional required-field validation.
 * - Standardised error-to-ResultError mapping.
 * - Configurable error-handling policy.
 *
 * ```ts
 * return asResult({
 *   requiredFields: { orgUid: parent.uuid },
 *   resolver: async ({ orgUid }) => loadOrg(orgUid),
 * });
 * ```
 */
export async function asResult<
    SuccessType,
    Policy extends OnErrorPolicy = OnErrorPolicy.ResultError,
    InputShape extends Record<string, unknown> | undefined = undefined,
>(
    config: AsResultConfig<SuccessType, Policy, InputShape>,
): Promise<WithRequiredResult<Policy, SuccessType>> {
    const policy = config.onError ?? OnErrorPolicy.ResultError;

    try {
        if (config.requiredFields) {
            const narrowed = expectFields(config.requiredFields);
            const result = await config.resolver(narrowed);
            return result as WithRequiredResult<Policy, SuccessType>;
        }

        const result = await config.resolver();
        return result as WithRequiredResult<Policy, SuccessType>;
    } catch (caught) {
        if (policy === OnErrorPolicy.Throw) {
            throw caught instanceof Error ? caught : new Error(String(caught));
        }

        if (policy === OnErrorPolicy.Null) {
            return null as WithRequiredResult<Policy, SuccessType>;
        }

        if (policy === OnErrorPolicy.EmptyList) {
            return [] as WithRequiredResult<Policy, SuccessType>;
        }

        const val = isResultError(caught)
            ? caught
            : schemaErrorFromCatch(caught);
        return val as WithRequiredResult<Policy, SuccessType>;
    }
}
