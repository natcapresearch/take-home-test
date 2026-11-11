export const insertIf = <T>(
    condition?: boolean | Promise<boolean>,
    ...elements: T[]
) => (condition ? elements : []);

export const pushIfDefined = <T>(arr: T[], value?: T | null) => {
    if (value != null && !arr.includes(value)) {
        arr.push(value);
    }
};

export const insertAt = <T>(arr: T[], index: number, item: T): T[] => [
    ...arr.slice(0, index),
    item,
    ...arr.slice(index),
];

export const areStringArraysEqual = (a: string[], b: string[]) =>
    a.length === b.length && a.every((value, index) => value === b[index]);
