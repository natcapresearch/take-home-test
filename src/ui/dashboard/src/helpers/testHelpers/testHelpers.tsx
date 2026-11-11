import { from, getApolloContext, InMemoryCache } from "@apollo/client";
import { onError } from "@apollo/client/link/error";
import { MockedProvider, MockLink } from "@apollo/client/testing";
import React, { ComponentProps, PropsWithChildren, useContext } from "react";
import { MemoryRouter, Route, RouteObject, Routes } from "react-router-dom";
import { ApplicationConfig } from "../../../../common/__generated__/client-types";
import { ThemeCustomizationProvider } from "../../../../common/theme/base";
import AppProvider from "../../contexts/AppProvider";
import OrganisationProvider, {
    OrganisationContextType,
} from "../../contexts/OrganisationProvider";
import { ToasterProvider } from "../../contexts/ToasterProvider";
import possibleTypes from "../../possibleTypes";

export const MockBase = ({ children }: PropsWithChildren) => {
    return (
        <ThemeCustomizationProvider>
            <ToasterProvider>{children}</ToasterProvider>
        </ThemeCustomizationProvider>
    );
};

interface MockRouterProps extends PropsWithChildren {
    routes?: RouteObject[];
    initialEntries?: string[];
}

/**
 * Wraps a component in a React Router-compatible Router.
 *
 * Uses `MemoryRouter` (library-mode router), which directly renders children
 * inside the router context. This is the correct approach for library-mode unit
 * testing in React Router v7.
 *
 * For tests that need path params or multiple routes, pass explicit `routes`.
 */
export const MockRouter = ({
    children,
    routes,
    initialEntries,
}: MockRouterProps) => {
    if (routes) {
        return (
            <MemoryRouter initialEntries={initialEntries}>
                <Routes>
                    {routes.map((route, i) => (
                        <Route
                            key={i}
                            path={route.path}
                            element={route.element as React.ReactElement}
                        />
                    ))}
                </Routes>
            </MemoryRouter>
        );
    }

    return (
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    );
};

interface MockOrganisationProviderProps extends PropsWithChildren {
    config?: OrganisationContextType["config"];
    defaultChangeSetUid?: OrganisationContextType["defaultChangeSetUid"];
}

export const mockOrganisation: OrganisationContextType = {
    name: "Test Organisation",
    uuid: "test-org-uuid",
};

export function MockOrganisationProvider({
    config,
    children,
    defaultChangeSetUid,
}: MockOrganisationProviderProps) {
    const apolloContext = useContext(getApolloContext());
    const hasApolloClient = Boolean(apolloContext?.client);

    const provider = (
        <OrganisationProvider
            organisation={{
                ...mockOrganisation,
                config,
                defaultChangeSetUid,
            }}
        >
            {children}
        </OrganisationProvider>
    );

    return hasApolloClient ? (
        provider
    ) : (
        <MockApolloProvider>{provider}</MockApolloProvider>
    );
}

interface MockApplicationProviderProps extends PropsWithChildren {
    config: ApplicationConfig;
}

export function MockAppContext({
    config,
    children,
}: MockApplicationProviderProps) {
    return <AppProvider config={config}>{children}</AppProvider>;
}

/**
 * Filters a list of HTML elements to remove any that are hidden (using the
 * hidden attribute, as it appears Paste does).
 *
 * This is useful because by default React Testing Library still "sees"
 * elements that are hidden.
 */
export function filterHiddenElements(elements: HTMLElement[]): HTMLElement[] {
    return elements.filter((element) => !element.closest("[hidden]"));
}

export const MockApolloProvider = ({
    mocks = [],
    debug,
    cache,
    ...rest
}: ComponentProps<typeof MockedProvider> & { debug?: boolean }) => (
    <MockedProvider
        {...rest}
        // Mirror the real client's cache so tests normalise entities the way
        // the app does.
        cache={cache ?? new InMemoryCache({ possibleTypes })}
        link={
            debug
                ? from([
                      onError(({ networkError }) => {
                          if (
                              networkError &&
                              /No more mocked responses for the query/.test(
                                  networkError.message,
                              )
                          ) {
                              console.log(`[Network error]: ${networkError}`);
                          }
                      }),
                      new MockLink(mocks),
                  ])
                : undefined
        }
        mocks={!debug ? mocks : undefined}
    />
);
