import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
    client: "@hey-api/client-fetch",
    input: "src/backend/__generated__/openapi.json",
    output: "src/graphql/__generated__/backend",
});
