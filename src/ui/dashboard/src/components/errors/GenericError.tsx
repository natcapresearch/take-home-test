import { Box, Card, Paragraph } from "@twilio-paste/core";
import { ReactNode } from "react";
import EmptyWarning from "../../../../common/theme/assets/empty-warning.svg";
import { AppElementId, ErrorType, PageId } from "../../types/uiIdentifiers";
import CardHeading from "../layout/typography/CardHeading";

interface GenericErrorProps {
    category: AppElementId | PageId;
    type: ErrorType;
    message?: string;
    heading?: string;
    content?: ReactNode;
}

const GenericError = ({ heading, content }: GenericErrorProps) => {
    return (
        <Card>
            <Box display="flex" alignItems="center" padding="space70">
                <Box marginRight="space70">
                    <Box width="size20" as="img" src={EmptyWarning} alt="" />
                </Box>
                <Box>
                    <CardHeading>
                        {heading || "Something went wrong."}
                    </CardHeading>
                    {content || <Paragraph>Please refresh the page.</Paragraph>}
                </Box>
            </Box>
        </Card>
    );
};

export default GenericError;
