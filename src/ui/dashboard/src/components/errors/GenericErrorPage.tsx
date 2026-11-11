import { Box } from "@twilio-paste/core";
import { ErrorType, PageId } from "../../types/uiIdentifiers";
import GenericError from "./GenericError";

interface GenericErrorPageProps {
    type: ErrorType;
}

function GenericErrorPage({ type }: GenericErrorPageProps) {
    return (
        <Box
            display="flex"
            flexDirection="column"
            minHeight="100vh"
            overflow="hidden"
        >
            <Box as="main" element="MAIN">
                <GenericError category={PageId.Index} type={type} />
            </Box>
        </Box>
    );
}

export default GenericErrorPage;
