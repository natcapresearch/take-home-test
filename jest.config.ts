const esmModules = [
    "uuid",
    "echarts",
    "zrender",
    "htmlparser2",
    "entities",
    "domelementtype",
    "domhandler",
    "domutils",
    "dom-serializer",
];

export default {
    workerThreads: true,
    projects: [
        {
            displayName: "ui",
            testEnvironment: "jest-fixed-jsdom",
            moduleNameMapper: {
                "\\.(css|less)$": "identity-obj-proxy",
                "@twilio-paste/icons/esm/(.*)": "@twilio-paste/icons/cjs/$1",
                "\\.(svg|png)$": "<rootDir>/src/ui/fileMock.js",
            },
            setupFilesAfterEnv: ["<rootDir>/src/ui/jest.setup.ts"],
            testMatch: ["<rootDir>/src/ui/**/*.(spec|test).ts?(x)"],
            clearMocks: true,
            transform: {
                "^.+.[jt]sx?$": [
                    "ts-jest",
                    { tsconfig: "<rootDir>/src/ui/tsconfig.json" },
                ],
            },
            transformIgnorePatterns: [
                `node_modules/(?!(?:.pnpm/)?(${esmModules.join("|")}))`,
            ],
        },
        {
            displayName: "common",
            testEnvironment: "node",
            testMatch: ["<rootDir>/src/common/**/*.(spec|test).ts?(x)"],
            clearMocks: true,
            transform: {
                "^.+.[jt]sx?$": ["ts-jest", {}],
            },
        },
        {
            displayName: "graphql",
            testEnvironment: "node",
            testMatch: ["<rootDir>/src/graphql/**/*.(spec|test).ts?(x)"],
            clearMocks: true,
            transform: {
                "^.+\\.[jt]sx?$": [
                    "ts-jest",
                    { tsconfig: "<rootDir>/src/graphql/tsconfig.json" },
                ],
            },
            transformIgnorePatterns: [
                `node_modules/(?!(?:.pnpm/)?(${esmModules.join("|")}))`,
            ],
        },
    ],
    collectCoverage: true,
    coverageDirectory: "coverage",
};
