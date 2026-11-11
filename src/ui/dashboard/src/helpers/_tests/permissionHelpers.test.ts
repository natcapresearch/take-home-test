import {
    hasAllPermissions,
    hasAnyPermission,
    hasPermission,
} from "../permissionHelpers";

describe("permissionHelpers - hasPermission", () => {
    it("should return false if permissionSet is null", () => {
        expect(hasPermission(null, "scope")).toBe(false);
    });

    it("should return false if permissionSet.__typename is not 'PermissionSet'", () => {
        const permissionSet = {
            __typename: "ResultError" as const,
            message: "Something went wrong",
        };
        expect(hasPermission(permissionSet, "scope")).toBe(false);
    });

    it("should return false if scope is not in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["otherScope"],
        };
        expect(hasPermission(permissionSet, "scope")).toBe(false);
    });

    it("should return true if scope is in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["scope"],
        };
        expect(hasPermission(permissionSet, "scope")).toBe(true);
    });
});

describe("permissionHelpers - hasAnyPermission", () => {
    it("should return false if none of the scopes are in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["otherScope"],
        };
        expect(hasAnyPermission(permissionSet, ["scope1", "scope2"])).toBe(
            false,
        );
    });

    it("should return true if any of the scopes are in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["scope1"],
        };
        expect(hasAnyPermission(permissionSet, ["scope1", "scope2"])).toBe(
            true,
        );
    });
});

describe("permissionHelpers - hasAllPermissions", () => {
    it("should return false if not all of the scopes are in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["scope1"],
        };
        expect(hasAllPermissions(permissionSet, ["scope1", "scope2"])).toBe(
            false,
        );
    });

    it("should return true if all of the scopes are in permissionSet.scopes", () => {
        const permissionSet = {
            __typename: "PermissionSet" as const,
            scopes: ["scope1", "scope2"],
        };
        expect(hasAllPermissions(permissionSet, ["scope1", "scope2"])).toBe(
            true,
        );
    });
});
