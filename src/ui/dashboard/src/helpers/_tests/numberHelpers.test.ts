import {
    formatAmountWithFloor,
    formatNumberCompact,
    formatWithFloor,
} from "../numberHelpers";

describe("numberHelpers - formatAmountWithFloor", () => {
    it("shows amounts to 2 significant figures", () => {
        expect(formatAmountWithFloor(211_200)).toEqual({ display: "$210K" });
        expect(formatAmountWithFloor(760_900)).toEqual({ display: "$760K" });
        expect(formatAmountWithFloor(4.53)).toEqual({ display: "$4.5" });
        expect(formatAmountWithFloor(0.05)).toEqual({ display: "$0.05" });
        expect(formatAmountWithFloor(0)).toEqual({ display: "$0" });
    });

    it("shows <$0.1 for a positive amount under $0.05", () => {
        expect(formatAmountWithFloor(0.015)).toEqual({
            display: "<$0.1",
            tooltip: "$0.015",
        });
    });

    it("shows >-$0.1 for a negative amount above -$0.05", () => {
        expect(formatAmountWithFloor(-0.012)).toEqual({
            display: ">-$0.1",
            tooltip: "$-0.012",
        });
    });
});

describe("numberHelpers - formatWithFloor, event percentages", () => {
    it("shows 2 decimal places, keeping trailing zeros", () => {
        expect(formatWithFloor(1.2, 2, 5, "%")).toEqual({ display: "1.20%" });
        expect(formatWithFloor(0, 2, 5, "%")).toEqual({ display: "0.00%" });
    });

    it("adds thousands separators", () => {
        expect(formatWithFloor(1750000, 2, 5, "%")).toEqual({
            display: "1,750,000.00%",
        });
    });

    it("shows <0.01% for a value that rounds to zero, with 5 decimal places on hover", () => {
        expect(formatWithFloor(0.001, 2, 5, "%")).toEqual({
            display: "<0.01%",
            tooltip: "0.00100%",
        });
    });

    it("shows >-0.01% for a negative value that rounds to zero", () => {
        expect(formatWithFloor(-0.004, 2, 5, "%")).toEqual({
            display: ">-0.01%",
            tooltip: "-0.00400%",
        });
    });

    it("rounds a value at the threshold up", () => {
        expect(formatWithFloor(0.005, 2, 5, "%")).toEqual({ display: "0.01%" });
    });

    it("shows -0 as 0.00%", () => {
        expect(formatWithFloor(-0, 2, 5, "%")).toEqual({ display: "0.00%" });
    });
});

describe("numberHelpers - formatWithFloor, event values", () => {
    it("shows 2 decimal places without a % sign", () => {
        expect(formatWithFloor(1.6, 2, 5)).toEqual({ display: "1.60" });
        expect(formatWithFloor(0.0004, 2, 5)).toEqual({
            display: "<0.01",
            tooltip: "0.00040",
        });
    });
});

describe("numberHelpers - formatWithFloor, financial percentages", () => {
    it("shows 1 decimal place, keeping trailing zeros", () => {
        expect(formatWithFloor(1, 1, 2, "%")).toEqual({ display: "1.0%" });
        expect(formatWithFloor(0, 1, 2, "%")).toEqual({ display: "0.0%" });
    });

    it("shows <0.1% for a value that rounds to zero, with 2 decimal places on hover", () => {
        expect(formatWithFloor(0.04, 1, 2, "%")).toEqual({
            display: "<0.1%",
            tooltip: "0.04%",
        });
    });

    it("shows >-0.1% for a negative value that rounds to zero", () => {
        expect(formatWithFloor(-0.04, 1, 2, "%")).toEqual({
            display: ">-0.1%",
            tooltip: "-0.04%",
        });
    });
});

describe("numberHelpers - formatNumberCompact", () => {
    it("abbreviates to 1 decimal place by default", () => {
        expect(formatNumberCompact(13_400)).toBe("13.4K");
    });

    it("abbreviates to the given significant figures", () => {
        expect(formatNumberCompact(950, 2)).toBe("950");
        expect(formatNumberCompact(1234, 2)).toBe("1.2K");
        expect(formatNumberCompact(380_000, 2)).toBe("380K");
        expect(formatNumberCompact(2_300_000, 2)).toBe("2.3M");
        expect(formatNumberCompact(13_400_000, 2)).toBe("13M");
        expect(formatNumberCompact(1_200_000_000, 2)).toBe("1.2B");
    });
});
