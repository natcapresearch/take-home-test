import { fireEvent, screen, waitFor, within } from "@testing-library/react";

export const expectMultiselectItems = async (
    name: string,
    options: string[],
) => {
    const dropdown = await screen.findByPlaceholderText(name);
    fireEvent.click(dropdown);

    await waitFor(() => {
        options.forEach((option) => {
            expect(screen.getByText(option)).toBeInTheDocument();
        });
    });
};

export const selectDropdownItem = async (name: string, option: string) => {
    const dropdown = screen.getByRole("textbox", {
        name: name,
    });

    fireEvent.click(dropdown!);

    fireEvent.click(
        within(await screen.findByRole("listbox")).getByText(option),
    );
};

export const selectMultiselectItem = async (name: string, option: string) => {
    const dropdown = await screen.findByPlaceholderText(`Select ${name}`);
    fireEvent.click(dropdown);
    fireEvent.change(dropdown, { target: { value: option } });

    const menus = await screen.findAllByRole("listbox");
    const menu = menus.find((lb) => {
        const labelId = lb.getAttribute("aria-labelledby");
        if (!labelId) return false;
        const label = document.getElementById(labelId);
        return label?.textContent?.toLowerCase().includes(name.toLowerCase());
    });

    if (!menu) throw new Error(`Listbox for "${name}" not found`);

    const [match] = await within(menu).findAllByText(option);
    fireEvent.click(match.closest('[role="option"]') as HTMLElement);
};

export const expectGenericError = async () => {
    await waitFor(() => {
        expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
    });
};

export const clickTableSort = async (columnName: string) => {
    await waitFor(() => {
        expect(screen.getAllByRole("columnheader").length).toBeGreaterThan(0);
    });

    const siteHeader = screen
        .getAllByRole("columnheader")
        .find((th) => th.textContent?.includes(columnName));

    const sortButton = siteHeader!.querySelector("button");

    fireEvent.click(sortButton!);
};
