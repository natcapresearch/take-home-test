import { Box, Breadcrumb, BreadcrumbItem, Text } from "@twilio-paste/core";
import { useHref, useLinkClickHandler } from "react-router-dom";
import { useBasename } from "../../contexts/BasenameContext";

export interface PageBreadcrumb {
    label: string;
    path?: string;
}

interface PageBreadcrumbsProps {
    items: PageBreadcrumb[];
    currentPage: string;
}

interface BreadcrumbChildProps {
    label: string;
    last?: boolean;
}

// Paste's BreadcrumbItem renders a plain Anchor, so route clicks through
// React Router to avoid a full page reload
const LinkedBreadcrumbItem = ({
    label,
    path,
    last,
}: BreadcrumbChildProps & { path: string }) => {
    const to = useBasename(path);
    const href = useHref(to);
    const handleClick = useLinkClickHandler(to);

    return (
        <BreadcrumbItem href={href} last={last} onClick={handleClick}>
            {label}
        </BreadcrumbItem>
    );
};

// Paste's BreadcrumbItem marks every item without an href as the current page,
// so non-link parents are rendered here with matching styles instead
const PlainBreadcrumbItem = ({ label, last }: BreadcrumbChildProps) => (
    <Box
        as="li"
        alignItems="center"
        display="inline-flex"
        fontSize="fontSize20"
        lineHeight="lineHeight20"
    >
        <Text
            as="span"
            color="colorTextWeak"
            fontSize="fontSize20"
            lineHeight="lineHeight20"
        >
            {label}
        </Text>
        {!last && (
            <Text
                as="span"
                color="colorTextWeak"
                fontSize="fontSize20"
                lineHeight="lineHeight20"
                paddingLeft="space20"
                paddingRight="space20"
                role="presentation"
            >
                /
            </Text>
        )}
    </Box>
);

const PageBreadcrumbs = ({ items, currentPage }: PageBreadcrumbsProps) => (
    <Breadcrumb>
        {items.map(({ label, path }) =>
            path ? (
                <LinkedBreadcrumbItem key={label} label={label} path={path} />
            ) : (
                <PlainBreadcrumbItem key={label} label={label} />
            ),
        )}
        <BreadcrumbItem>{currentPage}</BreadcrumbItem>
    </Breadcrumb>
);

export default PageBreadcrumbs;
