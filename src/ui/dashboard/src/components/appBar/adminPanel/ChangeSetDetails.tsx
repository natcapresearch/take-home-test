import {
    Alert,
    Anchor,
    Badge,
    Box,
    Button,
    Card,
    DetailText,
    Disclosure,
    DisclosureContent,
    DisclosureHeading,
    Input,
    Label,
    Separator,
    Text,
    TextArea,
} from "@twilio-paste/core";
import { ArchiveIcon } from "@twilio-paste/icons/esm/ArchiveIcon";
import { EditIcon } from "@twilio-paste/icons/esm/EditIcon";
import { UnarchiveIcon } from "@twilio-paste/icons/esm/UnarchiveIcon";
import { format } from "date-fns";
import { ReactNode, useEffect, useState } from "react";
import {
    AdminPanelChangeSetsDocument,
    ChangeSet,
    ChangeSetState,
    ChangeSetSummary as ChangeSetSummaryType,
    Maybe,
    UnitOfAnalysisChangeSummary,
    UpdateChangeSetDocument,
} from "../../../../../common/__generated__/client-types";
import useAuthenticatedMutation from "../../../helpers/hooks/useAuthenticatedMutation";
import { hasPermission } from "../../../helpers/permissionHelpers";
import {
    dateTimeFormat,
    formatChangeSetNameForViewer,
} from "../../../helpers/stringHelpers";
import SectionHeading from "../../layout/typography/SectionHeading";
import { changeSetStatusToBadge } from "./badgeHelpers";
import PublishChangeSetConfirmModal from "./PublishChangeSetConfirmModal";
import UnpublishChangeSetConfirmModal from "./UnpublishChangeSetConfirmModal";

interface ChangeSetDatesProps {
    changeSet: ChangeSet;
}

const formatOptionalDate = (value: string | null | undefined): string => {
    return value ? format(new Date(value), dateTimeFormat) : "-";
};

const ChangeSetDates = ({ changeSet }: ChangeSetDatesProps) => {
    return (
        <>
            <Box display="flex" columnGap="space40" marginBottom="space40">
                <Box
                    flexGrow={1}
                    flexBasis="0"
                    minWidth="size0"
                    data-testid="change-set-date-created"
                >
                    <Label>Created</Label>
                    {formatOptionalDate(changeSet.createdAt)}
                </Box>

                <Box
                    flexGrow={1}
                    flexBasis="0"
                    minWidth="size0"
                    data-testid="change-set-date-published"
                >
                    <Label>Published</Label>
                    {formatOptionalDate(changeSet.publishedAt)}
                </Box>
            </Box>

            <Box display="flex" columnGap="space40">
                <Box
                    flexGrow={1}
                    flexBasis="0"
                    minWidth="size0"
                    data-testid="change-set-date-processed"
                >
                    <Label>Processed</Label>
                    {formatOptionalDate(changeSet.processedAt)}
                </Box>

                <Box
                    flexGrow={1}
                    flexBasis="0"
                    minWidth="size0"
                    data-testid="change-set-date-unpublished"
                >
                    {changeSet.unpublishedAt && (
                        <>
                            <Label>Unpublished</Label>
                            {formatOptionalDate(changeSet.unpublishedAt)}
                        </>
                    )}
                </Box>
            </Box>
        </>
    );
};

const isSummaryLabel = (
    summary: UnitOfAnalysisChangeSummary,
    label: string,
) => {
    const normalised = summary.text.trim().toLowerCase();
    return normalised === label || normalised === `${label}s`;
};

const getRegionSummaries = (
    summaries: ChangeSetSummaryType["commoditySourceUnitOfAnalysisSummaries"],
): UnitOfAnalysisChangeSummary[] => {
    return summaries.regions.filter(
        (summary) =>
            !isSummaryLabel(summary, "activity") &&
            !isSummaryLabel(summary, "commodity"),
    );
};

interface SummaryStat {
    label: string;
    value: number;
}

interface SummaryStatCardProps {
    label: string;
    count: number;
    unit: string;
    stats: SummaryStat[];
}

