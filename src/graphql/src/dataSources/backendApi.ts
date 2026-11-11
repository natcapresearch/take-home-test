import {
    CacheOptions,
    RequestDeduplicationPolicy,
    RequestOptions,
    RESTDataSource,
} from "@apollo/datasource-rest";
import { FetcherHeaders } from "@apollo/utils.fetcher";
import { KeyValueCache } from "@apollo/utils.keyvaluecache";
import {
    AggregatedCommoditySourceRegion,
    ChangeSetCommoditySourceRead,
    ChangeSetRead,
    ChangeSetSummary,
    ChangeSetUpdate,
    CommoditySourceSummary,
    OrganisationRead,
    PermissionSetRead,
    UserResponse,
} from "../../__generated__/backend";
import { CommoditySourceFilter } from "../../__generated__/resolvers-types";
import { paramsToBackendParams } from "../helpers/backendApiHelpers";
import {
    BackendPagination,
    PaginationArgs,
    SortArgs,
} from "../helpers/paginationHelpers";
import { settings } from "../settings";

/** The header naming the organisation an org-scoped request is for. */
const ORG_UID_HEADER = "x-org-uid";

/**
 * The REST backend behind the GraphQL API. No credentials are sent: the
 * backend injects its demo user itself.
 */
export class BackendApi extends RESTDataSource {
    baseURL = settings.BACKEND_API_URL;

    constructor(options: { cache?: KeyValueCache<string> }) {
        super(options); // this sends our server's `cache` through
    }

    override cacheKeyFor(
        url: URL,
        request: RequestOptions<CacheOptions>,
    ): string {
        if (request.cacheKey) {
            return request.cacheKey;
        }
        const orgUid = request.headers?.[ORG_UID_HEADER] ?? "";
        return `${request.method ?? "GET"} ${url} org=${orgUid}`;
    }

    protected requestDeduplicationPolicyFor(
        url: URL,
        request: RequestOptions,
    ): RequestDeduplicationPolicy {
        const method = request.method ?? "GET";
        const cacheKey = this.cacheKeyFor(url, request);

        if (["GET", "HEAD"].includes(method)) {
            return {
                policy: "deduplicate-until-invalidated",
                deduplicationKey: `${method} ${cacheKey}`,
            };
        }

        return {
            policy: "do-not-deduplicate",
            // Always invalidate GETs and HEADs when a different method is seen
            // on the same cache key (i.e. URL), as per standard HTTP semantics.
            invalidateDeduplicationKeys: [
                this.cacheKeyFor(url, { ...request, method: "GET" }),
                this.cacheKeyFor(url, { ...request, method: "HEAD" }),
            ],
        };
    }

    parseHeaders(headers: FetcherHeaders): BackendPagination {
        const totalCount = headers.get("natcap-total-count") || 0;
        const result: BackendPagination = {
            totalCount: +totalCount,
        };

        const nextCursor = headers.get("natcap-next-cursor");
        if (nextCursor) result.nextCursor = nextCursor;

        const prevCursor = headers.get("natcap-prev-cursor");
        if (prevCursor) result.prevCursor = prevCursor;

        return result;
    }

    async getCurrentUser() {
        return this.get<UserResponse>("/api/v1/users/current/");
    }

    async getRootPermissionSet(): Promise<PermissionSetRead> {
        return this.get<PermissionSetRead>(
            "/api/v1/object-permission-set/root/",
        );
    }

    async getObjectPermissionSet(
        obj: string,
        uid: string,
        orgUid?: string,
    ): Promise<PermissionSetRead> {
        const headers = orgUid ? { [ORG_UID_HEADER]: orgUid } : undefined;

        return this.get<PermissionSetRead>(
            `/api/v1/object-permission-set/${obj}/${uid}/`,
            { headers },
        );
    }

    async getOrganisation(orgUid: string) {
        return this.get<OrganisationRead>(`/api/v1/organisations/${orgUid}/`);
    }

