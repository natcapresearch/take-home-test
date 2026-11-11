import { CustomizationProvider } from "@twilio-paste/core/customization";
import { GenericThemeShape, Theme } from "@twilio-paste/core/theme";
import { PropsWithChildren, ReactNode } from "react";
import tc from "tinycolor2";
import "./base.css";
import { colours, purpleScale } from "./colours";

// We can scale the theme down to below its original size
// to get a tighter, more data-dense UI.
const themeScaleFactor = 1;

const scaleThemeObj = (obj: { [key: string]: string | number }) =>
    Object.keys(obj).reduce((acc, k) => {
        const initial = obj[k];
        if (initial == 0 || `${initial}`.endsWith("%")) {
            return { ...acc, [k]: obj[k] };
        }
        const val = parseFloat(initial as string);
        const result = val * themeScaleFactor;
        return {
            ...acc,
            [k]: `${parseFloat(result.toFixed(2))}rem`,
        };
    }, {});

const codeFontStack = "'Roboto Mono', monospace";
export const fontStack =
    "'Hanken Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif";

export const natcapTheme = {
    fonts: {
        fontFamilyCode: codeFontStack,
        fontFamilyDisplay: fontStack,
        fontFamilyText: fontStack,
    },
    colors: {
        colorBrand: colours.green100,
        colorBrandHighlight: colours.green60,
    },
    backgroundColors: {
        colorBackground: colours.gray05,
        colorBackgroundAvailable: colours.green60,
        colorBackgroundBody: colours.gray0,
        colorBackgroundBodyElevation: colours.gray10,
        colorBackgroundBodyElevationPrimary: colours.blue05,
        colorBackgroundBusy: tc(colours.gray0).setAlpha(0.5).toRgbString(),
        colorBackgroundElevation: colours.gray15,
        //colorBackgroundNotification: ?,
        colorBackgroundOffline: colours.gray40,
        colorBackgroundOverlay: tc(colours.gray60).setAlpha(0.5).toRgbString(),
        colorBackgroundRequired: colours.red50,
        colorBackgroundRowStriped: colours.gray05,
        colorBackgroundStrong: colours.gray10,
        colorBackgroundStronger: colours.gray50,
        colorBackgroundStrongest: colours.gray70,
        // colorBackgroundStrongElevation: ?,
        colorBackgroundSubaccount: colours.yellow10,
        colorBackgroundTrial: colours.green10,
        colorBackgroundUnavailable: colours.red60,
        colorBackgroundUser: colours.green10,
        colorBackgroundWeak: colours.gray05,
        colorBackgroundWeakElevation: colours.gray05,
        colorBackgroundWeakest: colours.gray0,
        colorBackgroundWeaker: colours.gray0,
        colorBackgroundWeakerElevation: colours.gray05,

        colorBackgroundBodyInverse: colours.gray100,
        colorBackgroundInverse: colours.green100,
        colorBackgroundInverseElevation: colours.gray90,
        colorBackgroundInverseStrong: colours.green90,
        colorBackgroundInverseStronger: colours.green80,
        colorBackgroundInverseStrongElevation: colours.gray80,
        colorBackgroundInverseStrongerElevation: colours.gray70,
        colorBackgroundInverseStrongest: colours.gray0,

        colorBackgroundBrand: colours.green100,
        colorBackgroundBrand10: colours.orange50,
        colorBackgroundBrand20: colours.blue60,
        colorBackgroundBrand30: colours.pink30,
        colorBackgroundBrandHighlight: colours.green60,
        colorBackgroundBrandHighlightWeakest: tc(colours.green60)
            .setAlpha(0.1)
            .toRgbString(),
        colorBackgroundBrandStronger: colours.green100,
        colorBackgroundBrandStrong: colours.green70,

        colorBackgroundPrimary: colours.blue60,
        colorBackgroundPrimaryStrong: colours.blue70,
        colorBackgroundPrimaryStronger: colours.blue80,
        colorBackgroundPrimaryStrongest: colours.blue100,
        colorBackgroundPrimaryWeak: colours.blue30,
        colorBackgroundPrimaryWeaker: colours.blue20,
        colorBackgroundPrimaryWeakest: colours.blue05,

        colorBackgroundDestructive: colours.red60,
        colorBackgroundDestructiveStrong: colours.red80,
        colorBackgroundDestructiveStronger: colours.red90,
        colorBackgroundDestructiveStrongest: colours.red100,
        colorBackgroundDestructiveWeak: colours.red20,
        colorBackgroundDestructiveWeaker: colours.red10,
        colorBackgroundDestructiveWeakest: colours.red05,

        colorBackgroundSuccess: colours.green60,
        colorBackgroundSuccessWeakest: colours.green05,

        colorBackgroundWarning: colours.orange50,
        colorBackgroundWarningWeakest: colours.orange05,

        colorBackgroundError: colours.red60,
        colorBackgroundErrorStrong: colours.red80,
        colorBackgroundErrorStronger: colours.red90,
        colorBackgroundErrorStrongest: colours.red100,
        colorBackgroundErrorWeakest: colours.red05,

        colorBackgroundNeutralWeakest: colours.blue05,

        colorBackgroundNew: colours.purple10,
        colorBackgroundNewWeakest: colours.purple05,

        colorBackgroundDecorative10Weakest: colours.gray10,
        colorBackgroundDecorative20Weakest: colours.blue05,
        colorBackgroundDecorative30Weakest: colours.green05,
        colorBackgroundDecorative40Weakest: colours.purple10,
    },
    borderColors: {
        colorBorder: colours.gray50,
        colorBorderWeak: colours.gray30,
        colorBorderWeaker: colours.gray20,
        colorBorderWeakest: colours.gray0,
        colorBorderStrong: colours.gray60,

        colorBorderInverse: colours.gray50,
        colorBorderInverseStrong: colours.gray20,
        colorBorderInverseStronger: colours.gray10,
        colorBorderInverseStrongest: colours.gray0,
        colorBorderInverseWeaker: colours.green80,
        colorBorderInverseWeakest: colours.gray100,

        colorBorderPrimary: colours.blue50,
        colorBorderPrimaryStrong: colours.blue80,
        colorBorderPrimaryStronger: colours.blue90,
        colorBorderPrimaryStrongest: colours.blue100,
        colorBorderPrimaryWeak: colours.blue20,
        colorBorderPrimaryWeaker: colours.blue10,
        colorBorderPrimaryWeakest: colours.blue05,

        colorBorderDestructive: colours.red60,
        colorBorderDestructiveWeak: colours.red20,
        colorBorderDestructiveWeaker: colours.red10,
        colorBorderDestructiveWeakest: colours.red05,
        colorBorderDestructiveStrong: colours.red80,
        colorBorderDestructiveStronger: colours.red90,
        colorBorderDestructiveStrongest: colours.red100,

        colorBorderSuccess: colours.green60,
        colorBorderSuccessWeak: colours.green30,
        colorBorderSuccessWeaker: colours.green20,
        colorBorderSuccessWeakest: colours.green05,

        colorBorderWarning: colours.orange50,
        colorBorderWarningWeak: colours.orange40,
        colorBorderWarningWeaker: colours.orange20,
        colorBorderWarningWeakest: colours.orange05,

        colorBorderError: colours.red60,
        colorBorderErrorWeak: colours.red40,
        colorBorderErrorWeaker: colours.red20,
        colorBorderErrorWeakest: colours.red05,
        colorBorderErrorStrong: colours.red80,
        colorBorderErrorStronger: colours.red90,
        colorBorderErrorStrongest: colours.red100,

        colorBorderNeutral: colours.blue60,
        colorBorderNeutralWeak: colours.blue40,
        colorBorderNeutralWeaker: colours.blue20,

        colorBorderNewWeak: colours.purple40,
        colorBorderNewWeaker: colours.purple20,

        colorBorderDecorative10Weaker: colours.gray20,
        colorBorderDecorative20Weaker: colours.blue20,
        colorBorderDecorative30Weaker: colours.green10,
        colorBorderDecorative40Weaker: colours.purple20,

        colorBorderUser: colours.green20,
    },
    textColors: {
        colorText: colours.gray100,
        colorTextBrand: colours.gray100,
        colorTextBrandHighlight: colours.green60,
        colorTextWeakest: colours.gray50,

        colorTextWeaker: colours.gray40,
        colorTextWeak: colours.gray70,

        colorTextInverseWeakest: colours.gray70,
        colorTextInverseWeaker: colours.gray50,
        colorTextInverseWeak: colours.gray05,

        colorTextInverse: colours.gray0,
        colorTextBrandInverse: colours.gray0,

        colorTextInverseNew: colours.purple30,

        colorTextLinkWeak: colours.blue30,
        colorTextLink: colours.blue60,
        colorTextLinkStrong: colours.blue80,
        colorTextLinkStronger: colours.blue80,
        colorTextLinkStrongest: colours.blue100,

        colorTextLinkDestructiveWeak: colours.red30,
        colorTextLinkDestructive: colours.red60,
        colorTextLinkDestructiveStrong: colours.red70,
        colorTextLinkDestructiveStronger: colours.red100,
        colorTextLinkDestructiveStrongest: colours.red110,

        colorTextPrimaryWeak: colours.blue20,
        colorTextPrimary: colours.blue70,
        colorTextPrimaryStrong: colours.blue80,
        colorTextPrimaryStronger: colours.blue100,
        colorTextPrimaryStrongest: colours.blue100,

        colorTextDestructiveWeak: colours.red30,
        colorTextDestructive: colours.red70,
        colorTextDestructiveStrong: colours.red80,
        colorTextDestructiveStronger: colours.red100,
        colorTextDestructiveStrongest: colours.red110,

        colorTextSuccess: colours.green80,

        colorTextWarning: colours.orange80,
        colorTextWarningStrong: colours.orange90,

        colorTextErrorWeak: colours.red50,
        colorTextError: colours.red70,
        colorTextErrorStrong: colours.red80,
        colorTextErrorStronger: colours.red100,
        colorTextErrorStrongest: colours.red110,

        colorTextIconNeutral: colours.blue90,

        colorTextNew: colours.purple80,

        colorTextUser: colours.green70,

        colorTextSubaccount: colours.yellow90,

        colorTextDecorative10: colours.gray70,
        colorTextDecorative20: colours.blue80,
        colorTextDecorative30: colours.green80,
        colorTextDecorative40: colours.purple80,

        colorTextIconWeaker: colours.gray20,
        colorTextIcon: colours.gray70,
        colorTextIconInverse: colours.gray05,
        colorTextIconError: colours.red70,
        colorTextIconSuccess: colours.green60,
        colorTextIconWarning: colours.orange70,
        colorTextNeutral: colours.blue80,
        colorTextIconNew: colours.purple60,
        colorTextIconAvailable: colours.green70,
        colorTextIconBusy: colours.orange60,
        colorTextIconUnavailable: colours.red70,
        colorTextIconOffline: colours.gray70,
        colorTextIconBrandInverse: colours.gray0,

        // colorTextIconNotification: ?,
        // colorTextIconBrandHighlight: ?,
    },
    shadows: {
        // shadow: ?,
        shadowBorderBrand10: `0 0 0 1px ${colours.yellow40}`,
        shadowBorderBrand20: `0 0 0 1px ${colours.blue40}`,
        shadowBorderBrand30: `0 0 0 1px ${colours.green50}`,
        shadowBorder: `0 0 0 1px ${colours.gray50}`,
        shadowBorderStrong: `0 0 0 1px ${colours.gray60}`,
        shadowBorderWeak: `0 0 0 1px ${colours.gray30}`,
        shadowBorderWeaker: `0 0 0 1px ${colours.gray20}`,
        // shadowCard: ?,
        shadowElevation05: `0 0 0 1px ${colours.gray10}`,
        // shadowElevation10: ?,
        // shadowElevation20: ?,
        shadowElevationBottom05: `0 1px 0 0 ${colours.gray10}`,
        shadowElevationBottomInverse05: `0 1px 0 0 ${colours.gray90}`,
        shadowElevationInverse05: `0 0 0 1px ${colours.gray90}`,
        // shadowElevationInverse10: ?,
        // shadowElevationLeft20: ?,
        shadowElevationRightInverse05: `1px 0 0 0 ${colours.gray90}`,
        shadowElevationTop05: `0 -1px 0 0 ${colours.gray90}`,
        // shadowElevationTop20: ?,
        // shadowBorderNotification: ?,
        // shadowFocus: `${tc(col.midBlue).setAlpha(0.5)} 0px 0px 0px 4px`,
        // shadowFocusInset: ?,
        // shadowFocusInverse: `0 0 0 2px ${col.green60}`,
        // shadowFocusInverseInset: ?,
        // shadowFocusShadowBorder: `${col.charcoal50} 0px 0px 0px 4px`,
        // shadowHigh: ?,
        // shadowLeft: ?,
        // shadowLeftInverse: ?,
        // shadowLow: ?,
        // shadowRight: ?,
        // shadowRightInverse: ?,

        shadowBorderInverse: `0 0 0 1px ${colours.gray50}`,
        shadowBorderInverseWeaker: `0 0 0 1px ${colours.gray80}`,
        shadowBorderInverseWeakest: `0 0 0 1px ${colours.gray80}`,
        shadowBorderInverseStrong: `0 0 0 1px ${colours.gray20}`,
        shadowBorderInverseStronger: `0 0 0 1px ${colours.gray10}`,
        shadowBorderInverseStrongest: `0 0 0 1px ${colours.gray0}`,

        shadowBorderInverseNewWeaker: `0 0 0 1px ${colours.purple70}`,

        shadowBorderPrimary: `0 0 0 1px ${colours.blue50}`,
        shadowBorderPrimaryStrong: `0 0 0 1px ${colours.blue60}`,
        shadowBorderPrimaryStronger: `0 0 0 1px ${colours.blue90}`,
        shadowBorderPrimaryStrongest: `0 0 0 1px ${colours.blue100}`,
        shadowBorderPrimaryWeak: `0 0 0 1px ${colours.blue30}`,
        shadowBorderPrimaryWeaker: `0 0 0 1px ${colours.blue20}`,

        shadowBorderDestructive: `0 0 0 1px ${colours.red60}`,
        shadowBorderDestructiveStrong: `0 0 0 1px ${colours.red80}`,
        shadowBorderDestructiveStronger: `0 0 0 1px ${colours.red90}`,
        shadowBorderDestructiveStrongest: `0 0 0 1px ${colours.red100}`,
        shadowBorderDestructiveWeak: `0 0 0 1px ${colours.red30}`,
        shadowBorderDestructiveWeaker: `0 0 0 1px ${colours.red20}`,

        shadowBorderSuccessWeaker: `0 0 0 1px ${colours.green20}`,

        shadowBorderWarningWeaker: `0 0 0 1px ${colours.orange20}`,

        shadowBorderError: `0 0 0 1px ${colours.red60}`,
        shadowBorderErrorStrong: `0 0 0 1px ${colours.red80}`,
        shadowBorderErrorStronger: `0 0 0 1px ${colours.red90}`,
        shadowBorderErrorStrongest: `0 0 0 1px ${colours.red100}`,
        shadowBorderErrorWeak: `0 0 0 1px ${colours.red50}`,
        shadowBorderErrorWeaker: `0 0 0 1px ${colours.red20}`,

        shadowBorderNeutralWeaker: `0 0 0 1px ${colours.blue10}`,

        shadowBorderNewWeaker: `0 0 0 1px ${colours.purple20}`,

        shadowBorderSubaccount: `0 0 0 1px ${colours.yellow20}`,

        shadowBorderDecorative10Weaker: `0 0 0 1px ${colours.gray20}`,
        shadowBorderDecorative20Weaker: `0 0 0 1px ${colours.blue20}`,
        shadowBorderDecorative30Weaker: `0 0 0 1px ${colours.green20}`,
        shadowBorderDecorative40Weaker: `0 0 0 1px ${colours.purple20}`,

        shadowBorderTopPrimary: `0 -1px 0 0 ${colours.blue50}`,
        shadowBorderTopPrimaryStrongest: `0 -1px 0 0px ${colours.blue90}`,
        shadowBorderTopInverseStrongest: `0 -1px 0 0px ${colours.blue20}`,

        shadowBorderRightInverseStrong: `1px 0 0 0 ${colours.gray20}`,

        shadowBorderBottomBrand10Strong: `0 1px 0 0 ${colours.yellow10}`,

        // shadowBorderBottomBrand20Strong: ?,
        // shadowBorderBottomBrand30Strong: ?,
        shadowBorderBottomDecorative10Weaker: `0 1px 0 0 ${colours.gray40}`,
        shadowBorderBottomDecorative20Weaker: `0 1px 0 0 ${colours.blue40}`,
        shadowBorderBottomDecorative30Weaker: `0 1px 0 0 ${colours.green40}`,
        shadowBorderBottomDecorative40Weaker: `0 1px 0 0 ${colours.purple40}`,
        shadowBorderBottomErrorWeaker: `0 1px 0 0 ${colours.red40}`,
        shadowBorderBottomInverseNewWeaker: `0 1px 0 0 ${colours.purple70}`,
        // shadowBorderBottomInverseWeaker: ?,
        // shadowBorderBottomInverseWeakerInset: ?,
        shadowBorderBottomSuccessWeaker: `0 1px 0 0 ${colours.green40}`,
        shadowBorderBottomWarningWeaker: `0 1px 0 0 ${colours.orange40}`,
        shadowBorderBottomNeutralWeaker: `0 1px 0 0 ${colours.blue40}`,
        shadowBorderBottomNewWeaker: `0 1px 0 0 ${colours.purple30}`,
        shadowBorderBottomSubaccount: `0 1px 0 0 ${colours.yellow40}`,
        shadowBorderBottomPrimary: `0 1px 0 0 ${colours.blue50}`,
        shadowBorderBottomNotificationStronger: `0 1px 0 0 ${colours.red90}`,
        shadowBorderBottomWeak: `0 1px 0 0 ${colours.gray30}`,
        shadowBorderBottomWeakInset: `0 1px 0 0 ${colours.gray30}`,

        shadowBorderUser: `0 0 0 1px ${colours.green20}`,
    },
    fontWeights: {
        fontWeightLight: 300,
        fontWeightNormal: 400,
        fontWeightBold: 700,
    },
};

