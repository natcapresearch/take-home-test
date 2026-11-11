import { ApolloServer } from "@apollo/server";
import { ApolloServerPluginDrainHttpServer } from "@apollo/server/plugin/drainHttpServer";
import { ApolloServerPluginLandingPageLocalDefault } from "@apollo/server/plugin/landingPage/default";
import { expressMiddleware } from "@as-integrations/express5";
import cors from "cors";
import express from "express";
import { readFileSync } from "fs";
import gql from "graphql-tag";
import http from "http";
import { AddressInfo } from "net";
import { BackendApi } from "./dataSources/backendApi";
import { ApolloLoggerPlugin } from "./logging";
import { resolvers } from "./resolvers";
import { settings } from "./settings";

export interface Context {
    dataSources: {
        backendApi: BackendApi;
    };
}

const typeDefs = gql(
    readFileSync(`src/graphql/resources/schema.graphql`, {
        encoding: "utf-8",
    }),
);

const app = express();
const httpServer = http.createServer(app);

const server = new ApolloServer<Context>({
    typeDefs,
    resolvers,
    introspection: true,
    plugins: [
        ApolloServerPluginDrainHttpServer({ httpServer }),
        ApolloServerPluginLandingPageLocalDefault({ footer: false }),
        ApolloLoggerPlugin(),
    ],
});

await server.start();

app.use(
    "/api/graphql",
    cors<cors.CorsRequest>({
        // Only allows non-cors requests to access this API.
        origin: [],
    }),
    express.json(),
    expressMiddleware(server, {
        context: async () => ({
            dataSources: {
                backendApi: new BackendApi({ cache: server.cache }),
            },
        }),
    }),
);

app.get("/health", (_req, res) => {
    res.status(200).send("Okay!");
});

const { port } = await new Promise<AddressInfo>((resolve, reject) =>
    httpServer.listen({ port: settings.GRAPHQL_PORT }, () => {
        const addressInfo = httpServer.address();
        if (addressInfo && typeof addressInfo !== "string") {
            resolve(addressInfo);
        } else {
            reject(new Error("Server failed to start"));
        }
    }),
);

console.log(`Server ready at http://localhost:${port}/api/graphql`);
console.log(`Using backend API at ${settings.BACKEND_API_URL}`);
