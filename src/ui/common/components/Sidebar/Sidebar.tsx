import {
    Badge,
    Box,
    SidebarBody,
    SidebarCollapseButton,
    SidebarFooter,
    SidebarHeader,
    SidebarHeaderIconButton,
    SidebarHeaderLabel,
    SidebarNavigation,
    SidebarNavigationDisclosure,
    SidebarNavigationDisclosureContent,
    SidebarNavigationDisclosureHeading,
    SidebarNavigationDisclosureHeadingWrapper,
    SidebarNavigationItem,
    Sidebar as TwilioSidebar,
} from "@twilio-paste/core";
import { useHref, useLinkClickHandler } from "react-router-dom";
import UserDialog from "../../../dashboard/src/components/appBar/UserDialog";
import { useAppContext } from "../../../dashboard/src/contexts/AppProvider";
import {
    usePathIsMatch,
    usePathIsPartialMatch,
} from "../../../dashboard/src/helpers/navHelpers";
import { Maybe } from "../../__generated__/client-types";
import logo from "../../theme/assets/logo/logomark/logomark-talcum@2x.png";
import { NavItem, NavItemLink, NavItemParent } from "../../types";

interface SidebarProps {
    navItems: NavItem[];
    /** Shown in the sidebar header next to the logo */
    orgName?: Maybe<string>;
    isSidebarCollapsed: boolean;
    setIsSidebarCollapsed: (isSidebarCollapsed: boolean) => void;
}

const Sidebar = ({
    navItems,
    orgName,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
}: SidebarProps) => {
    const homepage = useHref("/");
    const { viewer } = useAppContext();

    const onSidebarButtonClick = () => {
        setIsSidebarCollapsed(!isSidebarCollapsed);
    };

    return (
        <TwilioSidebar
            sidebarNavigationSkipLinkID=""
            topbarSkipLinkID=""
            mainContentSkipLinkID=""
            variant="compact"
            collapsed={isSidebarCollapsed}
        >
            <SidebarHeader>
                <SidebarHeaderIconButton as="a" href={homepage}>
                    <Box as="div" size="sizeIcon40" display="flex">
                        <img
                            src={logo}
                            alt="Go to platform homepage"
                            width="size80"
                        />
                    </Box>
                </SidebarHeaderIconButton>
                {!isSidebarCollapsed && (
                    <SidebarHeaderLabel>
                        {orgName ?? "Platform"}
                    </SidebarHeaderLabel>
                )}
            </SidebarHeader>

            <SidebarBody>
                <SidebarNavigation
                    aria-label="main navigation"
                    hierarchical={!isSidebarCollapsed}
                >
                    {!isSidebarCollapsed &&
                        navItems.map((navItem, i) => (
                            <SidebarNavItem key={i} navItem={navItem} />
                        ))}
                </SidebarNavigation>
            </SidebarBody>

            <SidebarFooter>
                <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                >
                    {!isSidebarCollapsed && <UserDialog viewer={viewer} />}

                    <SidebarCollapseButton
                        onClick={onSidebarButtonClick}
                        i18nCollapseLabel="Close sidebar"
                        i18nExpandLabel="Open sidebar"
                    />
                </Box>
            </SidebarFooter>
        </TwilioSidebar>
    );
};

interface SidebarNavItemProps {
    navItem: NavItem;
}

function SidebarNavItem({ navItem }: SidebarNavItemProps) {
    if ("children" in navItem) {
        return <SidebarNavItemParent navItem={navItem} />;
    }

    return <SidebarNavItemLink item={navItem} />;
}

interface SidebarNavItemParentProps {
    navItem: NavItemParent;
}

function SidebarNavItemParent({ navItem }: SidebarNavItemParentProps) {
    const isChildSelected = usePathIsPartialMatch(navItem.rootPath);

    return (
        <SidebarNavigationDisclosure visible={isChildSelected}>
            <SidebarNavigationDisclosureHeadingWrapper>
                <SidebarNavigationDisclosureHeading
                    icon={navItem.icon}
                    selected={isChildSelected}
                >
                    {navItem.title}
                </SidebarNavigationDisclosureHeading>
            </SidebarNavigationDisclosureHeadingWrapper>
            <SidebarNavigationDisclosureContent>
                {navItem.children.map((childItem, i) => (
                    <SidebarNavItem key={i} navItem={childItem} />
                ))}
            </SidebarNavigationDisclosureContent>
        </SidebarNavigationDisclosure>
    );
}

function SidebarNavItemLink({ item }: { item: NavItemLink }) {
    // Hrefs may carry a query string; match on the path only
    const pathname = item.href.split("?")[0];
    const patchIsPartialMatch = usePathIsPartialMatch(pathname);
    const pathIsMatch = usePathIsMatch(pathname);
    const linkClickHandler = useLinkClickHandler(useHref(item.href));

    const selected = item.isSelectedForSubRoutes
        ? patchIsPartialMatch
        : pathIsMatch;

    return (
        <SidebarNavigationItem
            selected={selected}
            icon={item.icon}
            onClick={linkClickHandler}
            href={item.href}
        >
            {item.title}
            {item.isBeta && (
                <Badge as="span" variant="decorative40">
                    Beta
                </Badge>
            )}
        </SidebarNavigationItem>
    );
}

export default Sidebar;
