/**
 * Typed wrapper around `Object.keys()` that narrows the return type to `(keyof T)[]`.
 *
 * ⚠️ This assumes that, at runtime, the object does not have any keys beyond `keyof T`.
 * In other words, only use this for objects whose *actual* keys are known to match
 * their TypeScript type (e.g. carefully-constructed domain objects or Records where
 * all values share the same type).
 *
 * For arbitrary or loosely typed objects, prefer `Object.keys()` directly, or keep
 * the `string[]` result, because this helper is not sound in the general case.
 *
 * @template T - The object type to extract keys from.
 * @param obj - The object whose own enumerable string keys are to be returned.
 * @returns An array of keys typed as `(keyof T)[]`.
 */
export function typedKeys<T extends object>(obj: T): (keyof T)[] {
    return Object.keys(obj) as (keyof T)[];
}

/**
 * Type guard that narrows an unknown value to a plain record object.
 *
 * Returns `true` if the input is a non-null object (excluding primitives),
 * and `false` otherwise. Useful for safely narrowing generic `unknown`
 * values before performing object operations.
 *
 * @param x - The value to test.
 * @returns `true` if `x` is a non-null object, otherwise `false`.
 */
function isRecord(x: unknown): x is Record<string, unknown> {
    return x !== null && typeof x === "object";
}

/**
 * Perform a shallow equality check between two values.
 *
 * - Returns `true` if both values are referentially equal via `Object.is()`.
 * - If both are plain objects, compares their keys and ensures each
 *   corresponding value is referentially equal.
 * - Returns `false` for nulls, non-objects, mismatched key sets,
 *   or any differing value.
 *
 * Intended for use in lightweight comparisons where deep equality
 * is unnecessary—e.g. detecting structural equality in React state updates.
 *
 * @param a - The first value to compare.
 * @param b - The second value to compare.
 * @returns `true` if the values are shallowly equal, otherwise `false`.
 */
export function shallowEqual(a: unknown, b: unknown): boolean {
    if (Object.is(a, b)) return true;
    if (!isRecord(a) || !isRecord(b)) return false;

    const kA = Object.keys(a);
    const kB = Object.keys(b);
    if (kA.length !== kB.length) return false;

    for (const k of kA) {
        if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
        if (!Object.is(a[k], b[k])) return false;
    }
    return true;
}
