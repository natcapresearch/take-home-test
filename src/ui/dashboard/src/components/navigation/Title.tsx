import { useEffect } from "react";

interface TitleProps {
    title?: string;
}

function Title({ title }: TitleProps) {
    useEffect(() => {
        const newTitle = title ? `${title} | Natcap` : "Natcap";
        document.title = newTitle;
    }, [title]);

    return null;
}

export default Title;
