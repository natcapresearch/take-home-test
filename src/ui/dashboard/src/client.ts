import { ApolloClient, HttpLink, InMemoryCache } from "@apollo/client";
import { getDashboardApiUrl } from "./helpers/environmentHelpers";
import possibleTypes from "./possibleTypes";

export function createClient() {
    return new ApolloClient({
        cache: new InMemoryCache({ possibleTypes }),
        link: new HttpLink({ uri: getDashboardApiUrl() }),
    });
}
