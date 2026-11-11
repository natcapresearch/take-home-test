import { ApolloError } from "@apollo/client";
import { Box, BoxProps } from "@twilio-paste/core";
import { PropsWithChildren, ReactNode, useEffect, useRef } from "react";
import { ErrorType, TableId } from "../../types/uiIdentifiers";
import GenericError from "../errors/GenericError";
import Loader from "../loaders/Loader";
import LoadingOverlay from "../loaders/LoadingOverlay";
import { EmptyTableState } from "./EmptyTableState";

interface TableLoaderAndErrorHandlerProps extends PropsWithChildren {
    isLoading: boolean;
    hasData?: boolean;
    noDataComponent?: ReactNode;
    error?: ApolloError;
    tableName: TableId;
    showEmptyState?: boolean;
    wrapperBoxProps?: BoxProps;
    // Set when the table sits in its own fixed-height scroll container; see
    // LoadingOverlay.
    inScrollContainer?: boolean;
}

const TableLoaderAndErrorHandler = ({
    isLoading,
    error,
    children,
    hasData,
    noDataComponent,
    tableName,
    showEmptyState = true,
    wrapperBoxProps,
    inScrollContainer,
}: TableLoaderAndErrorHandlerProps) => {
    const isFirstLoad = useRef(true);

    useEffect(() => {
        if (!isLoading && !error) {
            isFirstLoad.current = false;
        }
    }, [isLoading, error]);

    // First load
    if (isLoading && isFirstLoad.current) {
        return <Loader />;
    }

    // Error
    if (error) {
        return (
            <GenericError
                category={tableName}
                type={ErrorType.GraphQLError}
                message={error.message}
            />
        );
    }

    // Empty state
    if (!isLoading && showEmptyState && !hasData) {
        if (noDataComponent) {
            return noDataComponent;
        }
        return <EmptyTableState />;
    }

    // Data with overlay loader (only after the first load)
    return (
        <Box {...wrapperBoxProps} position="relative">
            {children}

            {isLoading && (
                <LoadingOverlay inScrollContainer={inScrollContainer} />
            )}
        </Box>
    );
};

export default TableLoaderAndErrorHandler;