const SummaryStatCard = ({
    label,
    count,
    unit,
    stats,
}: SummaryStatCardProps) => {
    return (
        <Card element="FULL_WIDTH_CARD">
            <Text as="p" fontSize="fontSize30" color="colorTextWeak">
                {label}
            </Text>
            <Box
                display="flex"
                alignItems="baseline"
                columnGap="space20"
                marginTop="space20"
            >
                <Text
                    as="span"
                    fontSize="fontSize70"
                    fontWeight="fontWeightBold"
                >
                    {count}
                </Text>
                <Text as="span" fontSize="fontSize30" color="colorTextWeak">
                    {unit}
                </Text>
            </Box>
            <Box
                display="flex"
                flexWrap="wrap"
                rowGap="space20"
                marginTop="space30"
                justifyContent="space-between"
            >
                {stats.map((stat) => (
                    <Text
                        key={stat.label}
                        as="span"
                        fontSize="fontSize20"
                        color="colorTextWeak"
                    >
                        {stat.value} {stat.label}
                    </Text>
                ))}
            </Box>
        </Card>
    );
};

interface ChangeLogProps {
    changeSetState: ChangeSetState;
    changeSetSummary: ChangeSetSummaryType;
    commoditiesCount?: Maybe<number>;
    totalCommoditySources?: Maybe<number>;
    missingQuantityCount?: Maybe<number>;
    missingSpendCount?: Maybe<number>;
}

const ChangeLog = ({
    changeSetState,
    changeSetSummary,
    commoditiesCount,
    totalCommoditySources,
    missingQuantityCount,
    missingSpendCount,
}: ChangeLogProps) => {
    // Draft versions haven't had results calculated yet, so their data has
    // only been "uploaded" rather than "processed".
    const stateLabel =
        changeSetState === ChangeSetState.Draft ? "uploaded" : "processed";

    const suppliers =
        changeSetSummary.commoditySourceUnitOfAnalysisSummaries.suppliers;
    const products =
        changeSetSummary.commoditySourceUnitOfAnalysisSummaries.products;
    const commodityRegions = getRegionSummaries(
        changeSetSummary.commoditySourceUnitOfAnalysisSummaries,
    );

    return (
        <Disclosure visible>
            <DisclosureHeading as="h4" variant="heading40">
                Version summary
            </DisclosureHeading>
            <DisclosureContent>
                <Box marginTop="space40">
                    <SummaryStatCard
                        label={`Commodities ${stateLabel}`}
                        count={commoditiesCount ?? 0}
                        unit="commodities"
                        stats={[
                            {
                                label: "regions",
                                value: commodityRegions.length,
                            },
                            {
                                label: "suppliers",
                                value: suppliers.length,
                            },
                            {
                                label: "products",
                                value: products.length,
                            },
                        ]}
                    />
                    <MissingInformation
                        totalCommoditySources={totalCommoditySources}
                        missingQuantityCount={missingQuantityCount}
                        missingSpendCount={missingSpendCount}
                    />
                </Box>
            </DisclosureContent>
        </Disclosure>
    );
};

interface ChangeSetActionsProps {
    canPublishChangeSet: boolean;
    changeSet: ChangeSet;
    onEditChangeSet: () => void;
}

