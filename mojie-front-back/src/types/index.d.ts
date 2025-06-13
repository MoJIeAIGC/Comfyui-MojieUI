interface MenuType {
    id: number,
    text: string,
    icon: any,
    url: string,
    external: boolean,
    children: MenuType[]
}

export type {
    MenuType
}
