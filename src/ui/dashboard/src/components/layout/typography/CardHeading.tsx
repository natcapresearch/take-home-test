import { Box } from "@twilio-paste/core";
import { Margin } from "@twilio-paste/style-props";
import { PropsWithChildren, ReactNode } from "react";

interface CardHeadingProps extends PropsWithChildren {
    tagLine?: ReactNode | string;
    buttons?: ReactNode;
    isCentered?: boolean;
    margin?: Margin;
    hasButtonMargin?: boolean;
}

const CardHeading = ({
    children,
    tagLine,
    buttons,
    margin,
    isCentered,
    hasButtonMargin,
}: CardHeadingProps) => {
    return (
        <Box
            as="h3"
            fontSize="fontSize70"
            marginTop="space0"
            marginBottom={margin || "space60"}
        >
            <Box
                display="flex"
                alignItems={buttons ? "flex-start" : "flex-end"}
                justifyContent={isCentered ? "center" : "space-between"}
            >
                {children}
                {buttons && (
                    <Box display="flex" columnGap="space40">
                        {buttons}
                    </Box>
                )}
            </Box>
            {tagLine && (
                <Box
                    element="TAG_LINE"
                    marginTop={
                        buttons && !hasButtonMargin ? "space0" : "space40"
                    }
                    textAlign={isCentered ? "center" : "left"}
                >
                    {tagLine}
                </Box>
            )}
        </Box>
    );
};

export default CardHeading;
