import { PropsWithChildren, createContext, useContext } from "react";
import { useHref } from "react-router-dom";

const BasenameContext = createContext<string | undefined>(undefined);

interface BasenameContextProps extends PropsWithChildren {
    basename: string;
}

export function BasenameProvider({ basename, children }: BasenameContextProps) {
    // Ensure basename doesn't end with a slash (since we'll be joining to
    // an absolute pathname, starting with a slash)
    basename = basename.endsWith("/") ? basename.slice(0, -1) : basename;

    return (
        <BasenameContext.Provider value={basename}>
            {children}
        </BasenameContext.Provider>
    );
}

/**
 * Prefixes a pathname with a basename, set by the Basename context. This is
 * useful when creating absolute pathnames relative to /o/:orgId (i.e. a child
 * route of OrganisationApp).
 *
 * An error is thrown if used outside of this context, since it doesn't have a
 * basename to prefix with.
 *
 * @param pathname The pathname to be prefixed with the basename
 * @returns The prefixed pathname
 */
export function useBasename(pathname: string) {
    const basename = useContext(BasenameContext);

    if (basename === undefined) {
        throw new Error(
            "You cannot use useBasename outside of the BasenameContext Provider. It is restricted to routes that are children of <OrganisationApp>, since absolute pathnames need to be nested under an Organisation's id.",
        );
    }

    // Ensure pathname is prefixed with a slash
    pathname = pathname.startsWith("/") ? pathname : `/${pathname}`;

    return `${basename}${pathname}`;
}

/**
 * Prefixes a pathname with a basename, set by the Basename context and wraps
 * with the React Router useHref hook. This is useful when creating absolute
 * pathnames relative to /o/:orgId (i.e. a child route of OrganisationApp) and
 * then using in a non-React-Router-aware component like Paste's <Anchor>.
 *
 * An error is thrown if used outside of this context, since it doesn't have a
 * basename to prefix with.
 *
 * @param pathname The pathname to be prefixed with the basename and wrapped with useHref
 * @returns The prefixed and wrapped pathname
 */
export function useHrefWithBasename(pathname: string) {
    // Wrap with useHref to allow for currently loaded router
    return useHref(useBasename(pathname));
}
