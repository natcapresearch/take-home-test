import { Box, Spinner } from "@twilio-paste/core";
import { SpinnerProps } from "@twilio-paste/core/spinner";

interface LoaderProps {
    size?: SpinnerProps["size"];
}

const Loader = ({ size = "sizeIcon10" }: LoaderProps) => {
    return (
        <Box margin="auto">
            <Spinner decorative={false} title="Loading" size={size} />
        </Box>
    );
};

export default Loader;
