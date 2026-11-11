import {
    SideModal,
    SideModalContainer,
    SideModalProps,
    SideModalStateReturn,
} from "@twilio-paste/core";
import { useEffect, useMemo, useRef } from "react";

// Paste renders SideModal, Popover, Menu, Tooltip and Toaster content into
// reakit portals, and Modal content into a reach portal. A press inside one of
// these belongs to an overlay, not to the page behind the side modal.
const PASTE_PORTAL_SELECTOR = ".__reakit-portal, reach-portal";

interface DismissibleSideModalProps extends SideModalProps {
    state: SideModalStateReturn;
    // Called instead of state.hide when the user closes the panel by pressing
    // outside it, the close button or Escape.
    onRequestClose?: () => void;
}

/**
 * Paste's SideModal hardcodes hideOnClickOutside: false. This renders
 * SideModalContainer and SideModal and closes the panel when the user presses
 * outside it. The close button and Escape keep Paste's behaviour, and all
 * three go through onRequestClose when it is given.
 */
const DismissibleSideModal = ({
    state,
    onRequestClose,
    children,
    ...sideModalProps
}: DismissibleSideModalProps) => {
    const panelRef = useRef<HTMLDivElement>(null);
    const { visible, hide } = state;
    const requestClose = onRequestClose ?? hide;

    // SideModalHeader's close button and the Escape handler both call hide
    // from the state passed to SideModalContainer.
    const containerState = useMemo(
        () => ({ ...state, hide: requestClose }),
        [state, requestClose],
    );

    useEffect(() => {
        if (!visible) return;

        const handlePointerDown = (event: PointerEvent) => {
            const { target } = event;
            if (!(target instanceof Element)) return;
            // The app theme draws the backdrop as a ::before on the panel's
            // outer container, so a press on the backdrop targets the
            // container itself. Panel content always sits in a child element.
            if (target === panelRef.current) {
                requestClose();
                return;
            }
            if (panelRef.current?.contains(target)) return;
            if (target.closest(PASTE_PORTAL_SELECTOR)) return;
            requestClose();
        };

        document.addEventListener("pointerdown", handlePointerDown);
        return () =>
            document.removeEventListener("pointerdown", handlePointerDown);
    }, [visible, requestClose]);

    return (
        <SideModalContainer state={containerState}>
            <SideModal ref={panelRef} {...sideModalProps}>
                {children}
            </SideModal>
        </SideModalContainer>
    );
};

export default DismissibleSideModal;
