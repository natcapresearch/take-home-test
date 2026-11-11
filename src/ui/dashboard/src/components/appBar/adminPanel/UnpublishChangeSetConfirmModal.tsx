import {
    Alert,
    Box,
    Button,
    Modal,
    ModalBody,
    ModalFooter,
    ModalFooterActions,
    ModalHeader,
    ModalHeading,
} from "@twilio-paste/core";
import { useEffect, useState } from "react";
import {
    AdminPanelChangeSetsDocument,
    ChangeSet,
    ChangeSetState,
    UpdateChangeSetDocument,
} from "../../../../../common/__generated__/client-types";
import useAuthenticatedMutation from "../../../helpers/hooks/useAuthenticatedMutation";
import { ModalId } from "../../../types/uiIdentifiers";

interface UnpublishChangeSetConfirmModalProps {
    changeSet: ChangeSet;
    isOpen: boolean;
    onDismiss: () => void;
}

const UnpublishChangeSetConfirmModal = ({
    changeSet,
    isOpen,
    onDismiss,
}: UnpublishChangeSetConfirmModalProps) => {
    const [errorMessage, setErrorMessage] = useState<string | undefined>(
        undefined,
    );

    useEffect(() => {
        if (!isOpen) {
            setErrorMessage(undefined);
        }
    }, [isOpen, changeSet.uid]);

    const [updateChangeSet, { loading }] = useAuthenticatedMutation(
        UpdateChangeSetDocument,
        {
            showErrorToast: false,
            refetchQueries: [
                {
                    query: AdminPanelChangeSetsDocument,
                    variables: { orgUid: changeSet.orgUid },
                },
            ],
        },
    );

    const handleUnpublish = async () => {
        const outcome = await updateChangeSet({
            variables: {
                orgUid: changeSet.orgUid,
                changeSetUid: changeSet.uid,
                state: ChangeSetState.Done,
            },
        });

        if (!outcome.success) {
            setErrorMessage(`Failed to unpublish version: ${outcome.error}`);
            return;
        }

        onDismiss();
    };

    const isLoading = loading;
    const hasError = Boolean(errorMessage);

    return (
        <Modal
            ariaLabelledby={ModalId.UnpublishChangeSet}
            isOpen={isOpen}
            onDismiss={isLoading ? () => undefined : onDismiss}
            size="default"
        >
            <ModalHeader>
                <ModalHeading id={ModalId.UnpublishChangeSet}>
                    Unpublish version {changeSet.name}
                </ModalHeading>
            </ModalHeader>
            <ModalBody>
                <Box display="flex" flexDirection="column" rowGap="space50">
                    <Box>
                        This will make the version{" "}
                        <strong>{changeSet.name}</strong> unavailable to all
                        users. Are you sure you want to continue?
                    </Box>

                    {errorMessage && (
                        <Alert variant="error">{errorMessage}</Alert>
                    )}
                </Box>
            </ModalBody>
            <ModalFooter>
                <ModalFooterActions>
                    <Button
                        variant="secondary"
                        onClick={onDismiss}
                        disabled={isLoading}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={handleUnpublish}
                        loading={isLoading}
                        disabled={isLoading}
                    >
                        {hasError ? "Try again" : "Unpublish"}
                    </Button>
                </ModalFooterActions>
            </ModalFooter>
        </Modal>
    );
};

export default UnpublishChangeSetConfirmModal;
