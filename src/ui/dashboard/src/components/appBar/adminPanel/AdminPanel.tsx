import {
    Alert,
    Badge,
    Box,
    Button,
    SideModalBody,
    SideModalHeader,
    SideModalHeading,
    useSideModalState,
} from "@twilio-paste/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
    AdminPanelChangeSetsDocument,
    ChangeSet,
    ChangeSetSummaryDocument,
    ChangeSetSummary as ChangeSetSummaryType,
    CommoditySourceSummary,
    Maybe,
    Organisation,
} from "../../../../../common/__generated__/client-types";
import {
    nodesFromConnection,
    valueFromResult,
} from "../../../helpers/graphqlHelpers";
import useAuthenticatedQuery from "../../../helpers/hooks/useAuthenticatedQuery";
import { formatChangeSetNameForViewer } from "../../../helpers/stringHelpers";
import { rewriteOrgScopedPath } from "../../../helpers/urlHelpers";
import DismissibleSideModal from "../../modals/DismissibleSideModal";
import { changeSetStatusToBadge } from "./badgeHelpers";
import ChangeSetDetails from "./ChangeSetDetails";
import ChangeSetHistory from "./ChangeSetHistory";

interface AdminPanelProps {
    orgUid: string;
    selectedChangeSetUid?: string;
    defaultChangeSetUid?: Maybe<string>;
}

/**
 * The version (change set) panel in the app bar: a button naming the version
 * on show, opening a side panel with its details and the version history.
 */
function AdminPanel({
    orgUid,
    selectedChangeSetUid: selectedChangeSetUidFromUrl,
    defaultChangeSetUid,
}: AdminPanelProps) {
    const navigate = useNavigate();
    const currentLocation = useLocation();

    const searchSelectedChangeSetUid =
        new URLSearchParams(currentLocation.search).get("changeSetUid") ??
        undefined;

    const dialog = useSideModalState({ visible: false, animated: 500 });

    const [localSelectedChangeSetUid, setLocalSelectedChangeSetUid] = useState<
        string | undefined
    >(undefined);

    useEffect(() => {
        if (
            selectedChangeSetUidFromUrl &&
            localSelectedChangeSetUid === selectedChangeSetUidFromUrl
        ) {
            setLocalSelectedChangeSetUid(undefined);
        }
    }, [selectedChangeSetUidFromUrl, localSelectedChangeSetUid]);

    const selectedChangeSetUid =
        localSelectedChangeSetUid ||
        searchSelectedChangeSetUid ||
        selectedChangeSetUidFromUrl ||
        defaultChangeSetUid;

    const { data: changeSetsData, error } = useAuthenticatedQuery(
        AdminPanelChangeSetsDocument,
        {
            variables: { orgUid },
            skip: !orgUid,
            fetchPolicy: "network-only",
        },
    );

    const organisation = valueFromResult(
        "Organisation",
        changeSetsData?.organisationByUuid,
    );
    const changeSetsConnection = valueFromResult(
        "ChangeSetsConnection",
        organisation?.changeSets,
    );

    const changeSets = nodesFromConnection<ChangeSet>(changeSetsConnection);
    const accessibleChangeSetUids = useMemo(
        () => new Set(changeSets.map((cs) => cs.uid)),
        [changeSets],
    );
    const shouldHideAdminPanelButton =
        Boolean(changeSetsData) && !error && changeSets.length === 0;

    const topRef = useRef<HTMLDivElement>(null);

    const selectedChangeSet = changeSets.find(
        (changeSet) => changeSet.uid === selectedChangeSetUid,
    );

    const { data: changeSetSummaryData } = useAuthenticatedQuery(
        ChangeSetSummaryDocument,
        {
            variables: {
                orgUid,
                changeSetUid: selectedChangeSetUid ?? "",
            },
            skip: !selectedChangeSetUid || !dialog.visible,
        },
    );

    const changeSetSummaryOrganisation = valueFromResult<Organisation>(
        "Organisation",
        changeSetSummaryData?.organisationByUuid,
    );
    const selectedChangeSetSummary = valueFromResult<ChangeSetSummaryType>(
        "ChangeSetSummary",
        changeSetSummaryOrganisation?.changeSetSummary,
    );
    const selectedCommoditySourceSummary =
        valueFromResult<CommoditySourceSummary>(
            "CommoditySourceSummary",
            changeSetSummaryOrganisation?.commoditySourceSummary,
        );

    const handleSelectChangeSet = async (changeSetUid: string) => {
        setLocalSelectedChangeSetUid(changeSetUid);

        navigate({
            pathname: rewriteOrgScopedPath(currentLocation.pathname, {
                changeSetUid,
            }),
            search: currentLocation.search,
            hash: currentLocation.hash,
        });
    };

    if (shouldHideAdminPanelButton) {
        return null;
    }

    const versionButtonLabel = (
        <Box display="flex" columnGap="space40" alignItems="center">
            {selectedChangeSet
                ? formatChangeSetNameForViewer(selectedChangeSet.name)
                : "No active version"}
            {selectedChangeSet && (
                <Badge
                    as="span"
                    variant={
                        changeSetStatusToBadge[selectedChangeSet.state].variant
                    }
                >
                    {changeSetStatusToBadge[selectedChangeSet.state].text}
                </Badge>
            )}
        </Box>
    );

    return (
        <>
            <Button
                onClick={dialog.show}
                variant="secondary"
                element="ADMIN_PANEL_BUTTON"
                data-testid="admin-panel-trigger"
            >
                {versionButtonLabel}
            </Button>

            <DismissibleSideModal
                state={dialog}
                aria-label="Manage versions"
                element="SMALL_GRAY_BACKGROUND_MODAL"
            >
                <SideModalHeader>
                    <SideModalHeading>Manage versions</SideModalHeading>
                </SideModalHeader>

                <SideModalBody>
                    <Box
                        ref={topRef}
                        paddingTop="space80"
                        marginTop="spaceNegative80"
                    />

                    {error && (
                        <Box marginBottom="space60">
                            <Alert variant="error">
                                Failed to load versions.
                            </Alert>
                        </Box>
                    )}

                    {selectedChangeSet && selectedChangeSetSummary && (
                        <ChangeSetDetails
                            accessibleChangeSetUids={accessibleChangeSetUids}
                            changeSet={selectedChangeSet}
                            changeSetSummary={selectedChangeSetSummary}
                            commoditiesCount={
                                selectedCommoditySourceSummary?.totalCommodities
                            }
                            totalCommoditySources={
                                selectedCommoditySourceSummary?.totalCommoditySources
                            }
                            missingQuantityCount={
                                selectedCommoditySourceSummary?.missingQuantityCount
                            }
                            missingSpendCount={
                                selectedCommoditySourceSummary?.missingSpendCount
                            }
                            onSelectChangeSet={handleSelectChangeSet}
                        />
                    )}

                    <Box marginTop="space80">
                        <ChangeSetHistory
                            changeSets={changeSets}
                            selectedChangeSetUid={selectedChangeSetUid}
                            onSelectChangeSet={handleSelectChangeSet}
                        />
                    </Box>
                </SideModalBody>
            </DismissibleSideModal>
        </>
    );
}

export default AdminPanel;
