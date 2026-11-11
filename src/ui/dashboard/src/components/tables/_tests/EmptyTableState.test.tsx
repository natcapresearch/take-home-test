import { render, screen } from "@testing-library/react";
import { MockBase } from "../../../helpers/testHelpers/testHelpers";
import { EmptyTableState } from "../EmptyTableState";

const renderEmptyTableState = () => {
    return render(
        <MockBase>
            <EmptyTableState />
        </MockBase>,
    );
};

describe("EmptyTableState", () => {
    it("explains that no results matched the filters", async () => {
        renderEmptyTableState();
        expect(screen.getByText("No results found")).toBeDefined();
        expect(
            screen.getByText(/modify your filter selection/),
        ).toBeInTheDocument();
    });
});
