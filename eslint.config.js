import eslint from "@eslint/js";
import graphqlPlugin from "@graphql-eslint/eslint-plugin";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRecommended from "eslint-plugin-react/configs/jsx-runtime.js";
import tseslint from "typescript-eslint";

export default tseslint.config(
    {
        ignores: [
            "src/graphql/__generated__/**",
            "src/ui/common/__generated__/**",
            "src/common/__generated__/**",
            "src/graphql/resources/schema.graphql",
        ],
    },
    eslint.configs.recommended,
    ...tseslint.configs.recommended,

    {
        files: ["src/**/*.graphql"],
        languageOptions: {
            parser: graphqlPlugin.parser,
            parserOptions: {
                graphQLConfig: {
                    schema: "./src/graphql/resources/schema.graphql",
                    documents: ["./src/**/*.graphql"],
                },
            },
        },
        plugins: {
            "@graphql-eslint": graphqlPlugin,
        },
        rules: {
            ...graphqlPlugin.configs["flat/operations-recommended"].rules,
            "@graphql-eslint/naming-convention": "off",
            "@graphql-eslint/selection-set-depth": "off",
            "@graphql-eslint/no-deprecated": "warn",
        },
    },

    // To enable type checking, uncomment the following block
    // {
    //     languageOptions: {
    //         parserOptions: {
    //             project: true,
    //             tsconfigRootDir: import.meta.dirname,
    //         },
    //     },
    // },
    // The UI is not ready for type checking yet

    {
        files: ["src/ui/**/*.ts", "src/ui/**/*.tsx"],
        ...tseslint.configs.disableTypeChecked,
        ...reactRecommended,
        plugins: {
            "react-hooks": reactHooks,
            react: react,
        },
        rules: {
            curly: ["error", "multi-line"],
            "react/jsx-key": "error",
            "react-hooks/rules-of-hooks": "error",
            "react-hooks/exhaustive-deps": "error",
        },
    },
);
