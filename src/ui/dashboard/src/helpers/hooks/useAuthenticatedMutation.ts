import {
    MutationFunctionOptions,
    MutationHookOptions,
    MutationResult,
    OperationVariables,
    useMutation,
} from "@apollo/client";
import { getOperationName } from "@apollo/client/utilities";
import { TypedDocumentNode } from "@graphql-typed-document-node/core";
import { useCallback, useRef } from "react";
import { useAppToaster } from "../../contexts/ToasterProvider";
import {
    MutationData,
    MutationOutcomeOf,
    runMutation,
} from "../mutationHelpers";

/** How a mutation reports its outcome to the user. */
export interface MutationToastOptions<TData> {
    /**
     * Push an error toast on failure. Defaults to true; turn it off where the
     * caller shows the error itself, e.g. inline in a form or modal.
     */
    showErrorToast?: boolean;
    /** Error toast text, followed by the failure reason. */
    errorMessage?: string;
    /** Success toast text. No success toast is shown without it. */
    successMessage?: string | ((data: MutationData<TData>) => string);
    /**
     * Id for the toast. Paste replaces a toast with the same id rather than
     * stacking another, e.g. when the user retries after an error.
     */
    toastId?: string;
}

export type AuthenticatedMutationOptions<
    TData,
    TVariables extends OperationVariables,
> = MutationHookOptions<TData, TVariables> & MutationToastOptions<TData>;

/**
 * Runs the mutation. Never rejects: every failure resolves to
 * `{ success: false, error }` (see `runMutation`).
 * Toast options passed here override those passed to the hook.
 */
export type SafeMutationFunction<
    TData,
    TVariables extends OperationVariables,
> = (
    options?: MutationFunctionOptions<TData, TVariables> &
        MutationToastOptions<TData>,
) => Promise<MutationOutcomeOf<TData>>;

export default function useAuthenticatedMutation<
    TData,
    TVariables extends OperationVariables = OperationVariables,
>(
    mutation: TypedDocumentNode<TData, TVariables>,
    options: AuthenticatedMutationOptions<TData, TVariables> = {},
): [SafeMutationFunction<TData, TVariables>, MutationResult<TData>] {
    const {
        showErrorToast = true,
        errorMessage,
        successMessage,
        toastId,
        ...hookOptions
    } = options;
    const { push } = useAppToaster();

    // Read at call time, so inline options do not make `safeMutate` unstable.
    const toastOptionsRef = useRef({
        showErrorToast,
        errorMessage,
        successMessage,
        toastId,
    });
    toastOptionsRef.current = {
        showErrorToast,
        errorMessage,
        successMessage,
        toastId,
    };

    const [mutate, response] = useMutation<TData, TVariables>(mutation, {
        errorPolicy: "all",
        awaitRefetchQueries: true,
        ...hookOptions,
    });

    const operationName = getOperationName(mutation) ?? "UnnamedMutation";
    const safeMutate = useCallback<SafeMutationFunction<TData, TVariables>>(
        async (callOptions = {}) => {
            const defaults = toastOptionsRef.current;
            const {
                showErrorToast: showErrorToastForCall = defaults.showErrorToast,
                errorMessage: errorMessageForCall = defaults.errorMessage,
                successMessage: successMessageForCall = defaults.successMessage,
                toastId: toastIdForCall = defaults.toastId,
                ...mutateOptions
            } = callOptions;

            const outcome = await runMutation<TData>(operationName, () =>
                mutate(mutateOptions),
            );

            if (!outcome.success) {
                if (showErrorToastForCall) {
                    push({
                        id: toastIdForCall,
                        message: errorMessageForCall
                            ? `${errorMessageForCall}: ${outcome.error}`
                            : outcome.error,
                        variant: "error",
                    });
                }
            } else if (successMessageForCall) {
                push({
                    id: toastIdForCall,
                    message:
                        typeof successMessageForCall === "function"
                            ? successMessageForCall(outcome.data)
                            : successMessageForCall,
                    variant: "success",
                    dismissAfter: 5000,
                });
            }

            return outcome;
        },
        [mutate, operationName, push],
    );

    return [safeMutate, response];
}
