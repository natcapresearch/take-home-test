import {
    Toaster,
    useToaster,
    UseToasterReturnedProps,
} from "@twilio-paste/core";
import {
    createContext,
    PropsWithChildren,
    useCallback,
    useContext,
    useMemo,
    useRef,
} from "react";

/** The app-wide toaster: push a toast to it with `useAppToaster().push`. */
export interface AppToaster {
    push: UseToasterReturnedProps["push"];
}

const ToasterContext = createContext<AppToaster | undefined>(undefined);

/**
 * Renders the app's only `<Toaster>`. Every toast goes through it, via
 * `useAppToaster`, so toasts survive navigation and never stack on top of a
 * second toaster. `useAuthenticatedMutation` pushes mutation error and success
 * toasts here.
 */
export function ToasterProvider({ children }: PropsWithChildren) {
    const toaster = useToaster();

    // Paste's `push` is recreated on every render. Expose a stable one so
    // consumers do not re-render, or re-run effects, whenever a toast changes.
    const pushRef = useRef(toaster.push);
    pushRef.current = toaster.push;
    const push = useCallback<AppToaster["push"]>(
        (toast) => pushRef.current(toast),
        [],
    );
    const value = useMemo(() => ({ push }), [push]);

    return (
        <ToasterContext.Provider value={value}>
            <Toaster left={["space40", "unset", "unset"]} {...toaster} />
            {children}
        </ToasterContext.Provider>
    );
}

export function useAppToaster() {
    const context = useContext(ToasterContext);
    if (!context) {
        throw new Error("useAppToaster must be used within a ToasterProvider");
    }
    return context;
}
