import { Badge, Box, Card, DetailText } from "@twilio-paste/core";
import { format } from "date-fns";
import {
    ChangeSet,
    Maybe,
} from "../../../../../common/__generated__/client-types";
import {
    dateTimeFormat,
    formatChangeSetNameForViewer,
} from "../../../helpers/stringHelpers";
import SectionHeading from "../../layout/typography/SectionHeading";
import { changeSetStatusToBadge } from "./badgeHelpers";

interface ChangeSetHistoryRowProps {
    changeSet: ChangeSet;
    selectedChangeSetUid?: Maybe<string>;
    onSelectChangeSet: (changeSetUid: string) => Promise<void>;
}

const ChangeSetHistoryRow = ({
    changeSet,
    selectedChangeSetUid,
    onSelectChangeSet,
}: ChangeSetHistoryRowProps) => {
    const isSelected = selectedChangeSetUid === changeSet.uid;
    const changeSetName =
        formatChangeSetNameForViewer(changeSet.name) ?? changeSet.name;

    const handleSelect = () => {
        void onSelectChangeSet(changeSet.uid);
    };

    return (
        <Box
            as="button"
            type="button"
            cursor="pointer"
            onClick={handleSelect}
            borderRadius="borderRadius30"
            width="100%"
            border="none"
            padding="space0"
            textAlign="left"
            aria-pressed={isSelected}
            aria-label={`Select version ${changeSetName}`}
        >
            <Card element={isSelected ? "ACTIVE_CARD" : undefined}>
                <Box
                    display="grid"
                    gridTemplateColumns="minmax(0, 1fr) auto"
                    columnGap="space80"
                    alignItems="start"
                    width="100%"
                >
                    <Box minWidth="size0">
                        <Box
                            display="flex"
                            alignItems="center"
                            columnGap="space40"
                            marginBottom="space30"
                            flexWrap="wrap"
                        >
                            <Box fontWeight="fontWeightSemibold">
                                {changeSetName}
                            </Box>

                            <Badge
                                as="span"
                                variant={
                                    changeSetStatusToBadge[changeSet.state]
                                        .variant
                                }
                            >
                                {changeSetStatusToBadge[changeSet.state].text}
                            </Badge>
                        </Box>

                        <DetailText element="DETAIL_TEXT_NO_MARGIN">
                            {changeSet.description
                                ? formatChangeSetNameForViewer(
                                      changeSet.description,
                                  )
                                : changeSet.description}
                        </DetailText>

                        <DetailText element="DETAIL_TEXT_NO_MARGIN">
                            {format(
                                new Date(changeSet.updatedAt),
                                dateTimeFormat,
                            )}
                            {changeSet.parentChangeSet &&
                                ` · from ${
                                    changeSet.parentChangeSet.name
                                        ? formatChangeSetNameForViewer(
                                              changeSet.parentChangeSet.name,
                                          )
                                        : changeSet.parentChangeSet.uid
                                }`}
                        </DetailText>
                    </Box>
                </Box>
            </Card>
        </Box>
    );
};

interface ChangeSetHistoryProps {
    changeSets: ChangeSet[];
    selectedChangeSetUid?: Maybe<string>;
    onSelectChangeSet: (changeSetUid: string) => Promise<void>;
}

const ChangeSetHistory = ({
    changeSets,
    selectedChangeSetUid,
    onSelectChangeSet,
}: ChangeSetHistoryProps) => {
    return (
        <>
            <SectionHeading margin="space0">History</SectionHeading>

            <DetailText>
                Click a version for more details and to display it in the
                platform.
            </DetailText>

            <Box
                display="flex"
                flexDirection="column"
                rowGap="space40"
                marginTop="space40"
            >
                {changeSets.map((changeSet) => (
                    <ChangeSetHistoryRow
                        key={changeSet.uid}
                        changeSet={changeSet}
                        selectedChangeSetUid={selectedChangeSetUid}
                        onSelectChangeSet={onSelectChangeSet}
                    />
                ))}
            </Box>
        </>
    );
};

export default ChangeSetHistory;
