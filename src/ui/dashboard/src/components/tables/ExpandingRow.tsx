import {
    Button,
    DataGridCell,
    DataGridRow,
    DataGridRowProps,
} from "@twilio-paste/core";
import { ChevronDownIcon } from "@twilio-paste/icons/esm/ChevronDownIcon";
import { ChevronRightIcon } from "@twilio-paste/icons/esm/ChevronRightIcon";
import { ReactNode, useState } from "react";

interface ExpandingRowProps extends DataGridRowProps {
    renderExpandedRows: () => ReactNode;
}

export default function ExpandingRow({
    renderExpandedRows,
    children,
    ...dataGridRowProps
}: ExpandingRowProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <>
            <DataGridRow {...dataGridRowProps}>
                <DataGridCell>
                    <Button
                        variant="secondary"
                        size="icon_small"
                        onClick={() => setIsExpanded((state) => !state)}
                    >
                        {isExpanded ? (
                            <ChevronDownIcon
                                decorative={false}
                                title="Collapse row"
                            />
                        ) : (
                            <ChevronRightIcon
                                decorative={false}
                                title="Expand row"
                            />
                        )}
                    </Button>
                </DataGridCell>
                {children}
            </DataGridRow>
            {isExpanded && renderExpandedRows()}
        </>
    );
}