    async getChangeSets(
        orgUid: string,
        pagination?: PaginationArgs,
        sortArgs?: SortArgs,
        state?: string,
    ): Promise<{
        response: ChangeSetRead[];
        headers: BackendPagination;
    }> {
        const params = paramsToBackendParams(sortArgs, undefined, {
            before: pagination?.before || undefined,
            after: pagination?.after || undefined,
            limit: pagination?.first?.toString(),
            state: state || undefined,
        });

        const res = await this.fetch<ChangeSetRead[]>("/api/v1/change-sets/", {
            headers: { [ORG_UID_HEADER]: orgUid },
            params,
        });

        return {
            response: res.parsedBody,
            headers: this.parseHeaders(res.response.headers),
        };
    }

    async getChangeSet(orgUid: string, changeSetUid?: string) {
        const params = changeSetUid
            ? { change_set_uid: changeSetUid }
            : undefined;
        return this.get<ChangeSetRead>("/api/v1/change-set/", {
            headers: { [ORG_UID_HEADER]: orgUid },
            params,
        });
    }

    async patchChangeSet(
        orgUid: string,
        changeSetUid: string,
        input: ChangeSetUpdate,
    ) {
        return this.patch<ChangeSetRead>(
            `/api/v1/change-sets/${changeSetUid}/`,
            {
                headers: { [ORG_UID_HEADER]: orgUid },
                body: input,
            },
        );
    }

    async getChangeSetSummary(
        orgUid: string,
        changeSetUid: string,
    ): Promise<ChangeSetSummary> {
        return this.get<ChangeSetSummary>(
            `/api/v1/change-sets/${changeSetUid}/summary/`,
            {
                headers: { [ORG_UID_HEADER]: orgUid },
            },
        );
    }

    async getChangeSetCommoditySummary(
        orgUid: string,
        changeSetUid: string,
        scope?: string,
    ) {
        return this.get<CommoditySourceSummary>("/api/v2/commodity-summary/", {
            headers: { [ORG_UID_HEADER]: orgUid },
            params: {
                change_set_uid: changeSetUid,
                // "all" widens the entity set to the whole org so the
                // filter-value lists cover entities outside the changeset;
                // omitted keeps the backend default, "alive".
                ...(scope ? { scope } : {}),
            },
        });
    }

    async getChangeSetCommoditySources(
        orgUid: string,
        changeSetUid: string,
        pagination?: PaginationArgs,
        sortArgs?: SortArgs,
        filter?: CommoditySourceFilter | null,
        scope?: string,
    ) {
        const params = paramsToBackendParams(sortArgs, filter, {
            change_set_uid: changeSetUid,
            before: pagination?.before || undefined,
            after: pagination?.after || undefined,
            limit: pagination?.first?.toString(),
            scope: scope ?? undefined,
        });

        const res = await this.fetch<ChangeSetCommoditySourceRead[]>(
            "/api/v2/commodity-sources/",
            {
                headers: { [ORG_UID_HEADER]: orgUid },
                params,
            },
        );
        return {
            response: res.parsedBody,
            headers: this.parseHeaders(res.response.headers),
        };
    }

    async getAggregatedCommoditySourceRegions(
        orgUid: string,
        changeSetUid: string,
        commoditySubgroups?: string[] | null,
        includeGeometry?: boolean,
        groupByCountry?: boolean,
    ) {
        const params = paramsToBackendParams(undefined, undefined, {
            change_set_uid: changeSetUid,
            commodity_subgroups: commoditySubgroups,
            include_geometry: includeGeometry ?? undefined,
            group_by_country: groupByCountry ?? undefined,
        });
        return this.get<AggregatedCommoditySourceRegion[]>(
            "/api/v2/commodity-source-regions-aggregated/",
            {
                headers: { [ORG_UID_HEADER]: orgUid },
                params,
            },
        );
    }
}
