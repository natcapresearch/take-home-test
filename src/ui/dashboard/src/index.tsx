import { ApolloProvider } from "@apollo/client";
import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
    createBrowserRouter,
    Navigate,
    redirect,
    RouterProvider,
} from "react-router-dom";
import {
    ApplicationConfig,
    BootstrapDocument,
} from "../../common/__generated__/client-types";
import Base from "../../common/theme/base";
import OrganisationApp from "./apps/OrganisationApp";
import { createClient } from "./client";
import GenericErrorPage from "./components/errors/GenericErrorPage";
import NotFoundErrorPage from "./components/errors/NotFoundErrorPage";
import AppProvider from "./contexts/AppProvider";
import { ToasterProvider } from "./contexts/ToasterProvider";
import {
    EchartsTooltipGlobalStyle,
    registerNatcapEchartsTheme,
} from "./helpers/echartsHelpers";
import { valueFromResult } from "./helpers/graphqlHelpers";
import useLazyAuthenticatedQuery from "./helpers/hooks/useLazyAuthenticatedQuery";
import { redirectHashRouterToBrowserRouter } from "./helpers/urlHelpers";
import CommoditiesOverview from "./page/Organisation/CommoditiesOverview";
import { ErrorType } from "./types/uiIdentifiers";

// This *MUST* be called before React Router initialises, to prevent it from
// interpreting the hash-based route as a root path (i.e. /#/foo is technically
// / when using the browser router)
redirectHashRouterToBrowserRouter();
registerNatcapEchartsTheme();

const orgRoute = {
    ErrorBoundary: () => <GenericErrorPage type={ErrorType.PageNotFound} />,
    element: <OrganisationApp />,
    children: [
        {
            index: true,
            element: <Navigate to="commodities-overview" replace />,
        },
        {
            path: "commodities-overview",
            element: <CommoditiesOverview />,
            handle: { title: "Commodities Overview" },
        },
    ],
};

const AppWithRoutes = () => {
    const [loaded, setLoaded] = useState(false);
    const [bootstrap, { loading, error, data }] = useLazyAuthenticatedQuery(
        BootstrapDocument,
        {
            // We always want to fetch the latest data from the server when this
            // component is mounted.
            fetchPolicy: "network-only",
        },
    );

    useEffect(() => {
        bootstrap();
    }, [bootstrap]);

    if (!loaded && !loading && data) {
        setLoaded(true);
    }

    // Show an error if we've loaded, but have an error
    if (loaded && error) {
        return <GenericErrorPage type={ErrorType.NoData} />;
    }

    // Show a loading state if we're loading for the first time
    if (!loaded && loading) {
        return null;
    }

    // Show an error if we've loaded, and are not re-loading, but have no data
    if (loaded && !loading && !data) {
        return <GenericErrorPage type={ErrorType.NoData} />;
    }

    if (!data) {
        return null;
    }

    const appConfig = valueFromResult<ApplicationConfig>(
        "ApplicationConfig",
        data.config,
    );

    // The dashboard serves one organisation: the one the GraphQL server is
    // configured with (DEFAULT_ORG_UID). The root URL opens it.
    const defaultOrgUid = appConfig?.defaultOrgUid;

    const router = createBrowserRouter([
        {
            path: "*",
            element: <NotFoundErrorPage />,
        },
        {
            path: "/o/:orgId",
            ...orgRoute,
        },
        {
            path: "/o/:orgId/c/:changeSetUid",
            ...orgRoute,
        },
        {
            path: "/",
            loader: () =>
                defaultOrgUid
                    ? redirect(`/o/${defaultOrgUid}/commodities-overview`)
                    : null,
            element: <GenericErrorPage type={ErrorType.MissingOrganisation} />,
        },
    ]);

    return (
        <Base>
            <EchartsTooltipGlobalStyle />
            <AppProvider config={appConfig} viewer={data.viewer}>
                <ToasterProvider>
                    <RouterProvider router={router} />
                </ToasterProvider>
            </AppProvider>
        </Base>
    );
};

const client = createClient();
const AppWithApollo = () => {
    return (
        <ApolloProvider client={client}>
            <AppWithRoutes />
        </ApolloProvider>
    );
};

const container = document.getElementById("app");
const root = createRoot(container as HTMLElement);

root.render(
    <StrictMode>
        <AppWithApollo />
    </StrictMode>,
);
