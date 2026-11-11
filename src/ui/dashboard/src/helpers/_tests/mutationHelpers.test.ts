import {
    errorMessageFromOutcome,
    runMutation,
    UNKNOWN_MUTATION_ERROR,
} from "../mutationHelpers";

type TestMutation = {
    doThing?:
        | { __typename?: "OkResult"; ok: boolean }
        | { __typename?: "ResultError"; message: string }
        | null;
};

const ok = { __typename: "OkResult" as const, ok: true };

describe("runMutation", () => {
    let consoleError: jest.SpyInstance;

    beforeEach(() => {
        consoleError = jest
            .spyOn(console, "error")
            .mockImplementation(() => undefined);
    });

    afterEach(() => {
        consoleError.mockRestore();
    });

    it("returns the root field's value on success", async () => {
        const outcome = await runMutation<TestMutation>(
            "DoThing",
            async () => ({
                data: { doThing: ok },
            }),
        );

        expect(outcome).toEqual({ success: true, data: ok });
        expect(consoleError).not.toHaveBeenCalled();
    });

    it("fails with the ResultError's message, keeping the error", async () => {
        const resultError = {
            __typename: "ResultError" as const,
            message: "Forbidden",
        };

        const outcome = await runMutation<TestMutation>(
            "DoThing",
            async () => ({
                data: { doThing: resultError },
            }),
        );

        expect(outcome).toEqual({
            success: false,
            error: "Forbidden",
            resultError,
        });
        expect(consoleError).toHaveBeenCalledTimes(1);
    });

    it("fails with the first GraphQL error's message", async () => {
        const outcome = await runMutation<TestMutation>(
            "DoThing",
            async () => ({
                data: { doThing: null },
                errors: [{ message: "Boom" }],
            }),
        );

        expect(outcome).toMatchObject({ success: false, error: "Boom" });
    });

    it("fails with the unknown error when the root field is missing", async () => {
        const outcome = await runMutation<TestMutation>(
            "DoThing",
            async () => ({
                data: { doThing: null },
            }),
        );

        expect(outcome).toMatchObject({
            success: false,
            error: UNKNOWN_MUTATION_ERROR,
        });
    });

    it("fails with the thrown error's message", async () => {
        const outcome = await runMutation<TestMutation>("DoThing", async () => {
            throw new Error("Failed to fetch");
        });

        expect(outcome).toMatchObject({
            success: false,
            error: "Failed to fetch",
        });
    });
});

describe("errorMessageFromOutcome", () => {
    it("is null on success", () => {
        expect(
            errorMessageFromOutcome({ success: true, data: ok }, "Failed"),
        ).toBeNull();
    });

    it("prefixes the failure reason", () => {
        expect(
            errorMessageFromOutcome(
                { success: false, error: "Forbidden" },
                "Failed to publish",
            ),
        ).toBe("Failed to publish: Forbidden");
    });
});
