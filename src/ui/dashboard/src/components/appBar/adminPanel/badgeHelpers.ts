import { Badge } from "@twilio-paste/core";
import type { ComponentProps } from "react";
import { ChangeSetState } from "../../../../../common/__generated__/client-types";

type BadgeVariant = NonNullable<ComponentProps<typeof Badge>["variant"]>;

type ChangeSetBadge = {
    variant: BadgeVariant;
    text: string;
};

export const changeSetStatusToBadge: Record<ChangeSetState, ChangeSetBadge> = {
    [ChangeSetState.Draft]: {
        variant: "new",
        text: "Draft",
    },
    [ChangeSetState.Processing]: {
        variant: "warning",
        text: "Processing",
    },
    [ChangeSetState.Done]: {
        variant: "default",
        text: "Unpublished",
    },
    [ChangeSetState.Published]: {
        variant: "success",
        text: "Published",
    },
};
