import {
    act,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMultiselectCombobox } from "@twilio-paste/core";
import { MockBase } from "../../../helpers/testHelpers/testHelpers";
import TypeaheadSearch from "../TypeaheadSearch";

// Replace lodash debounce with synchronous identity; add .cancel so the
// component's cleanup useEffect doesn't throw.
jest.mock("lodash/debounce", () => (fn: (...args: unknown[]) => unknown) => {
    const immediate = (...args: unknown[]) => fn(...args);
    immediate.cancel = () => {};
    return immediate;
});

type Item = { label: string; group: string };

const ITEMS: Item[] = [
    { label: "Alpha Site", group: "Sites" },
    { label: "Beta Site", group: "Sites" },
    { label: "Arabica", group: "Commodity sources" },
    { label: "Almonds", group: "Commodity sources" },
];

function renderMulti(
    opts: {
        items?: Item[];
        onSearchTermChange?: (v?: string) => void;
        onClear?: () => void;
    } = {},
) {
    const Wrapper = () => {
        const state = useMultiselectCombobox<Item>({
            initialSelectedItems: [],
        });
        return (
            <MockBase>
                <TypeaheadSearch
                    mode="multi"
                    state={state}
                    items={opts.items ?? ITEMS}
                    placeholder="Search here"
                    onSearchTermChange={opts.onSearchTermChange}
                    onClear={opts.onClear}
                    getItemKey={(item) => `${item.group}:${item.label}`}
                />
            </MockBase>
        );
    };
    return render(<Wrapper />);
}

function renderSingle(opts: {
    items?: Item[];
    onSelectedItemChange: (item: Item) => void;
}) {
    const Wrapper = () => (
        <MockBase>
            <TypeaheadSearch
                mode="single"
                items={opts.items ?? ITEMS}
                placeholder="Search here"
                onSelectedItemChange={opts.onSelectedItemChange}
            />
        </MockBase>
    );
    return render(<Wrapper />);
}

describe("TypeaheadSearch", () => {
    it("shows no items until at least 2 characters are typed", async () => {
        renderMulti();
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            await userEvent.type(input, "A");
        });

        // Only 1 character — no options shown
        expect(screen.queryByRole("option")).toBeNull();

        await act(async () => {
            await userEvent.type(input, "l");
        });

        // 2 characters "Al" — "Alpha Site" and "Almonds" should appear
        await waitFor(() => {
            expect(screen.queryAllByRole("option").length).toBeGreaterThan(0);
        });
    });

    it("filters items by label match (case-insensitive)", async () => {
        renderMulti();
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            await userEvent.type(input, "ar");
        });

        await waitFor(() => {
            const options = screen.queryAllByRole("option");
            const labels = options.map((o) => o.textContent ?? "");
            expect(labels.some((l) => l.includes("Arabica"))).toBe(true);
            expect(labels.some((l) => l.includes("Almonds"))).toBe(false);
        });
    });

    it("calls onSearchTermChange with the typed value when ≥2 chars", async () => {
        // lodash/debounce is mocked to identity, so calls are synchronous.
        const onSearchTermChange = jest.fn();
        renderMulti({ onSearchTermChange });
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            fireEvent.change(input, { target: { value: "al" } });
        });

        expect(onSearchTermChange).toHaveBeenCalledWith("al");
    });

    it("calls onSearchTermChange with undefined when input is shorter than 2 chars", async () => {
        const onSearchTermChange = jest.fn();
        renderMulti({ onSearchTermChange });
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            fireEvent.change(input, { target: { value: "a" } });
        });

        expect(onSearchTermChange).toHaveBeenCalledWith(undefined);
    });

    it("calls onSelectedItemChange in single mode when an item is chosen", async () => {
        const onSelectedItemChange = jest.fn();
        renderSingle({ onSelectedItemChange });
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            await userEvent.type(input, "Ar");
        });

        await waitFor(() => {
            expect(screen.queryAllByRole("option").length).toBeGreaterThan(0);
        });

        const arabica = screen
            .getAllByRole("option")
            .find((o) => o.textContent?.includes("Arabica"));
        expect(arabica).toBeDefined();

        await act(async () => {
            if (arabica) fireEvent.click(arabica);
        });

        await waitFor(() => {
            expect(onSelectedItemChange).toHaveBeenCalledWith(
                expect.objectContaining({ label: "Arabica" }),
            );
        });
    });

    it("clears input and calls onClear when the clear button is clicked", async () => {
        const onClear = jest.fn();
        renderMulti({ onClear });
        const input = screen.getByPlaceholderText("Search here");

        await act(async () => {
            fireEvent.change(input, { target: { value: "al" } });
        });

        const clearButton = await screen.findByTestId("clear-button");
        fireEvent.click(clearButton);

        await waitFor(() => {
            expect(onClear).toHaveBeenCalledTimes(1);
        });
    });
});
