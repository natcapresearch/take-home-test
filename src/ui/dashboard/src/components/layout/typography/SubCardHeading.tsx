import { Box } from "@twilio-paste/core";
import { Margin } from "@twilio-paste/style-props";
import { PropsWithChildren } from "react";

interface SubCardHeadingProps extends PropsWithChildren {
    margin?: Margin;
    element?: string;
}

const SubCardHeading = ({ children, margin, element }: SubCardHeadingProps) => {
    return (
        <Box as="h4" fontSize="fontSize50" margin={margin} element={element}>
            {children}
        </Box>
    );
};

export default SubCardHeading;
