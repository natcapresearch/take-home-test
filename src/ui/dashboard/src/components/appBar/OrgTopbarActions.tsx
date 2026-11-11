import { Box, TopbarActions } from "@twilio-paste/core";
import { Maybe } from "../../../../common/__generated__/client-types";
import AdminPanel from "./adminPanel/AdminPanel";

interface OrgTopbarActionsProps {
    orgUid: string;
    selectedChangeSetUid?: string;
    defaultChangeSetUid?: Maybe<string>;
}

/**
 * The organisation-scoped contents of the app bar: the version (change set)
 * selection panel, right-aligned.
 */
function OrgTopbarActions({
    orgUid,
    selectedChangeSetUid,
    defaultChangeSetUid,
}: OrgTopbarActionsProps) {
    return (
        <Box display="flex" justifyContent="flex-end" width="100%">
            <TopbarActions justify="end">
                <AdminPanel
                    orgUid={orgUid}
                    selectedChangeSetUid={selectedChangeSetUid}
                    defaultChangeSetUid={defaultChangeSetUid}
                />
            </TopbarActions>
        </Box>
    );
}

export default OrgTopbarActions;
