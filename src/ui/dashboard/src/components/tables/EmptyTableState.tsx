import { Box, Card, Paragraph } from "@twilio-paste/core";
import EmptySearch from "../../../../common/theme/assets/empty-search.svg";
import CardHeading from "../layout/typography/CardHeading";

export const EmptyTableState = () => {
    return (
        <Card>
            <Box display="flex" alignItems="center">
                <Box marginRight="space70">
                    <Box width="size20" as="img" src={EmptySearch} alt="" />
                </Box>
                <Box>
                    <CardHeading>No results found</CardHeading>
                    <Paragraph>
                        You can modify your filter selection above, or clear all
                        of them.
                    </Paragraph>
                </Box>
            </Box>
        </Card>
    );
};
