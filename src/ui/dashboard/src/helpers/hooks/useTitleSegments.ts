import { Params, useMatches, useParams } from "react-router-dom";
import { OrganisationConfig } from "../../../../common/__generated__/client-types";
import { useOptionalOrganisation } from "../../contexts/OrganisationProvider";

interface MatchHandle {
    title?:
        | string
        | ((
              params: Params,
              config?: OrganisationConfig | null,
          ) => string | undefined);
}

export function useTitleSegments(): string[] {
    const matches = useMatches();
    const params = useParams();
    const config = useOptionalOrganisation()?.config;

    return [...matches]
        .reverse()
        .map((match) => {
            const handle = match.handle as MatchHandle;

            if (handle?.title == null) return;

            return typeof handle.title === "function"
                ? handle.title(params, config)
                : handle.title;
        })
        .filter((title): title is string => title != null);
}
