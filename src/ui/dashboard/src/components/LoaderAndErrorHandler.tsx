import { ApolloError } from "@apollo/client";
import { Box, BoxProps } from "@twilio-paste/core";
import { PropsWithChildren, ReactNode } from "react";
import { AppElementId, ErrorType, PageId } from "../types/uiIdentifiers";
import GenericError from "./errors/GenericError";
import Loader from "./loaders/Loader";
import PageLoader from "./loaders/PageLoader";

interface LoaderAndErrorHandlerProps extends PropsWithChildren {
    errorCategory: AppElementId | PageId;
    isLoading: boolean;
    hasData: unknown;
    error?: ApolloError;
    isFullPage?: boolean;
    hasPermission?: boolean;
    noDataComponent?: ReactNode;
    loadedWrapperBoxProps?: BoxProps;
}

const LoaderAndErrorHandler = ({
    errorCategory,
    isLoading,
    error,
    children,
    hasData,
    isFullPage,
    hasPermission = true,
    noDataComponent,
    loadedWrapperBoxProps,
}: LoaderAndErrorHandlerProps) => {
    const isVisible = !isLoading && !error;

    if (isLoading) {
        return isFullPage ? <PageLoader /> : <Loader />;
    }

    if (error) {
        return (
            <GenericError
                category={errorCategory}
                type={ErrorType.GraphQLError}
                message={error.message}
            />
        );
    }

    if (!hasData) {
        if (noDataComponent) {
            return noDataComponent;
        }
        return (
            <GenericError category={errorCategory} type={ErrorType.NoData} />
        );
    }

    if (!hasPermission) {
        return (
            <GenericError
                category={errorCategory}
                type={ErrorType.InsufficientPermission}
            />
        );
    }

    return (
        <Box
            transition="opacity 0.2s ease-in-out"
            opacity={isVisible ? 1 : 0}
            {...loadedWrapperBoxProps}
        >
            {children}
        </Box>
    );
};

export default LoaderAndErrorHandler;
