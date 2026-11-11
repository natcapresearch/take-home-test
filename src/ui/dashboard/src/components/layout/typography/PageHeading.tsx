import { Box, Text } from "@twilio-paste/core";
import { Margin } from "@twilio-paste/style-props";
import { PropsWithChildren, ReactNode } from "react";

interface PageHeadingProps extends PropsWithChildren {
    tagLine?: ReactNode | string;
    buttons?: ReactNode;
    showButtons?: boolean;
    isCentered?: boolean;
    hasBreadcrumbs?: boolean;
    marginBottom?: Margin;
}

const PageHeading = ({
    children,
    tagLine,
    buttons,
    showButtons,
    isCentered,
    hasBreadcrumbs,
    marginBottom = "space100",
}: PageHeadingProps) => {
    const getMarginTop = () => {
        if (hasBreadcrumbs) return "space60";
        if (showButtons) return "space40";
        return "space80";
    };
    return (
        <Box
            as="h1"
            fontSize="fontSize90"
            marginTop={getMarginTop()}
            marginBottom={marginBottom}
        >
            <Box
                display="flex"
                justifyContent={isCentered ? "center" : "space-between"}
                alignItems="flex-end"
            >
                {children}
                {showButtons && (
                    <Box display="flex" columnGap="space40">
                        {buttons}
                    </Box>
                )}
            </Box>
            {tagLine && (
                <Text
                    as="span"
                    fontWeight="fontWeightNormal"
                    marginTop="space60"
                    textAlign={isCentered ? "center" : "left"}
                    display="block"
                >
                    {tagLine}
                </Text>
            )}
        </Box>
    );
};

export default PageHeading;
