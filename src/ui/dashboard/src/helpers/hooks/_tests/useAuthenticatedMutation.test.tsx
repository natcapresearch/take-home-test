const mockPush = jest.fn();
const mockMutate = jest.fn();

jest.mock("@apollo/client", () => ({
    ...jest.requireActual("@apollo/client"),
    useMutation: () => [mockMutate, { loading: false }],
}));

jest.mock("../../../contexts/ToasterProvider", () => ({
    useAppToaster: () => ({ push: mockPush }),
}));

import { act, renderHook } from "@testing-library/react";
import {
    UpdateChangeSetDocument,
    UpdateChangeSetMutation,
} from "../../../../../common/__generated__/client-types";
import useAuthenticatedMutation, {
    MutationToastOptions,
} from "../useAuthenticatedMutation";

const updatedChangeSet = {
    __typename: "ChangeSet" as const,
    id: "cs-id",
    uid: "cs-1",
    name: "Renamed",
    description: null,
    state: "DONE",
    updatedAt: "2026-01-02T00:00:00Z",
};
const okResponse = { data: { updateChangeSet: updatedChangeSet } };
const variables = { orgUid: "org", changeSetUid: "cs-1", name: "Renamed" };

const run = async (
    hookOptions: MutationToastOptions<UpdateChangeSetMutation> = {},
    callOptions: MutationToastOptions<UpdateChangeSetMutation> = {},
) => {
    const { result } = renderHook(() =>
        useAuthenticatedMutation(UpdateChangeSetDocument, hookOptions),
    );
    let outcome;
    await act(async () => {
        outcome = await result.current[0]({ variables, ...callOptions });
    });
    return outcome;
};

describe("useAuthenticatedMutation", () => {
    let consoleError: jest.SpyInstance;

    beforeEach(() => {
        mockPush.mockClear();
        mockMutate.mockReset();
        consoleError = jest
            .spyOn(console, "error")
            .mockImplementation(() => undefined);
    });

    afterEach(() => {
        consoleError.mockRestore();
    });

    it("returns the success value and shows no toast by default", async () => {
        mockMutate.mockResolvedValue(okResponse);

        expect(await run()).toEqual({ success: true, data: updatedChangeSet });
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("does not pass toast options through to Apollo", async () => {
        mockMutate.mockResolvedValue(okResponse);

        await run({}, { errorMessage: "Nope", successMessage: "Yes" });

        expect(mockMutate).toHaveBeenCalledWith({ variables });
    });

    it("shows a success toast when given a successMessage", async () => {
        mockMutate.mockResolvedValue(okResponse);

        await run({ successMessage: "Version updated." });

        expect(mockPush).toHaveBeenCalledWith(
            expect.objectContaining({
                message: "Version updated.",
                variant: "success",
            }),
        );
    });

    it("passes toastId through as the toast id", async () => {
        mockMutate.mockRejectedValue(new Error("Failed to fetch"));

        await run({ toastId: "update-change-set-error" });

        expect(mockPush).toHaveBeenCalledWith(
            expect.objectContaining({ id: "update-change-set-error" }),
        );
    });

    it("shows an error toast for a ResultError", async () => {
        mockMutate.mockResolvedValue({
            data: {
                updateChangeSet: {
                    __typename: "ResultError",
                    message: "Forbidden",
                },
            },
        });

        const outcome = await run({ errorMessage: "Unable to update version" });

        expect(outcome).toMatchObject({ success: false, error: "Forbidden" });
        expect(mockPush).toHaveBeenCalledWith({
            id: undefined,
            message: "Unable to update version: Forbidden",
            variant: "error",
        });
    });

    it("shows an error toast when the mutation throws", async () => {
        mockMutate.mockRejectedValue(new Error("Failed to fetch"));

        const outcome = await run();

        expect(outcome).toMatchObject({
            success: false,
            error: "Failed to fetch",
        });
        expect(mockPush).toHaveBeenCalledWith({
            id: undefined,
            message: "Failed to fetch",
            variant: "error",
        });
    });

    it("shows no error toast when showErrorToast is false", async () => {
        mockMutate.mockRejectedValue(new Error("Failed to fetch"));

        const outcome = await run({ showErrorToast: false });

        expect(outcome).toMatchObject({ success: false });
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("lets call options override hook options", async () => {
        mockMutate.mockResolvedValue({ data: { updateChangeSet: null } });

        await run({ errorMessage: "From hook" }, { errorMessage: "From call" });

        expect(mockPush).toHaveBeenCalledWith(
            expect.objectContaining({
                message: expect.stringMatching(/^From call: /),
            }),
        );
    });
});
