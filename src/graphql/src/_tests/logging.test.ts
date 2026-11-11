import { cleanParameters } from "../logging";

describe("logging filter", () => {
    it("should filter out sensitive data with mutations", () => {
        const input_params = {
            password: "password",
            orgUuid: "this-is-a-fake-uuid",
            email: "wibble@example.com",
        };
        const result = cleanParameters(input_params, "mutation");
        expect(result).toEqual({
            password: "[REDACTED]",
            orgUuid: "this-is-a-fake-uuid",
            email: "[REDACTED]",
        });
    });
    it("should not filter out sensitive data with queries", () => {
        const input_params = {
            password: "password",
            orgUuid: "this-is-a-fake-uuid",
            email: "wibble@example.com",
        };
        const result = cleanParameters(input_params, "query");
        expect(result).toEqual({
            password: "password",
            orgUuid: "this-is-a-fake-uuid",
            email: "wibble@example.com",
        });
    });
});
