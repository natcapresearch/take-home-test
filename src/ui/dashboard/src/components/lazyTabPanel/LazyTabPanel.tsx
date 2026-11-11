import { Card, TabPanel } from "@twilio-paste/core";
import { PropsWithChildren, useRef } from "react";
import Loader from "../loaders/Loader";

interface LazyTabPanelProps extends PropsWithChildren {
    tabId: string;
    isActive: boolean;
}

const LazyTabPanel = ({ tabId, isActive, children }: LazyTabPanelProps) => {
    const hasLazyLoaded = useRef(false);

    if (isActive && hasLazyLoaded.current === false) {
        hasLazyLoaded.current = true;
    }

    return (
        <TabPanel tabId={tabId}>
            {hasLazyLoaded.current ? (
                children
            ) : (
                <Card>
                    <Loader />
                </Card>
            )}
        </TabPanel>
    );
};

export default LazyTabPanel;
