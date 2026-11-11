import { Box } from "@twilio-paste/core";
import { PropsWithChildren } from "react";

interface PageWrapperProps extends PropsWithChildren {
    isFullWidth?: boolean;
    isForm?: boolean;
    width?: string;
}

const PageWrapper = ({
    isFullWidth,
    children,
    isForm,
    width,
}: PageWrapperProps) => {
    return (
        <Box
            maxWidth={isFullWidth ? "100%" : "80em"}
            margin="auto"
            padding="space70"
            width={isForm ? "size80" : width}
        >
            {children}
        </Box>
    );
};

export default PageWrapper;
