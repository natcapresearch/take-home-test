export enum PageId {
    Index = "index_page",
    OrganisationApp = "organisation_app",
    CommoditiesOverview = "commodities_overview_page",
}

export enum ComponentId {
    CommoditiesToProductsSankeyChart = "commodities_to_products_sankey_chart_component",
    CommodityAnalysisBarChart = "commodity_analysis_bar_chart_component",
}

export enum TableId {
    CommoditiesList = "commodities_list_table",
}

export enum ModalId {
    PublishChangeSet = "publish_change_set_modal",
    UnpublishChangeSet = "unpublish_change_set_modal",
}

export enum ErrorType {
    MissingOrganisation = "missing_organisation_error",
    NoData = "no_data_error",
    PageNotFound = "page_not_found_error",
    GraphQLError = "graphql_error_error",
    InsufficientPermission = "insufficient_permission_error",
}

export type AppElementId = ComponentId | TableId | ModalId;
