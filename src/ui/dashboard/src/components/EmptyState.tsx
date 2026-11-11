import { Box, BoxProps, Text } from "@twilio-paste/core";
import { ReactNode } from "react";
// This is turned off becuase we don't have a solution for loading images in Jest,
// so we can't test the image is rendered correctly.
// import EmptySearch from "../../../common/theme/assets/empty-search.svg";

type EmptyStateProps = BoxProps & {
    children?: ReactNode;
    // illustrate?: boolean;
};

const EmptyState = ({ children, ...boxProps }: EmptyStateProps) => {
    const props: BoxProps = {
        paddingY: "space40",
        paddingX: "space50",
        ...boxProps,
    };
    return (
        <Box {...props} data-testid="empty-state">
            <Box display="flex" alignItems="center">
                {/* {illustrate && (
                    <Box marginRight="space70">
                        <Box width="size20" as="img" src={EmptySearch} alt="" />
                    </Box>
                )} */}
                <Text as="span" fontStyle="italic" element="TEXT_WEAK">
                    {children ?? "No results found."}
                </Text>
            </Box>
        </Box>
    );
};

export default EmptyState;
