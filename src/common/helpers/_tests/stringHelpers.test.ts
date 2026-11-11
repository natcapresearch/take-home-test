import { slugify } from "../stringHelpers";

describe("stringHelpers - slugify", () => {
    it("Should return string correctly as a slug", () => {
        expect(slugify("test string")).toBe("test_string");
    });
});
