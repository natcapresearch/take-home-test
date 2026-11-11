import {
    act,
    fireEvent,
    render,
    screen,
    waitFor,
    within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMultiselectCombobox } from "@twilio-paste/core";
import { useState } from "react";
import { MockBase } from "../../../helpers/testHelpers/testHelpers";
import MultiSelectFilter from "../MultiSelectFilter";

const defaultItems = ["item_1", "item_2", "item_3", "item_10"];
const itemsWithSubLabels = ["a/b/item_1", "x/y/item_2"];
const fieldName = "input label";

interface RenderMultiSelectFilterProps {
    showSubLabel?: boolean;
    items?: string[];
}

const renderMultiSelectFilter = ({
    showSubLabel,
    items,
}: RenderMultiSelectFilterProps) => {
    const Wrapper = () => {
        const state = useMultiselectCombobox({
            initialSelectedItems: [],
        });

        return (
            <MockBase>
                <MultiSelectFilter
                    state={state}
                    items={
                        items ??
                        (showSubLabel ? itemsWithSubLabels : defaultItems)
                    }
                    fieldName={fieldName}
                    showSubLabel={showSubLabel}
                />
            </MockBase>
        );
    };

    return render(<Wrapper />);
};

const getFilter = () => screen.getByTestId(`multi-select-filter-${fieldName}`);

describe("MultiSelectFilter", () => {
    it("Renders all dropdown items", async () => {
        renderMultiSelectFilter({});

        const filter = getFilter();
        fireEvent.click(filter);

        defaultItems.forEach((item) => {
            expect(screen.getByText(item)).toBeInTheDocument();
        });
    });

    it("Renders correct dropdown items on type", async () => {
        renderMultiSelectFilter({});

        const filter = getFilter();
        const searchString = "_1";

        await act(async () => {
            fireEvent.click(filter);
            await userEvent.type(filter, searchString);
        });

        await waitFor(() => {
            expect(screen.getByText("item_1")).toBeInTheDocument();
        });
        expect(screen.queryByText("item_2")).toBeNull();
    });

    it("displays the correct placeholder", () => {
        renderMultiSelectFilter({});

        expect(screen.getByPlaceholderText(fieldName)).toBeInTheDocument();
    });

    it("shows the field name as a heading at the top of the dropdown", async () => {
        renderMultiSelectFilter({});

        const filter = getFilter();
        fireEvent.click(filter);

        expect(
            await screen.findByRole("group", { name: fieldName }),
        ).toBeInTheDocument();
    });

    it("displays empty message if no results found and disappears if found", async () => {
        renderMultiSelectFilter({});

        expect(screen.queryByTestId("empty-state")).toBeNull();

        const filter = getFilter();

        await act(async () => {
            await userEvent.type(filter, "item_12");
        });

        await waitFor(() => {
            expect(screen.getByTestId("empty-state")).toBeInTheDocument();
        });

        await act(async () => {
            await userEvent.type(filter, "{backspace}");
        });

        await waitFor(() => {
            expect(screen.queryByTestId("empty-state")).toBeNull();
        });
    });

    it("renders label and sublabel when showSubLabel is true", async () => {
        renderMultiSelectFilter({
            showSubLabel: true,
        });

        const filter = getFilter();
        await act(async () => {
            filter.focus();
            fireEvent.click(filter);
        });

        expect(screen.getByText("item_1")).toBeInTheDocument();
        expect(screen.getByText("a/b/item_1")).toBeInTheDocument();
        expect(screen.getByText("item_2")).toBeInTheDocument();
        expect(screen.getByText("x/y/item_2")).toBeInTheDocument();
    });

    it("shows only the short label in the selected chip when showSubLabel is true", async () => {
        renderMultiSelectFilter({ showSubLabel: true });

        const filter = getFilter();
        await act(async () => {
            fireEvent.click(filter);
        });

        await act(async () => {
            fireEvent.click(screen.getByText("item_1"));
        });

        const selectedPills = screen.getByRole("listbox", {
            name: /Selected input label/i,
        });

        expect(within(selectedPills).getByText("item_1")).toBeInTheDocument();
        expect(within(selectedPills).queryByText("a/b/item_1")).toBeNull();
    });

    it("does not repeat the label as its own sublabel when an item has no path", async () => {
        // Some sources hold only the leaf of an ISIC path, so this filter
        // can be fed already-abbreviated values. Rendering the sublabel
        // anyway showed every activity name twice.
        renderMultiSelectFilter({
            items: ["Wind energy production", "a/b/item_1"],
            showSubLabel: true,
        });

        const filter = getFilter();
        await act(async () => {
            fireEvent.click(filter);
        });

        expect(screen.getAllByText("Wind energy production")).toHaveLength(1);
        // An item that does have a path still shows both lines.
        expect(screen.getByText("item_1")).toBeInTheDocument();
        expect(screen.getByText("a/b/item_1")).toBeInTheDocument();
    });

    it("does not render sublabel when showSubLabel is false even if items contain '/'", async () => {
        renderMultiSelectFilter({
            items: itemsWithSubLabels,
            showSubLabel: false,
        });

        const filter = getFilter();
        await act(async () => {
            fireEvent.click(filter);
        });

        expect(screen.getByText("a/b/item_1")).toBeInTheDocument();
        expect(screen.queryByText("item_1")).toBeNull();

        expect(screen.getByText("x/y/item_2")).toBeInTheDocument();
        expect(screen.queryByText("item_2")).toBeNull();
    });

    it("does not reapply filters when the parent rerenders without selection changes", async () => {
        const applyFilters = jest.fn();

        const Wrapper = () => {
            const [renderCount, setRenderCount] = useState(0);
            const state = useMultiselectCombobox({
                initialSelectedItems: [],
            });

            return (
                <MockBase>
                    <button onClick={() => setRenderCount((prev) => prev + 1)}>
                        rerender {renderCount}
                    </button>
                    <MultiSelectFilter
                        state={state}
                        items={defaultItems}
                        fieldName={fieldName}
                        applyFilters={() => applyFilters()}
                    />
                </MockBase>
            );
        };

        render(<Wrapper />);

        expect(applyFilters).toHaveBeenCalledTimes(1);

        await userEvent.click(
            screen.getByRole("button", { name: /rerender/i }),
        );

        expect(applyFilters).toHaveBeenCalledTimes(1);
    });
});
