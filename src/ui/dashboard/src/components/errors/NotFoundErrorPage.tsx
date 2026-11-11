import { Box } from "@twilio-paste/core";
import NotFoundErrorBanner from "./NotFoundErrorBanner";

function NotFoundErrorPage() {
    return (
        <Box
            display="flex"
            flexDirection="column"
            minHeight="100vh"
            overflow="hidden"
        >
            <Box as="main" element="MAIN">
                <NotFoundErrorBanner entity="Page" />
            </Box>
        </Box>
    );
}

export default NotFoundErrorPage;
