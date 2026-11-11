import {
    Maybe,
    PermissionSet,
    PermissionSetResult,
} from "../../../common/__generated__/client-types";
import { valueFromResult } from "./graphqlHelpers";

/**
 * Check if the user has a specific permission.
 * @param permissionSet The permission set of the user.
 * @param scope The scope to check.
 * @returns True if the user has the permission, false otherwise.
 */
export function hasPermission(
    permissionSet: Maybe<PermissionSetResult> | undefined,
    scope: string,
): boolean {
    const set = valueFromResult<PermissionSet>("PermissionSet", permissionSet);
    return set?.scopes?.includes(scope) ?? false;
}

/**
 * Check if the user has any of the permissions.
 * @param permissionSet The permission set of the user.
 * @param scopes The scopes to check.
 * @returns True if the user has any of the permissions, false otherwise.
 */
export function hasAnyPermission(
    permissionSet: Maybe<PermissionSetResult> | undefined,
    scopes: string[],
): boolean {
    return scopes.some((scope) => hasPermission(permissionSet, scope));
}

/**
 * Check if the user has all of the permissions.
 * @param permissionSet The permission set of the user.
 * @param scopes The scopes to check.
 * @returns True if the user has all of the permissions, false otherwise.
 */
export function hasAllPermissions(
    permissionSet: Maybe<PermissionSetResult> | undefined,
    scopes: string[],
): boolean {
    return scopes.every((scope) => hasPermission(permissionSet, scope));
}
