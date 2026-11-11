import { createProxyMiddleware } from "http-proxy-middleware";

// For whatever reason it appears Parcel *only* supports CJS-style exports for
// this specific file.
module.exports = function (app) {
    // When running in docker-compose, the GraphQL service is available via the
    // auto-setup network host. Otherwise, assume it is running on localhost.
    const host = process.env.IN_DOCKER === "true" ? "graphql" : "localhost";

    app.use(
        "/api",
        createProxyMiddleware({ target: `http://${host}:4000/api` }),
    );
};
