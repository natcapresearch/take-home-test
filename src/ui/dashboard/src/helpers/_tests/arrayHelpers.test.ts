import { insertIf } from "../arrayHelpers";

describe("arrayHelpers - insertIf", () => {
    it("Should only insert items into the array if the condition is true", () => {
        const item1 = { name: "name1" };
        const item2 = { name: "name2" };
        const item3 = { name: "name3" };

        const objArray = [
            ...insertIf(true, item1),
            ...insertIf(false, item2),
            item3,
        ];

        expect(objArray).toEqual([item1, item3]);
        expect(objArray).not.toContain(item2);
    });
});
