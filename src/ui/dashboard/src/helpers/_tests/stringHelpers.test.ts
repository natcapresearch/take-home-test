import {
    capitalise,
    conditionalLowercase,
    deslugify,
    formatChangeSetNameForViewer,
    getFilename,
    isEmailValid,
    replaceDotsWithSpaces,
    slugifyForUrl,
    toTitleCase,
} from "../stringHelpers";

describe("stringHelpers - toTitleCase", () => {
    it("Should return string correctly as title case", () => {
        expect(toTitleCase("test string")).toBe("Test String");
    });
});

describe("stringHelpers - isEmailValid", () => {
    it("Should return false if string doesn't contain @", () => {
        expect(isEmailValid("laura.rollatnatcapresearch.com")).toBeFalsy();
    });

    it("Should return false if string doesn't contain .", () => {
        expect(isEmailValid("laura.roll@natcapresearchdotcom")).toBeFalsy();
    });

    it("Should return false if valid email.", () => {
        expect(isEmailValid("laura.roll@natcapresearch.com")).toBeTruthy();
    });
});

describe("stringHelpers - deslugify", () => {
    it("Should return string correctly without underscore", () => {
        expect(deslugify("test_string")).toBe("Test string");
    });
});

describe("stringHelpers - conditionalLowercase", () => {
    it.each`
        acronym         | result
        ${"tnfd"}       | ${"TNFD"}
        ${"csrd"}       | ${"CSRD"}
        ${"leap phase"} | ${"LEAP phase"}
        ${"esrs"}       | ${"ESRS"}
    `("Should uppercase acronyms appropriately", ({ acronym, result }) => {
        expect(conditionalLowercase(acronym)).toBe(result);
    });
});

describe("stringHelpers - replaceDotsWithSpaces", () => {
    it("Should replace dots with spaces", () => {
        expect(replaceDotsWithSpaces("test.string")).toBe("test string");
    });
});

describe("stringHelpers - capitalise", () => {
    it("Should capitalise a string", () => {
        expect(capitalise("test string")).toBe("Test string");
    });
});

describe("stringHelpers - slugifyForUrl", () => {
    it("Should return string correctly as a slug when contains slash", () => {
        expect(slugifyForUrl("test / string")).toBe("test-string");
        expect(slugifyForUrl("test/string")).toBe("test-string");
        expect(slugifyForUrl("test string / slash")).toBe("test_string-slash");
        expect(slugifyForUrl("test string/slash")).toBe("test_string-slash");
    });
});

describe("stringHelpers - getFilename", () => {
    it("Should return the filename without extension from a file path", () => {
        expect(getFilename("/path/to/file.txt")).toBe("file");
        expect(getFilename("/path/to/another/file.pdf")).toBe("file");
    });
});

describe("stringHelpers - formatChangeSetNameForViewer", () => {
    describe("ISO Z timestamp format (YYYY-MM-DDTHH:MM:SS.fffffZ)", () => {
        it("Should convert ISO Z at beginning", () => {
            expect(
                formatChangeSetNameForViewer("2024-01-15T10:30:45.123456Z"),
            ).toBe("2024-01-15 10:30AM");
        });

        it("Should convert ISO Z in middle of name", () => {
            expect(
                formatChangeSetNameForViewer(
                    "Version 2024-01-15T10:30:45.123456Z update",
                ),
            ).toBe("Version 2024-01-15 10:30AM update");
        });

        it("Should convert ISO Z at end", () => {
            expect(
                formatChangeSetNameForViewer(
                    "My Version 2024-01-15T10:30:45.123456Z",
                ),
            ).toBe("My Version 2024-01-15 10:30AM");
        });
    });

    describe("Slash timestamp format (YYYY-MM-DD/HH:MM:SS, treated as UTC)", () => {
        it("Should convert slash timestamp at beginning", () => {
            expect(formatChangeSetNameForViewer("2024-01-15/10:30:45")).toBe(
                "2024-01-15 10:30AM",
            );
        });

        it("Should convert slash timestamp in middle of name", () => {
            expect(
                formatChangeSetNameForViewer(
                    "Version 2024-01-15/10:30:45 update",
                ),
            ).toBe("Version 2024-01-15 10:30AM update");
        });

        it("Should convert slash timestamp at end", () => {
            expect(
                formatChangeSetNameForViewer("My Version 2024-01-15/10:30:45"),
            ).toBe("My Version 2024-01-15 10:30AM");
        });
    });
});
