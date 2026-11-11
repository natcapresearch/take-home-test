/**
 * Environment variables read by the GraphQL server, with their defaults.
 *
 * - GRAPHQL_PORT: the port the server listens on (default 4000).
 * - BACKEND_API_URL: the REST backend the resolvers call (default
 *   http://localhost:8000).
 * - DEFAULT_ORG_UID: the organisation the dashboard opens when its URL names
 *   none. Exposed to the dashboard through `Query.config.defaultOrgUid`.
 * - LOG_LEVEL: pino log level (default "info").
 */
export const settings = {
    GRAPHQL_PORT: Number(process.env.GRAPHQL_PORT) || 4000,
    BACKEND_API_URL: process.env.BACKEND_API_URL || "http://localhost:8000",
    DEFAULT_ORG_UID: process.env.DEFAULT_ORG_UID || undefined,
    LOG_LEVEL: process.env.LOG_LEVEL || "info",
};
