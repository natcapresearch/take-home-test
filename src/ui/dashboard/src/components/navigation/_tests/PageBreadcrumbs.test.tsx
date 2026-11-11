import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BasenameProvider } from "../../../contexts/BasenameContext";
import { MockRouter } from "../../../helpers/testHelpers/testHelpers";
import PageBreadcrumbs from "../PageBreadcrumbs";

describe("PageBreadcrumbs", () => {
    const renderBreadcrumbs = () =>
        render(
            <MockRouter
                initialEntries={["/o/org-1/c/cs-1/commodities/coffee"]}
                routes={[
                    {
                        path: "/o/org-1/c/cs-1/commodities/coffee",
                        element: (
                            <BasenameProvider basename="/o/org-1/c/cs-1">
                                <PageBreadcrumbs
                                    items={[
                                        {
                                            label: "Commodities overview",
                                            path: "/commodities-overview",
                                        },
                                        { label: "Commodities" },
                                    ]}
                                    currentPage="Coffee"
                                />
                            </BasenameProvider>
                        ),
                    },
                    {
                        path: "/o/org-1/c/cs-1/commodities-overview",
                        element: <p>Commodities overview page</p>,
                    },
                ]}
            />,
        );

    it("renders parents as links, prefixed with the basename", () => {
        renderBreadcrumbs();

        expect(
            screen
                .getByRole("link", { name: "Commodities overview" })
                .getAttribute("href"),
        ).toBe("/o/org-1/c/cs-1/commodities-overview");
    });

    it("renders parents without a path as plain text, not the current page", () => {
        renderBreadcrumbs();

        const commodities = screen.getByText("Commodities");
        expect(commodities.closest("a")).toBeNull();
        expect(commodities.getAttribute("aria-current")).toBeNull();
    });

    it("renders the current page last, as non-clickable text", () => {
        renderBreadcrumbs();

        const currentPage = screen.getByText("Coffee");
        expect(currentPage.closest("a")).toBeNull();
        expect(currentPage.getAttribute("aria-current")).toBe("page");
        expect(screen.getAllByRole("listitem").at(-1)?.textContent).toBe(
            "Coffee",
        );
    });

    it("separates items, with no separator after the current page", () => {
        renderBreadcrumbs();

        expect(screen.getByRole("navigation").textContent).toBe(
            "Commodities overview/Commodities/Coffee",
        );
    });

    it("navigates to the parent page without a full reload", async () => {
        renderBreadcrumbs();

        await userEvent.click(
            screen.getByRole("link", { name: "Commodities overview" }),
        );

        expect(screen.getByText("Commodities overview page")).toBeDefined();
    });
});
