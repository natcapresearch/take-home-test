import { Box, Topbar } from "@twilio-paste/core";
import OrgTopbarActions from "../../dashboard/src/components/appBar/OrgTopbarActions";
import { Maybe } from "../__generated__/client-types";

interface AppBarProps {
    orgUid: string;
    selectedChangeSetUid?: string;
    defaultChangeSetUid?: Maybe<string>;
}

const AppBar = ({
    orgUid,
    selectedChangeSetUid,
    defaultChangeSetUid,
}: AppBarProps) => {
    return (
        <Box
            position="sticky"
            top="0"
            backgroundColor="colorBackgroundBody"
            zIndex="zIndex80"
        >
            <Topbar id="topbar">
                <OrgTopbarActions
                    orgUid={orgUid}
                    selectedChangeSetUid={selectedChangeSetUid}
                    defaultChangeSetUid={defaultChangeSetUid}
                />
            </Topbar>
        </Box>
    );
};

export default AppBar;
