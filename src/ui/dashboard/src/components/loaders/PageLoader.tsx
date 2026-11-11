import { Box, Spinner } from "@twilio-paste/core";

const PageLoader = () => {
    return (
        <Box
            width="100%"
            height="70vh"
            justifyContent="center"
            alignItems="center"
            display="flex"
        >
            <Spinner decorative={false} title="Loading" size="sizeIcon60" />
        </Box>
    );
};

export default PageLoader;
