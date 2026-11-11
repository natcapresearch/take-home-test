import type { ApolloServerPlugin } from "@apollo/server";
import { GraphQLRequest } from "@apollo/server";
import { OperationDefinitionNode } from "graphql";
import { pino } from "pino";
import { v4 as uuidv4 } from "uuid";
import { settings } from "./settings";

export const logger = pino({
    level: settings.LOG_LEVEL,
    redact: ["auth", "password", "token", "email"],
});

const ALLOWED_MUTATION_PARAMS = [
    "orgUuid", // we want to know who is doing a mutation to aid debugging.
];

export function cleanParameters(
    parameters: GraphQLRequest["variables"] | undefined,
    operationKind: string,
): GraphQLRequest["variables"] | undefined {
    // Mutations are much more likely to have PII in parameters so we only allow a
    // few known parameters to be logged and we redact the rest.
    if (parameters && operationKind === "mutation") {
        const result = { ...parameters };
        Object.keys(result).forEach((variable) => {
            if (!ALLOWED_MUTATION_PARAMS.includes(variable)) {
                result[variable] = "[REDACTED]";
            }
        });
        return result;
    }
    // for anything else we rely on the pino redaction above as this keeps it consistent
    // with any logging used elsewhere in the application.
    return parameters;
}

// Implementing a custom ApolloServerPlugin so that we can log graphql requests
// This has two advantages: 1: we can filter parameters using our own logic, 2: we can
// use the pino object logging for parameters.
export function ApolloLoggerPlugin(): ApolloServerPlugin {
    return {
        async serverWillStart() {
            logger.info("Starting GraphQL Server.");
            return {
                async serverWillStop() {
                    logger.info("Stopping GraphQL Server.");
                },
            };
        },
        async requestDidStart() {
            // Log a correlation id for the request.
            const requestUuid = uuidv4();
            const requestLogger = logger.child({ requestUuid });

            // Record the start time so we can work out the duration later.
            const startTime = Date.now();

            requestLogger.debug("Request started.");
            return {
                async didResolveSource({ source }: { source: string }) {
                    requestLogger.trace(source);
                },
                async didResolveOperation({
                    operation,
                    operationName,
                    request: { variables },
                }: {
                    operation?: OperationDefinitionNode;
                    operationName?: string | null;
                    request: {
                        variables?: GraphQLRequest["variables"] | undefined;
                    };
                }) {
                    const kind = operation?.operation || "operation";
                    const name = operationName || "unnamed";

                    const params = cleanParameters(variables, kind);

                    requestLogger.info({
                        msg: `Started ${kind} ${name} with params`,
                        ...params,
                    });
                },
                async didEncounterErrors({
                    errors,
                }: {
                    errors: ReadonlyArray<Error>;
                }) {
                    if (errors) {
                        requestLogger.error(errors, "Request errors");
                    }
                },
                async parsingDidStart() {
                    requestLogger.debug("Parsing source...");

                    return async (err?: Error) => {
                        if (err) {
                            requestLogger.error(err, "Request parsing error");
                        } else {
                            requestLogger.debug("Parsing complete");
                        }
                    };
                },
                async validationDidStart() {
                    requestLogger.debug("Checking GraphQL document...");

                    return async (err?: ReadonlyArray<Error>) => {
                        if (err) {
                            requestLogger.error(
                                err,
                                "Request validation error",
                            );
                        } else {
                            requestLogger.debug(
                                "Validation complete. Document cached.",
                            );
                        }
                    };
                },
                async executionDidStart({
                    operation,
                    operationName,
                }: {
                    operation?: OperationDefinitionNode;
                    operationName?: string | null;
                }) {
                    const typeName = operation?.operation || "operation";

                    requestLogger.debug(
                        `Executing ${typeName} ${operationName}...`,
                    );
                },

                async willSendResponse({
                    operation,
                    operationName,
                }: {
                    operation?: OperationDefinitionNode;
                    operationName?: string | null;
                }) {
                    const kind = operation?.operation || "operation";
                    const name = operationName || "";
                    const duration = Date.now() - startTime;

                    requestLogger.info(
                        `Completed ${kind} ${name} in ${duration}ms`,
                    );
                },
            };
        },
    };
}