const ChangeSetActions = ({
    canPublishChangeSet,
    changeSet,
    onEditChangeSet,
}: ChangeSetActionsProps) => {
    const [isConfirmPublishOpen, setIsConfirmPublishOpen] = useState(false);
    const [isConfirmUnpublishOpen, setIsConfirmUnpublishOpen] = useState(false);

    const closeConfirm = () => {
        setIsConfirmPublishOpen(false);
    };

    const closeUnpublishConfirm = () => {
        setIsConfirmUnpublishOpen(false);
    };

    const editButton = (
        <Button variant="secondary" size="small" onClick={onEditChangeSet}>
            <EditIcon decorative />
            Edit
        </Button>
    );

    switch (changeSet.state) {
        case ChangeSetState.Published:
            return (
                <Box display="flex" columnGap="space40">
                    {editButton}

                    {canPublishChangeSet && (
                        <>
                            <Button
                                variant="secondary"
                                size="small"
                                onClick={() => setIsConfirmUnpublishOpen(true)}
                            >
                                <ArchiveIcon decorative />
                                Unpublish
                            </Button>
                            <UnpublishChangeSetConfirmModal
                                changeSet={changeSet}
                                isOpen={isConfirmUnpublishOpen}
                                onDismiss={closeUnpublishConfirm}
                            />
                        </>
                    )}
                </Box>
            );

        case ChangeSetState.Done:
            return (
                <Box display="flex" columnGap="space40">
                    {editButton}

                    {canPublishChangeSet && (
                        <>
                            <Button
                                variant="primary"
                                element="PRIMARY_BUTTON"
                                size="small"
                                onClick={() => setIsConfirmPublishOpen(true)}
                            >
                                <UnarchiveIcon decorative />
                                Publish
                            </Button>
                            <PublishChangeSetConfirmModal
                                changeSet={changeSet}
                                isOpen={isConfirmPublishOpen}
                                onDismiss={closeConfirm}
                            />
                        </>
                    )}
                </Box>
            );

        case ChangeSetState.Draft:
            return (
                <Box display="flex" columnGap="space40">
                    {editButton}
                </Box>
            );

        default:
            return null;
    }
};

interface ChangeSetSummaryProps {
    accessibleChangeSetUids: Set<string>;
    actions: ReactNode;
    changeSet: ChangeSet;
    isEditingChangeSet: boolean;
    onEditChangeSet: () => void;
    onSelectChangeSet: (changeSetUId: string) => Promise<void>;
}