const cardSharedStyles = {
    padding: "space40",
    borderRadius: "borderRadius20",
};

const sideModalOverlayStyles = {
    content: '""',
    position: "fixed",
    top: "0",
    left: "0",
    right: "0",
    bottom: "0",
    backgroundColor: "colorBackgroundOverlay",
    zIndex: -1,
} as const;

export const ThemeCustomizationProvider = ({
    theme,
    children,
}: {
    theme?: Partial<GenericThemeShape>;
    children: ReactNode;
}) => (
    <CustomizationProvider
        baseTheme="default"
        theme={theme}
        elements={{
            LIST_STYLE_NONE: {
                listStyle: "none",
                margin: "space0",
            },
            LIST_MARGIN_BOTTOM_NONE: {
                marginBottom: "space0",
            },
            LIST_ITEM: {
                margin: "space0",
            },
            LIST_ITEM_PADDING_LEFT: {
                padding: "space0",
                paddingLeft: "space60",
                marginTop: "space0",
                marginBottom: "space40",

                "&:last-of-type": {
                    marginBottom: "space0",
                },
            },
            LIST_ITEM_SMALL: {
                fontSize: "fontSize20",
                lineHeight: "lineHeight20",
                margin: "space0",
                color: "colorTextWeak",
            },
            BADGE_LIST_ITEM: {
                marginBlock: "space30",
            },
            DATA_GRID_ROW: {
                verticalAlign: "top",
            },
            DATA_GRID_ROW_INCOMPLETE: {
                backgroundColor: "colorBackgroundWeak",
                verticalAlign: "top",
                color: "colorTextWeak",
                ":nth-of-type(2n)": {
                    backgroundColor: "colorBackgroundWeak",
                },
            },
            DATA_GRID_CELL_WITH_DROPDOWN: {
                //@ts-expect-error (needed for paste)
                paddingTop: "0.3rem",
                paddingBottom: "space0",
            },
            DISCLOSURE_CONTENT: {
                padding: "space0",
                fontWeight: "fontWeightNormal",
            },
            SEARCH_MULTISELECT_CHEVRON_WRAPPER: {
                display: "none",
            },
            SEARCH_MULTISELECT_ELEMENT_CONTAINER: {
                display: "grid",
                gridTemplateColumns: "1fr",
                width: "100%",
            },
            INVERSE_TEXT: {
                color: "colorTextBrandInverse",
            },
            PRIMARY_BUTTON: {
                "&:not([disabled]):hover, &:not([disabled]):focus": {
                    backgroundColor: "colorBackgroundPrimaryStrong",
                    color: "colorTextBrandInverse",
                },
                boxShadow: "none",
                borderRadius: "borderRadius20",
            },
            SMALL_TEXT_BUTTON: {
                fontSize: "fontSize20",
            },
            GROUPED_FILTER_TRIGGER: {
                width: "100%",
                justifyContent: "flex-start",
                boxShadow: "shadowBorder",
                "&:not([disabled]):hover, &:not([disabled]):focus": {
                    boxShadow: "shadowBorderPrimary",
                },
                //@ts-expect-error (twilio paste type mismatch)
                padding: "0.35rem 0.75rem",
                minHeight: "2.25rem",
            },
            FILTER_BADGE: {
                backgroundColor: "colorBackgroundPrimaryWeakest",
                color: "colorTextWeak",
                borderColor: "colorBorderPrimaryWeak",
                borderRadius: "borderRadiusPill",
                borderStyle: "solid",
                borderWidth: "borderWidth10",
                display: "inline-flex",
                position: "relative",
                alignItems: "center",
                height: "1.5rem",
                lineHeight: "lineHeight20",
                paddingLeft: "space30",
                paddingRight: "space80",
                fontSize: "fontSize20",
                fontWeight: "fontWeightNormal",
            },
            ANCHOR_BUTTON: {
                color: "colorTextPrimary",
                boxShadow: "shadowBorderPrimary",
                "&:not([disabled]):hover, &:not([disabled]):focus": {
                    color: "colorTextPrimaryStrong",
                    boxShadow: "shadowBorderPrimaryStrong",
                },
            },
            FULL_WIDTH_RADIO_BUTTON: {
                "[data-paste-element='BUTTON'], [data-paste-element='LABEL'], [data-paste-element='RADIO']":
                    {
                        width: "100%",
                        justifyContent: "flex-start",
                    },
            },
            LINK_BUTTON: {
                "&:not([disabled]):hover, &:not([disabled]):focus": {
                    color: "colorTextPrimaryStrong",
                },
            },
            MODAL_OVERLAY: {
                zIndex: "zIndex80",
            },
            MODAL_HEADER_SMALL: {
                paddingBottom: "space20",
            },
            EXTRA_WIDE_MODAL: {
                maxWidth: "60rem",
            },
            SIDE_MODAL_CONTAINER: {
                zIndex: "zIndex80",
                "&::before": {
                    ...sideModalOverlayStyles,
                    zIndex: -1,
                },
            },
            SMALL_GRAY_BACKGROUND_MODAL_CONTAINER: {
                zIndex: "zIndex80",
                "&::before": {
                    ...sideModalOverlayStyles,
                    zIndex: -1,
                },
            },
            SIDE_MODAL: {
                width: "size70",
            },
            SMALL_GRAY_BACKGROUND_MODAL: {
                width: "size60",
                backgroundColor: "colorBackgroundBodyElevation",
            },
            GRAY_BACKGROUND_MODAL: {
                backgroundColor: "colorBackgroundBodyElevation",
            },
            MULTISELECT_COMBOBOX: {
                width: "size30",
            },
            COMBOBOX: {
                width: "size30",
            },
            MAIN: {
                backgroundColor: "colorBackground",
                flex: "1",
            },
            //@ts-expect-error (twilio paste type mismatch)
            CARD: {
                ...cardSharedStyles,
            },
            //@ts-expect-error (twilio paste type mismatch)
            ACTIVE_CARD: {
                ...cardSharedStyles,
                borderColor: "colorBorderPrimary",
                backgroundColor: "colorBackgroundPrimaryWeakest",
                boxShadow: "shadowBorderDecorative10Weaker",
            },
            //@ts-expect-error (twilio paste type mismatch)
            BORDERED_CARD_NO_SCORE: {
                ...cardSharedStyles,
                borderColor: "colorBorderPrimary",
                borderTopWidth: "borderWidth30",
                width: "100%",
                height: "100%",
            },
            //@ts-expect-error (twilio paste type mismatch)
            PADDED_CARD: {
                ...cardSharedStyles,
                padding: "space70",
            },
            //@ts-expect-error (twilio paste type mismatch)
            FULL_WIDTH_CARD: {
                ...cardSharedStyles,
                width: "100%",
            },
            // Used by the Data management card's Commodities/Sites summary
            // cards (DataManagementCard.tsx, chosen in a ternary).
            FULL_WIDTH_CLICKABLE_CARD: {
                ...cardSharedStyles,
                width: "100%",
                //@ts-expect-error (twilio paste type mismatch)
                cursor: "pointer",
                "&:hover": {
                    boxShadow: "shadowBorderPrimary",
                },
            },
            //@ts-expect-error (twilio paste type mismatch)
            FULL_WIDTH_PADDED_CARD: {
                ...cardSharedStyles,
                width: "100%",
                padding: "space70",
            },
            //@ts-expect-error (twilio paste type mismatch)
            FULL_WIDTH_AND_HEIGHT_PADDED_CARD: {
                ...cardSharedStyles,
                width: "100%",
                height: "100%",
                padding: "space70",
            },
            //@ts-expect-error (twilio paste type mismatch)
            TAB_CARD: {
                ...cardSharedStyles,
                borderTopLeftRadius: "borderRadius0",
            },
            ERROR_LINK: {
                fontWeight: "fontWeightBold",
                color: "colorTextError",
                "&:hover, &:focus": {
                    color: "colorTextError",
                },
            },
            TRANSPARENT_DISCLOSURE: {
                color: "inherit",
                backgroundColor: "transparent",
                '[data-paste-element="DISCLOSURE_HEADING"], [data-paste-element="DISCLOSURE_HEADING_ICON"], [data-paste-element="HEADING"], [data-paste-element="DISCLOSURE_CONTENT"], [data-paste-element="DISCLOSURE_HEADING"]:hover':
                    {
                        backgroundColor: "transparent",
                        color: "inherit",
                    },
            },
            FORM_CONTROL: {
                marginBottom: "space40",
            },
            FILE_UPLOADER_FULL_WIDTH: {
                width: "100%",
                maxWidth: "none",
            },
            FILE_UPLOADER_FULL_HEIGHT: {
                width: "100%",
                maxWidth: "none",
                height: "100%",
                label: {
                    height: "calc(100% - 60px)",
                },
            },
            DATA_GRID_METRIC_HEADER: {
                verticalAlign: "top",
                height: "4.5rem",
            },
            DATA_GRID_STICKY_COLUMN_HEADER: {
                verticalAlign: "top",
                position: "sticky",
                top: 0,
                left: 0,
                zIndex: "zIndex90",
                backgroundColor: "inherit",
                borderStyle: "solid",
                borderColor: "colorBorderWeaker",
                borderRightWidth: "borderWidth10",
                borderLeftWidth: "borderWidth10",
                borderTopWidth: "borderWidth0",
            },
            DATA_GRID_STICKY_COLUMN_CELL: {
                verticalAlign: "top",
                position: "sticky",
                top: 0,
                left: 0,
                //@ts-expect-error zIndex needed to be set to lower than paste allows
                zIndex: "1",
                backgroundColor: "colorBackgroundBody",
                borderStyle: "solid",
                borderColor: "colorBorderWeaker",
                borderRightWidth: "borderWidth10",
                borderLeftWidth: "borderWidth10",
                borderTopWidth: "borderWidth0",
            },
            DATA_GRID_HEATMAP_METRIC_CELL: {
                verticalAlign: "middle",
                textAlign: "center",
            },
            DATA_GRID_WITH_STICKY_COLUMN: {
                borderLeftWidth: "borderWidth0",
            },
            DATA_GRID_STICKY_COLUMN_HEADER_ROW: {
                background: "inherit",
            },
            DATA_GRID_SMALL: {
                th: {
                    padding: "space20",
                    "&:first-of-type": {
                        paddingLeft: "space30",
                    },
                },
                td: {
                    padding: "space20",
                    "&:first-of-type": {
                        paddingLeft: "space30",
                    },
                },
            },
            DATA_GRID_ROW_NO_BORDER: {
                td: {
                    border: "none",
                    verticalAlign: "top",
                    paddingBottom: "space0",
                },
            },
            DATA_GRID_ROW_BACKGROUND: {
                backgroundColor: "colorBackgroundElevation",
                ":nth-of-type(2n)": {
                    backgroundColor: "colorBackgroundElevation",
                },
            },
            DATA_GRID_ROW_HIDDEN: {
                backgroundColor: "colorBackgroundStrong",
                ":nth-of-type(2n)": {
                    backgroundColor: "colorBackgroundStrong",
                },
            },
            DATA_GRID_CELL_HIDDEN: {
                opacity: "0.5",
                backgroundColor: "colorBackgroundStrong",
            },
            DATA_GRID_CELL_HIDDEN_MANAGE: {
                backgroundColor: "colorBackgroundStrong",
            },
            DROPDOWN_SEARCH: {
                width: "size30",
            },
            DROPDOWN_SEARCH_SUFFIX: {
                backgroundColor: "none",
                borderLeft: "none",
            },
            TIMELINE_ITEM_MAX_WIDTH_CONTENT: {
                maxWidth: "size30",
            },
            TIMELINE_ITEM_MAX_WIDTH_LAST_CONTENT: {
                maxWidth: "size30",
            },
            TIMELINE_ITEM_MAX_WIDTH_LAST_SEPARATOR: {
                "::after": {
                    // Paste hides this by default, but we need this if we are going outside of the Paste standard.
                    // Necessary if we are doing more complex things in the timeline outside of what Paste handles.
                    // Changes to the structure require this override to ensure the separator remains hidden
                    display: "none !important",
                },
            },
            TIMELINE_ITEM_LAST_SEPARATOR: {
                "::after": {
                    // Paste hides this by default, but we need this if we are going outside of the Paste standard.
                    // Necessary if we are doing more complex things in the timeline outside of what Paste handles.
                    // Changes to the structure require this override to ensure the separator remains hidden
                    display: "none !important",
                },
            },
            FULL_WIDTH_DROPDOWN: {
                width: "100%",
            },
            FULL_WIDTH_DROPDOWN_SUFFIX: {
                backgroundColor: "transparent",
                borderLeft: "none",
            },
            BUTTON: {
                borderRadius: "borderRadius20",
            },
            SMALL_BADGE: {
                height: "24px",
            },
            TEXT_WEAK: {
                color: "colorTextWeak",
                fontWeight: "fontWeightNormal",
            },
            TEXT_WEAK_NO_MARGIN: {
                color: "colorTextWeak",
                fontWeight: "fontWeightNormal",
                margin: "space0",
            },
            REQUIRED: {
                color: "colorTextError",
            },
            ICON_SUCCESS: {
                color: "colorTextSuccess",
            },
            ICON_INFO: {
                color: "colorTextPrimary",
            },
            LOADER_OVERLAY: {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                zIndex: "zIndex90",
                backgroundColor: "colorBackgroundBusy",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "background-color 0.2s ease-in-out",
            },
            COOKIE_BANNER: {
                display: "flex",
                position: "fixed",
                bottom: "0",
                left: "0",
                width: "100%",
                zIndex: "zIndex90",
                padding: "space70",
                fontSize: "fontSize40",
                backgroundColor: "colorBackgroundDecorative20Weakest",
                borderTopWidth: "borderWidth10",
                borderTopStyle: "solid",
                borderTopColor: "colorBorderWeaker",
            },
            DECLARATION: {
                borderColor: "colorBorderWeak",
                borderRadius: "borderRadius20",
                borderWidth: "borderWidth10",
                borderStyle: "solid",
                padding: "space30",
                backgroundColor: "colorBackground",
            },
            ARCHIVED_ROW: {
                td: {
                    backgroundColor: "colorBackground",
                },
            },
            ORDERED_LIST: {
                marginBottom: "space0",
            },
            DISABLED_LINK: {
                color: "colorTextWeakest",
                cursor: "not-allowed",
                textDecoration: "none",
                "&:hover, &:focus": {
                    color: "colorTextWeakest",
                    textDecoration: "none",
                },
            },
            CALLOUT: {
                borderTopWidth: "borderWidth10",
                borderTopStyle: "solid",
                borderTopColor: "colorBorderWeaker",
                borderBottomWidth: "borderWidth10",
                borderBottomStyle: "solid",
                borderBottomColor: "colorBorderWeaker",
                borderRightWidth: "borderWidth10",
                borderRightStyle: "solid",
                borderRightColor: "colorBorderWeaker",
            },
            SIDEBAR_HEADER_ICON_BUTTON: {
                boxShadow: "none",
            },
            SIDEBAR_HEADER: {
                paddingX: "space60",
                boxShadow: "none",
                borderBottomWidth: "borderWidth10",
                borderBottomStyle: "solid",
                borderBottomColor: "colorBorderInverseWeaker",
            },
            LABEL_WEAK: {
                fontWeight: "fontWeightNormal",
                color: "colorTextWeak",
            },
            AVATAR_NO_BORDER: {
                border: "none",
                boxShadow: "none",
            },
            TAG_LINE: {
                fontWeight: "fontWeightNormal",
                color: "colorTextWeak",
                fontSize: "fontSize30",
            },
            HORIZONTAL_TAB_LIST_CHILD: {
                // @ts-expect-error not using a paste variable here, but this is needed to match the design
                boxShadow: `${colours.gray20} 0px -1px 0px 0px inset`,
                marginBottom: "space50",
            },
            FINANCIAL_RISK_COMPONENT_DISCLOSURE_HEADING: {
                "&:focus, &:hover, &[aria-expanded='true']": {
                    backgroundColor: "colorBackgroundBody",
                },
                paddingX: "space0",
            },
            DETAIL_TEXT_NO_MARGIN: {
                margin: "space0",
            },
            SMALL_DETAIL_TEXT: {
                fontSize: "fontSize10",
            },
            SMALL_DETAIL_TEXT_NO_MARGIN: {
                fontSize: "fontSize10",
                margin: "space0",
            },
            ALERT: {
                ul: {
                    marginBottom: "space0",
                },
            },
            MENU_ITEM_LINK: {
                color: "colorTextPrimary",
                paddingX: "space60",
            },
            SIDEBAR: {
                zIndex: "zIndex70",
                boxShadow: "none",
            },
            SIDEBAR_FOOTER: {
                borderTopWidth: "borderWidth10",
                borderTopStyle: "solid",
                borderTopColor: "colorBorderInverseWeaker",
                padding: "space60",
            },
            USER_DIALOG: {
                zIndex: "zIndex90",
            },
            USER_DIALOG_BUTTON_ICON: {
                display: "none",
            },
            USER_DIALOG_LIST: {
                borderTopLeftRadius: "borderRadius0",
                borderTopRightRadius: "borderRadius0",
            },
            USER_DIALOG_USER_EMAIL: {
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis",
            },
            TOPBAR: {
                backgroundColor: "colorBackground",
                borderBottomWidth: "borderWidth10",
                borderBottomStyle: "solid",
                borderBottomColor: "colorBorderWeaker",
            },
            SIDEBAR_NAVIGATION_DISCLOSURE_HEADING_EXPAND_ICON: {
                order: 2,
                marginLeft: "auto",
            },
            SIDEBAR_NAVIGATION_DISCLOSURE_HEADING_SELECTED_EXPAND_ICON: {
                order: 2,
                marginLeft: "auto",
            },
            SIDEBAR_NAVIGATION_ITEM: {
                paddingLeft: "space50",
                columnGap: "space50",
            },
            SIDEBAR_NAVIGATION_DISCLOSURE_HEADING: {
                paddingLeft: "space50",
                columnGap: "space50",
                "[data-paste-element='BOX']": {
                    marginLeft: "space0",
                },
            },
            SIDEBAR_NAVIGATION_DISCLOSURE_CONTENT: {
                paddingLeft: "space40",
                "[data-paste-element='SIDEBAR_NAVIGATION_ITEM']": {
                    paddingLeft: "2.5rem",
                },
            },
            SIDEBAR_COLLAPSE_BUTTON: {
                boxShadow: "none",
                borderColor: "colorBorderInverseWeaker",
                borderWidth: "borderWidth10",
                borderStyle: "solid",
            },
            RADIO_BUTTON_GROUP_VISUALLY_HIDDEN_LABEL: {
                LEGEND: {
                    clip: "rect(0 0 0 0)",
                    clipPath: "inset(50%)",
                    height: "1px",
                    overflow: "hidden",
                    position: "absolute",
                    whiteSpace: "nowrap",
                    width: "1px",
                },

                "& > span[data-paste-element='BOX']": {
                    marginTop: "space0",
                },
            },
            MAP_LEGEND_GRADIENT: {
                height: "0.625rem",
                borderRadius: "borderRadiusPill",
                // @ts-expect-error not using a paste variable here in order to create a gradient
                background: `linear-gradient(to right, ${purpleScale.join(
                    ", ",
                )})`,
            },
            MAP_LEGEND_TITLE: {
                fontWeight: "fontWeightBold",
                fontSize: "fontSize20",
            },
            MAP_LEGEND: {
                position: "absolute",
                top: "0.75rem",
                right: "0.75rem",
                padding: "space30",
                minWidth: "size20",
                backgroundColor: "colorBackgroundBody",
                borderWidth: "borderWidth10",
                borderStyle: "solid",
                borderColor: "colorBorderWeaker",
                borderRadius: "borderRadius20",
            },
            SEPARATOR_INVERSE: {
                borderColor: "colorBorderInverseWeaker",
            },
            CARD_ICON: {
                backgroundColor: "colorBackgroundSuccessWeakest",
                padding: "space30",
                borderRadius: "borderRadius40",
                borderWidth: "borderWidth20",
                borderStyle: "solid",
                borderColor: "colorBorderSuccessWeaker",
                color: "colorTextSuccess",
            },
            TITLE_TOOLTIP: {
                backgroundColor: "colorBackgroundPrimaryStrongest",
                color: "colorTextInverse",
                paddingY: "space20",
                paddingX: "space30",
                borderRadius: "borderRadius20",
                fontSize: "fontSize10",
                marginTop: "space30",
                opacity: 0,
                visibility: "hidden",
                position: "absolute",
                transition:
                    "opacity 0.15s ease-in-out, visibility 0.15s ease-in-out",
                whiteSpace: "nowrap",
                top: "100%",
                left: "50%",
                transform: "translateX(-50%)",
                "label:hover &": {
                    opacity: 1,
                    visibility: "visible",
                },
            },
            MODAL_TOOLTIP: {
                zIndex: "zIndex90",
            },
            DATA_GRID_HEADER: {
                "[data-paste-element='CHECKBOX']": {
                    backgroundColor: "colorBackgroundRowStriped",
                },
            },
            GLOBAL_SEARCH: {
                width: "100%",
            },
            ADMIN_PANEL_BUTTON: {
                // @ts-expect-error not using a paste variable here to get correct sizing
                padding: "6px 12px",
            },
        }}
    >
        {children}
    </CustomizationProvider>
);

const Base = ({ children }: PropsWithChildren) => (
    <Theme.Provider theme="default">
        <Theme.Consumer>
            {({ theme: defaultTheme }) => {
                const sizeKeys: Array<keyof GenericThemeShape> = [
                    "fontSizes",
                    "heights",
                    "widths",
                    "maxHeights",
                    "maxWidths",
                    "minHeights",
                    "minWidths",
                    "iconSizes",
                    "lineHeights",
                    "space",
                    "sizes",
                ];
                const scaledTheme = {
                    ...defaultTheme,
                    ...natcapTheme,
                    ...sizeKeys.reduce(
                        (acc, k) => ({
                            ...acc,
                            [k]: scaleThemeObj(defaultTheme[k]),
                        }),
                        {},
                    ),
                };
                return (
                    <ThemeCustomizationProvider theme={scaledTheme}>
                        {children}
                    </ThemeCustomizationProvider>
                );
            }}
        </Theme.Consumer>
    </Theme.Provider>
);

export default Base;
