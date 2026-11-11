import { Box, MultiselectCombobox } from "@twilio-paste/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { afterLast, conditionalLowercase } from "../../helpers/stringHelpers";
import EmptyState from "../EmptyState";

// The item shape backing MultiSelectFilter's combobox state. Every item
// shares `group: fieldName`, which is what Paste's groupItemsBy renders as
// the heading at the top of the dropdown.
export interface MultiSelectFilterItem {
    label: string;
    group: string;
}

export interface MultiSelectFilterProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    state: any;
    items: string[];
    fieldName: string;
    disabled?: boolean;
    applyFilters?: () => void;
    showSubLabel?: boolean;
    usePortal?: boolean;
    element?: string;
}

const MultiSelectFilter = ({
    state,
    items,
    fieldName,
    disabled,
    applyFilters,
    showSubLabel,
    usePortal = true,
    element,
}: MultiSelectFilterProps) => {
    const [inputValue, setInputValue] = useState("");
    const previousSelectedLabelsRef = useRef<string[] | null>(null);
    const applyFiltersRef = useRef(applyFilters);

    const selectedItems = state.selectedItems as MultiSelectFilterItem[];
    const selectedLabels = useMemo(
        () => selectedItems.map((item) => item.label),
        [selectedItems],
    );
    const selectedLabelSet = useMemo(
        () => new Set(selectedLabels),
        [selectedLabels],
    );

    useEffect(() => {
        applyFiltersRef.current = applyFilters;
    }, [applyFilters]);

    useEffect(() => {
        const previousSelectedLabels = previousSelectedLabelsRef.current;
        const selectionChanged =
            !previousSelectedLabels ||
            previousSelectedLabels.length !== selectedLabels.length ||
            previousSelectedLabels.some(
                (label, index) => label !== selectedLabels[index],
            );

        if (!selectionChanged) {
            return;
        }

        previousSelectedLabelsRef.current = [...selectedLabels];

        applyFiltersRef.current?.();
    }, [selectedLabels]);

    const getLabel = (label: string) => {
        if (!label) return "";
        if (showSubLabel) {
            return afterLast(label, "/");
        }
        return label;
    };

    // The sub-label is the full path behind an abbreviated label, e.g.
    // "Wind energy production" over its whole ISIC classification. Values
    // that arrive already abbreviated (just the leaf, no path) have nothing
    // to add, and rendering it anyway prints the same name twice, stacked.
    const getSubLabel = (label: string) => {
        if (!label || !showSubLabel || getLabel(label) === label) {
            return <></>;
        }
        return (
            <Box as="span" element="TEXT_WEAK">
                {label}
            </Box>
        );
    };

    // Stable per-label objects (memoized on the raw items/fieldName, not on
    // the filtered-by-search-text subset) so Paste's selection toggle, which
    // compares items by reference, keeps working across renders.
    const allComboboxItems = useMemo<MultiSelectFilterItem[]>(
        () => items.map((label) => ({ label, group: fieldName })),
        [items, fieldName],
    );

    const comboboxItems = useMemo(
        () =>
            allComboboxItems.filter(
                (item) =>
                    !selectedLabelSet.has(item.label) &&
                    item.label.toLowerCase().includes(inputValue.toLowerCase()),
            ),
        [allComboboxItems, selectedLabelSet, inputValue],
    );

    return (
        <Box width="100%" minWidth="0">
            <MultiselectCombobox
                element={element}
                disabled={disabled}
                labelText=""
                data-testid={`multi-select-filter-${fieldName}`}
                selectedItemsLabelText={`Selected ${conditionalLowercase(
                    fieldName,
                )}`}
                items={comboboxItems}
                groupItemsBy="group"
                onInputValueChange={({ inputValue: newValue = "" }) => {
                    setInputValue(newValue);
                }}
                placeholder={fieldName}
                usePortal={usePortal}
                state={state}
                emptyState={() => <EmptyState />}
                data-form-type="other"
                itemToString={(item) => (item ? getLabel(item.label) : "")}
                optionTemplate={(item) => (
                    <Box as="span" display="flex" flexDirection="column">
                        <Box as="span">{getLabel(item.label)}</Box>
                        {getSubLabel(item.label)}
                    </Box>
                )}
            />
        </Box>
    );
};

export default MultiSelectFilter;
