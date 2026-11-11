import {
    Avatar,
    Box,
    Menu,
    MenuButton,
    Tooltip,
    useMenuState,
} from "@twilio-paste/core";
import { UserIcon } from "@twilio-paste/icons/esm/UserIcon";
import { User } from "../../../../common/__generated__/client-types";

interface UserDialogProps {
    viewer?: Pick<User, "email" | "nickname"> | null;
}

/** The signed-in user's avatar, with their name and email in a menu. */
const UserDialog = ({ viewer }: UserDialogProps) => {
    const menu = useMenuState({ baseId: "user-dialog" });

    if (!viewer?.email) {
        return null;
    }

    const name = viewer.nickname || viewer.email;

    return (
        <Box width="sizeIcon60" marginLeft="space30">
            <MenuButton
                {...menu}
                variant="reset"
                size="reset"
                aria-label="user menu"
            >
                <Tooltip text="Profile">
                    <Box
                        display="flex"
                        alignItems="center"
                        columnGap="space30"
                        paddingX="space20"
                        paddingY="space20"
                        borderRadius="borderRadius20"
                        tabIndex={1}
                    >
                        <Avatar
                            name={name}
                            icon={UserIcon}
                            size="sizeIcon60"
                            variant="user"
                        />
                    </Box>
                </Tooltip>
            </MenuButton>

            <Menu {...menu} aria-label="User menu" placement="bottom-end">
                <Box
                    display="flex"
                    paddingY="space20"
                    paddingX="space40"
                    columnGap="space40"
                    alignItems="center"
                >
                    <Avatar
                        name={name}
                        icon={UserIcon}
                        size="sizeIcon80"
                        variant="user"
                    />
                    <Box>
                        <Box>{name}</Box>
                        <Box element="TEXT_WEAK">{viewer.email}</Box>
                    </Box>
                </Box>
            </Menu>
        </Box>
    );
};

export default UserDialog;
