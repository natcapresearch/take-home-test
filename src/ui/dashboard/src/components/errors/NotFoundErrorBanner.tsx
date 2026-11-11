import { Box, Card, Paragraph } from "@twilio-paste/core";
import NotFound from "../../../../common/theme/assets/not-found.svg";
import CardHeading from "../layout/typography/CardHeading";

interface NotFoundErrorBannerProps {
    entity: string;
    additionalInfo?: string;
}

function NotFoundErrorBanner({
    entity,
    additionalInfo,
}: NotFoundErrorBannerProps) {
    return (
        <Box as="main" element="MAIN">
            <Card>
                <Box display="flex" alignItems="center">
                    <Box marginRight="space70">
                        <Box width="size20" as="img" src={NotFound} alt="" />
                    </Box>
                    <Box>
                        <CardHeading>{entity} not found</CardHeading>
                        <Paragraph>
                            The {entity.toLocaleLowerCase()} you're looking for
                            either doesn't exist or was moved.
                        </Paragraph>
                        {additionalInfo && (
                            <Paragraph>{additionalInfo}</Paragraph>
                        )}
                    </Box>
                </Box>
            </Card>
        </Box>
    );
}

export default NotFoundErrorBanner;