const ChangeSetSummary = ({
    accessibleChangeSetUids,
    actions,
    changeSet,
    isEditingChangeSet,
    onEditChangeSet,
    onSelectChangeSet,
}: ChangeSetSummaryProps) => {
    const [updateChangeSet, { loading: isSavingChangeSet }] =
        useAuthenticatedMutation(UpdateChangeSetDocument, {
            errorMessage: "Failed to update version details",
            refetchQueries: [
                {
                    query: AdminPanelChangeSetsDocument,
                    variables: { orgUid: changeSet.orgUid },
                },
            ],
        });
    const [changeSetName, setChangeSetName] = useState(changeSet.name);
    const [draftChangeSetName, setDraftChangeSetName] = useState(
        changeSet.name,
    );
    const [changeSetDescription, setChangeSetDescription] = useState(
        changeSet.description ?? "",
    );
    const [draftChangeSetDescription, setDraftChangeSetDescription] = useState(
        changeSet.description ?? "",
    );

    useEffect(() => {
        setChangeSetName(changeSet.name);
        setDraftChangeSetName(changeSet.name);
        setChangeSetDescription(changeSet.description ?? "");
        setDraftChangeSetDescription(changeSet.description ?? "");
    }, [changeSet.description, changeSet.id, changeSet.name]);

    const handleSaveChangeSet = async () => {
        const trimmedName = draftChangeSetName.trim();
        const trimmedDescription = draftChangeSetDescription.trim();

        if (!trimmedName) {
            return;
        }

        if (
            trimmedName === changeSetName &&
            trimmedDescription === changeSetDescription
        ) {
            onEditChangeSet();
            return;
        }

        const outcome = await updateChangeSet({
            variables: {
                orgUid: changeSet.orgUid,
                changeSetUid: changeSet.uid,
                name: trimmedName,
                description: trimmedDescription,
            },
        });

        if (!outcome.success) {
            return;
        }

        setChangeSetName(trimmedName);
        setDraftChangeSetName(trimmedName);
        setChangeSetDescription(trimmedDescription);
        setDraftChangeSetDescription(trimmedDescription);
        onEditChangeSet();
    };

    const handleCancelChangeSetEdit = () => {
        setDraftChangeSetName(changeSetName);
        setDraftChangeSetDescription(changeSetDescription);
        onEditChangeSet();
    };

    return (
        <Box width="100%">
            {isEditingChangeSet ? (
                <Box
                    display="flex"
                    flexDirection="column"
                    rowGap="space40"
                    alignItems="flex-start"
                    width="100%"
                >
                    <Box width="100%">
                        <Input
                            id="change-set-name-input"
                            type="text"
                            maxLength={80}
                            aria-label="Version name"
                            value={draftChangeSetName}
                            onChange={(event) => {
                                setDraftChangeSetName(event.target.value);
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                    void handleSaveChangeSet();
                                }

                                if (event.key === "Escape") {
                                    handleCancelChangeSetEdit();
                                }
                            }}
                        />
                    </Box>

                    <Box width="100%">
                        <TextArea
                            id="change-set-description-input"
                            maxLength={250}
                            aria-label="Version description"
                            value={draftChangeSetDescription}
                            onChange={(event) => {
                                setDraftChangeSetDescription(
                                    event.target.value,
                                );
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                    void handleSaveChangeSet();
                                }

                                if (event.key === "Escape") {
                                    handleCancelChangeSetEdit();
                                }
                            }}
                        />
                    </Box>

                    <Box display="flex" columnGap="space40" width="100%">
                        <Box
                            width="100%"
                            display="flex"
                            justifyContent="flex-start"
                        >
                            <Button
                                variant="secondary"
                                size="small"
                                onClick={handleCancelChangeSetEdit}
                            >
                                Cancel
                            </Button>
                        </Box>

                        <Box
                            width="100%"
                            display="flex"
                            justifyContent="flex-end"
                        >
                            <Button
                                variant="primary"
                                size="small"
                                onClick={() => {
                                    void handleSaveChangeSet();
                                }}
                                loading={isSavingChangeSet}
                            >
                                Save
                            </Button>
                        </Box>
                    </Box>

                    <Box width="100%">
                        <Separator
                            orientation="horizontal"
                            verticalSpacing="space0"
                        />
                    </Box>
                </Box>
            ) : (
                <Box>
                    <Box
                        display="flex"
                        alignItems="center"
                        columnGap="space40"
                        justifyContent="space-between"
                        width="100%"
                        flexWrap="wrap"
                        rowGap="space30"
                    >
                        <SectionHeading margin="space0">
                            {formatChangeSetNameForViewer(changeSetName) ??
                                changeSetName}
                        </SectionHeading>

                        <Box>{actions}</Box>
                    </Box>

                    <DetailText>
                        {changeSetDescription ||
                            "No description. Click edit to add description"}
                    </DetailText>
                </Box>
            )}

            <Box
                display="flex"
                alignItems="center"
                columnGap="space40"
                marginTop="space40"
            >
                <Badge
                    as="span"
                    variant={changeSetStatusToBadge[changeSet.state].variant}
                >
                    {changeSetStatusToBadge[changeSet.state].text}
                </Badge>

                {changeSet.parentChangeSet &&
                    (accessibleChangeSetUids.has(
                        changeSet.parentChangeSet.uid,
                    ) ? (
                        <Anchor
                            href="#"
                            onClick={(event) => {
                                event.preventDefault();
                                void onSelectChangeSet(
                                    changeSet.parentChangeSet!.uid,
                                );
                            }}
                        >
                            Previous version:{" "}
                            {changeSet.parentChangeSet.name
                                ? formatChangeSetNameForViewer(
                                      changeSet.parentChangeSet.name,
                                  )
                                : changeSet.parentChangeSet.uid}
                        </Anchor>
                    ) : (
                        <Text as="span" fontSize="fontSize30">
                            Previous version:{" "}
                            {changeSet.parentChangeSet.name
                                ? formatChangeSetNameForViewer(
                                      changeSet.parentChangeSet.name,
                                  )
                                : changeSet.parentChangeSet.uid}
                        </Text>
                    ))}
            </Box>
        </Box>
    );
};

type FieldCoverage = "complete" | "partial" | "none";

const fieldCoverage = (missing: number, total: number): FieldCoverage => {
    if (total <= 0 || missing <= 0) {
        return "complete";
    }
    return missing >= total ? "none" : "partial";
};

interface MissingInformationProps {
    totalCommoditySources: number | null | undefined;
    missingQuantityCount: number | null | undefined;
    missingSpendCount: number | null | undefined;
}

