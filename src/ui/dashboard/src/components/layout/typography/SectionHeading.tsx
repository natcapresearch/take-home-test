import { Box } from "@twilio-paste/core";
import { Margin } from "@twilio-paste/style-props";
import { PropsWithChildren } from "react";

interface SectionHeadingProps extends PropsWithChildren {
    margin?: Margin;
}

const SectionHeading = ({ children, margin }: SectionHeadingProps) => {
    return (
        <Box as="h4" fontSize="fontSize40" margin={margin}>
            {children}
        </Box>
    );
};

export default SectionHeading;
