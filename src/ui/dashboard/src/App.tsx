import { Box, SidebarPushContentWrapper } from "@twilio-paste/core";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Maybe } from "../../common/__generated__/client-types";
import AppBar from "../../common/components/AppBar";
import Sidebar from "../../common/components/Sidebar/Sidebar";
import { NavItem } from "../../common/types";
import PageLoader from "./components/loaders/PageLoader";
import Title from "./components/navigation/Title";
import { useTitleSegments } from "./helpers/hooks/useTitleSegments";

interface AppProps {
    navItems: NavItem[];
    orgUid: string;
    orgName?: Maybe<string>;
    selectedChangeSetUid?: string;
    defaultChangeSetUid?: Maybe<string>;
    isPageContentLoading?: boolean;
}

function App({
    navItems,
    orgUid,
    orgName,
    selectedChangeSetUid,
    defaultChangeSetUid,
    isPageContentLoading,
}: AppProps) {
    const titleSegments = useTitleSegments();

    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

    return (
        <>
            <Title title={titleSegments.join(" | ")} />
            <Sidebar
                navItems={navItems}
                orgName={orgName}
                isSidebarCollapsed={isSidebarCollapsed}
                setIsSidebarCollapsed={setIsSidebarCollapsed}
            />

            <SidebarPushContentWrapper
                collapsed={isSidebarCollapsed}
                variant="compact"
            >
                <Box display="flex" flexDirection="column">
                    <AppBar
                        orgUid={orgUid}
                        selectedChangeSetUid={selectedChangeSetUid}
                        defaultChangeSetUid={defaultChangeSetUid}
                    />

                    <Box as="main" element="MAIN">
                        {isPageContentLoading ? <PageLoader /> : <Outlet />}
                    </Box>
                </Box>
            </SidebarPushContentWrapper>
        </>
    );
}

export default App;
