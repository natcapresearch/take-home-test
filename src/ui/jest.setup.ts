import "@testing-library/jest-dom";

/**
 * React Router v7 Library Mode Testing
 *
 * This codebase uses React Router in "library mode" (not "framework mode"):
 *   • Library mode: BrowserRouter/MemoryRouter + <Routes>/<Route>
 *   • Framework mode: RouterProvider + data-driven route config
 * See: https://reactrouter.com/start/library/routing
 *
 * MemoryRouter is the correct testing router for library mode. RouterProvider is
 * only for framework mode and does not reliably propagate LocationContext in
 * React 19 + Jest JSDOM environments (see MockRouter in testHelpers.tsx).
 *
 * Some APIs require a data router (RouterProvider/createMemoryRouter) which
 * provides DataRouterContext/DataRouterStateContext. Tests use MemoryRouter,
 * so we must stub the data-router-only APIs that components use:
 *
 *   • useMatches: Returns route match objects from data router.
 *     Library mode has no data router, so return [] to disable handle-based
 *     logic. If tests verify route-specific behavior, they can override this
 *     mock locally.
 *
 *   • Form: React Router's <Form> calls useSubmit() internally, which requires
 *     DataRouterContext. Stub to "form" (native <form> tag), which is all unit
 *     tests need.
 */
jest.mock("react-router-dom", () => ({
    ...jest.requireActual("react-router-dom"),
    useMatches: jest.fn(() => []),
    Form: "form",
}));

// Jest does not fully support ES modules (ESM) by default, and react-leaflet is an ESM package.
// This can cause Jest to throw syntax errors when trying to import `react-leaflet` components.
// Since map rendering is not the focus of our unit tests, we can safely mock the library.
jest.mock("react-leaflet", () => ({
    MapContainer: jest.fn(() => "<MapContainer />"),
    ScaleControl: jest.fn(() => "<ScaleControl />"),
    TileLayer: jest.fn(() => "<TileLayer />"),
}));

// JSDOM (the DOM environment used by Jest) does not implement certain browser APIs,
// including window.scrollTo, because there is no real viewport to scroll.
// Some components in our codebase call window.scrollTo, which would otherwise throw
// "Error: Not implemented: window.scrollTo" during tests.
// We mock scrollTo globally to silence this error and allow those components to be tested.
beforeAll(() => {
    Object.defineProperty(window, "scrollTo", {
        value: jest.fn(),
        writable: true,
    });
});
