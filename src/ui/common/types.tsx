import { PageId } from "../dashboard/src/types/uiIdentifiers";

export type NavItem = NavItemLink | NavItemParent;

export interface NavItemParent {
    title: string;
    icon?: React.ReactNode;
    rootPath: string;
    children: NavItem[];
}

export interface NavItemLink {
    title: string;
    icon?: React.ReactNode;
    href: string;
    /** Allows a NavItemLink to be selected when on a "sub routes", e.g. Site should be selected for /site and /site/:siteSlug */
    isSelectedForSubRoutes?: boolean;
    isBeta?: boolean;
    pageId: PageId;
}
