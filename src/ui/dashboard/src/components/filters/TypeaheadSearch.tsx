import {
    Button,
    Combobox,
    MultiselectCombobox,
    useMultiselectCombobox,
} from "@twilio-paste/core";
import { CloseIcon } from "@twilio-paste/icons/esm/CloseIcon";
import { SearchIcon } from "@twilio-paste/icons/esm/SearchIcon";
import debounce from "lodash/debounce";
import { ReactNode, useCallback, useEffect, useMemo, useState } from "react";

type GroupedTypeaheadItem = {
    label: string;
    group: string;
};

interface SharedGroupedTypeaheadSearchProps<T extends GroupedTypeaheadItem> {
    items: T[];
    inputValue?: string;
    onInputValueChange?: (value: string) => void;
    onSearchTermChange?: (searchTerm?: string) => void;
    placeholder: string;
    emptyState?: (() => ReactNode) | undefined;
    onClear?: () => void;
    getItemKey?: (item: T) => string;
}

interface MultiGroupedTypeaheadSearchProps<T extends GroupedTypeaheadItem>
    extends SharedGroupedTypeaheadSearchProps<T> {
    mode: "multi";
    state: ReturnType<typeof useMultiselectCombobox<T>>;
}

interface SingleGroupedTypeaheadSearchProps<T extends GroupedTypeaheadItem>
    extends SharedGroupedTypeaheadSearchProps<T> {
    mode: "single";
    resetKey?: number;
    onSelectedItemChange: (item: T) => void;
}

type GroupedTypeaheadSearchProps<T extends GroupedTypeaheadItem> =
    | MultiGroupedTypeaheadSearchProps<T>
    | SingleGroupedTypeaheadSearchProps<T>;

function GroupedTypeaheadSearch<T extends GroupedTypeaheadItem>({
    mode,
    items,
    inputValue: controlledInputValue,
    onInputValueChange,
    onSearchTermChange,
    placeholder,
    emptyState,
    onClear,
    getItemKey,
    ...modeSpecificProps
}: GroupedTypeaheadSearchProps<T>) {
    const isControlledInput = controlledInputValue !== undefined;
    const [uncontrolledInputValue, setUncontrolledInputValue] = useState("");
    const inputValue = isControlledInput
        ? controlledInputValue
        : uncontrolledInputValue;

    const debouncedSearchTermChange = useMemo(() => {
        if (!onSearchTermChange) return undefined;
        return debounce(onSearchTermChange, 300);
    }, [onSearchTermChange]);

    useEffect(() => {
        return () => debouncedSearchTermChange?.cancel();
    }, [debouncedSearchTermChange]);

    const setInputValue = useCallback(
        (nextValue: string) => {
            if (!isControlledInput) {
                setUncontrolledInputValue(nextValue);
            }
            onInputValueChange?.(nextValue);

            if (!onSearchTermChange) return;

            const normalizedValue = nextValue.trim();
            debouncedSearchTermChange?.(
                normalizedValue.length >= 2 ? normalizedValue : undefined,
            );
        },
        [
            debouncedSearchTermChange,
            isControlledInput,
            onInputValueChange,
            onSearchTermChange,
        ],
    );

    const normalizedInput = inputValue.trim().toLowerCase();
    const shouldShowItems = normalizedInput.length >= 2;
    const multiselectState =
        mode === "multi"
            ? (modeSpecificProps as MultiGroupedTypeaheadSearchProps<T>).state
            : undefined;

    const visibleItems = useMemo(() => {
        if (!shouldShowItems) return [];

        const filteredItems = items.filter((item) =>
            item.label.toLowerCase().includes(normalizedInput),
        );

        if (mode !== "multi" || !multiselectState || !getItemKey) {
            return filteredItems;
        }

        const selectedKeys = new Set(
            multiselectState.selectedItems.map((item) => getItemKey(item)),
        );

        return filteredItems.filter(
            (item) => !selectedKeys.has(getItemKey(item)),
        );
    }, [
        getItemKey,
        items,
        mode,
        multiselectState,
        normalizedInput,
        shouldShowItems,
    ]);

    const optionTemplate = (item: T) => {
        if (!shouldShowItems) return item.label;

        const index = item.label.toLowerCase().indexOf(normalizedInput);
        if (index === -1) return item.label;

        const start = item.label.slice(0, index);
        const match = item.label.slice(index, index + normalizedInput.length);
        const end = item.label.slice(index + normalizedInput.length);

        return (
            <>
                {start}
                <strong>{match}</strong>
                {end}
            </>
        );
    };

    const clearButton =
        inputValue || (multiselectState?.selectedItems.length ?? 0) > 0 ? (
            <Button
                variant="link"
                element="LINK_BUTTON"
                data-testid="clear-button"
                onClick={() => {
                    debouncedSearchTermChange?.cancel();
                    if (!isControlledInput) {
                        setUncontrolledInputValue("");
                    }
                    onInputValueChange?.("");
                    multiselectState?.setSelectedItems([]);
                    onSearchTermChange?.(undefined);
                    onClear?.();
                }}
            >
                <CloseIcon decorative={false} title="Clear" />
            </Button>
        ) : undefined;

    if (mode === "single") {
        const { resetKey, onSelectedItemChange } =
            modeSpecificProps as SingleGroupedTypeaheadSearchProps<T>;

        return (
            <Combobox
                labelText=""
                key={resetKey}
                element="FULL_WIDTH_SEARCH"
                autocomplete
                placeholder={placeholder}
                items={visibleItems}
                selectedItem={null}
                inputValue={inputValue}
                groupItemsBy="group"
                itemToString={(item) => item?.label ?? ""}
                optionTemplate={optionTemplate}
                onSelectedItemChange={(changes) => {
                    if (changes.selectedItem) {
                        onSelectedItemChange(changes.selectedItem as T);
                    }
                }}
                onInputValueChange={({ inputValue: newValue = "" }) =>
                    setInputValue(newValue)
                }
                insertBefore={<SearchIcon decorative={false} title="Search" />}
                insertAfter={clearButton}
                emptyState={shouldShowItems ? emptyState : undefined}
            />
        );
    }

    const { state } = modeSpecificProps as MultiGroupedTypeaheadSearchProps<T>;

    return (
        <MultiselectCombobox
            labelText=""
            selectedItemsLabelText="Selected search filters"
            element="SEARCH_MULTISELECT"
            placeholder={placeholder}
            items={visibleItems}
            groupItemsBy="group"
            itemToString={(item) => item?.label ?? ""}
            optionTemplate={optionTemplate}
            inputValue={inputValue}
            // Paste's public multiselect state type is not generic-compatible
            // with a wrapper generic, but this is the state returned by its hook.
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            state={state as any}
            onInputValueChange={({ inputValue: newValue = "" }) =>
                setInputValue(newValue)
            }
            insertBefore={<SearchIcon decorative={false} title="Search" />}
            insertAfter={clearButton}
            emptyState={shouldShowItems ? emptyState : undefined}
        />
    );
}

export default GroupedTypeaheadSearch;
