import { createContext, PropsWithChildren, useContext } from "react";
import {
    ApplicationConfig,
    User,
} from "../../../common/__generated__/client-types";

export interface AppContextValue extends ApplicationConfig {
    /** The signed-in user, from the bootstrap query. */
    viewer?: Pick<User, "id" | "email" | "nickname"> | null;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

interface AppProviderProps extends PropsWithChildren {
    config?: ApplicationConfig;
    viewer?: AppContextValue["viewer"];
}

function AppProvider({ config, viewer, children }: AppProviderProps) {
    const context: AppContextValue = {
        ...(config || {}),
        viewer,
    };

    return (
        <AppContext.Provider value={context}>{children}</AppContext.Provider>
    );
}

export function useAppContext() {
    const context = useContext(AppContext);

    if (!context) {
        throw new Error("useAppContext is only available inside AppProvider");
    }

    return context;
}

export default AppProvider;