const MissingInformation = ({
    totalCommoditySources,
    missingQuantityCount,
    missingSpendCount,
}: MissingInformationProps) => {
    // Quantity and spend are optional: "no data at all" (every row lacks the
    // field) is called out separately from "incomplete" (some rows have it,
    // some don't).
    const totalSources = totalCommoditySources ?? 0;

    const fields = [
        {
            label: "Commodity quantity",
            coverage: fieldCoverage(missingQuantityCount ?? 0, totalSources),
        },
        {
            label: "Commodity spend",
            coverage: fieldCoverage(missingSpendCount ?? 0, totalSources),
        },
    ];
    const noDataCategories = fields
        .filter((field) => field.coverage === "none")
        .map((field) => field.label);
    const incompleteCategories = fields
        .filter((field) => field.coverage === "partial")
        .map((field) => field.label);

    const hasNoDataInformation = noDataCategories.length > 0;
    const hasIncompleteInformation = incompleteCategories.length > 0;

    if (!hasNoDataInformation && !hasIncompleteInformation) {
        return null;
    }

    return (
        <Box marginTop="space40">
            <Alert variant="warning">
                <Box fontWeight="fontWeightBold">Missing information</Box>
                <Box fontSize="fontSize20">
                    Optional, improves calculation accuracy.
                </Box>
                <Box
                    display="flex"
                    flexDirection="column"
                    rowGap="space20"
                    marginTop="space40"
                >
                    {hasNoDataInformation && (
                        <Box display="flex" justifyContent="space-between">
                            {noDataCategories.join(", ")}
                            <Box
                                fontWeight="fontWeightBold"
                                fontSize="fontSize20"
                            >
                                No data
                            </Box>
                        </Box>
                    )}

                    {hasIncompleteInformation && (
                        <Box display="flex" justifyContent="space-between">
                            {incompleteCategories.join(", ")}
                            <Box
                                fontWeight="fontWeightBold"
                                fontSize="fontSize20"
                            >
                                Incomplete
                            </Box>
                        </Box>
                    )}
                </Box>
            </Alert>
        </Box>
    );
};

interface ChangeSetDetailsProps {
    accessibleChangeSetUids: Set<string>;
    changeSet: ChangeSet;
    changeSetSummary: ChangeSetSummaryType;
    commoditiesCount?: Maybe<number>;
    totalCommoditySources?: Maybe<number>;
    missingQuantityCount?: Maybe<number>;
    missingSpendCount?: Maybe<number>;
    onSelectChangeSet: (changeSetUid: string) => Promise<void>;
}

const ChangeSetDetails = ({
    accessibleChangeSetUids,
    changeSet,
    changeSetSummary,
    commoditiesCount,
    totalCommoditySources,
    missingQuantityCount,
    missingSpendCount,
    onSelectChangeSet,
}: ChangeSetDetailsProps) => {
    const canPublishChangeSet = hasPermission(
        changeSet.permissionSet,
        "update:change_set:publish",
    );

    const [isEditingChangeSet, setIsEditingChangeSet] = useState(false);

    const handleEnterEditMode = () => {
        setIsEditingChangeSet(true);
    };

    const handleExitEditMode = () => {
        setIsEditingChangeSet(false);
    };

    useEffect(() => {
        setIsEditingChangeSet(false);
    }, [changeSet.id]);

    return (
        <Card>
            <Box marginBottom="space40">
                <ChangeSetSummary
                    accessibleChangeSetUids={accessibleChangeSetUids}
                    actions={
                        <ChangeSetActions
                            canPublishChangeSet={canPublishChangeSet}
                            changeSet={changeSet}
                            onEditChangeSet={handleEnterEditMode}
                        />
                    }
                    changeSet={changeSet}
                    isEditingChangeSet={isEditingChangeSet}
                    onEditChangeSet={handleExitEditMode}
                    onSelectChangeSet={onSelectChangeSet}
                />
            </Box>

            <Separator orientation="horizontal" verticalSpacing="space50" />

            <ChangeSetDates changeSet={changeSet} />

            <Separator orientation="horizontal" verticalSpacing="space50" />

            <ChangeLog
                changeSetState={changeSet.state}
                changeSetSummary={changeSetSummary}
                commoditiesCount={commoditiesCount}
                totalCommoditySources={totalCommoditySources}
                missingQuantityCount={missingQuantityCount}
                missingSpendCount={missingSpendCount}
            />
        </Card>
    );
};

export default ChangeSetDetails;
