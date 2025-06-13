export interface ThemeStates {
    primary: string
    themeLayout:string
    setPrimary: (primary: string) => void
    setThemeLayout: (themeLayout: string) => void
    //面包屑
    breadcrumb: boolean
    setBreadcrumb: (state: boolean) => void
    //标签栏
    tabs: boolean
    setTabs: (state: boolean) => void
    reset: () => void
}


export interface LocalesStates {
    locale: string
    setLocale: (locale: string) => void
}

export interface TransitionStates{
    enable: boolean
    setEnable: (enabled: boolean) => void
    type: string
    setType: (type: string) => void
}

//tab
export interface Tab{
    id: number
    closeable: boolean
    active: boolean
    url: string
    text: string
    external: boolean
}
export interface TabsStates{
    tabs: Array<Tab>
    setTabs: (tabs: Array<Tab>) => void
    pushTab: (tab: Tab) => void

    //sidebar激活的menu-item
    defaultActive: string
    setDefaultActive: (active: string) => void
    reset: () => void
}



export interface MenuItemStates {
    id: number
    text: string
    children: Array<MenuItem>
    icon: string
    url: string
    external: boolean
}

export interface MenuStates {
    menus: Array<MenuItem>
    setMenus: (menus: Array<MenuItem>) => void
}