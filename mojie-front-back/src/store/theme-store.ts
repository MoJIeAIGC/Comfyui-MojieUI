import {defineStore} from "pinia";
import {primary} from "@/theme/colors";
import {setPrimaryColor} from "@/theme";
import type {ThemeColor, ThemeStates} from "@/store/interface";

const sidebarTheme = {
    default: {
        "--sidebar-text-active-color": "#FFF",
        "--sidebar-bg-color": "#001525",
        "--sidebar-text-color": "rgba(255, 255, 255, 0.65)",
        "--sidebar-text-hover-color": "#FFF",
        "--sidebar-bg-hover-color": "#182637",
        "--sidebar-banner-color": "#FFF",
    },
    light: {
        "--sidebar-text-active-color": "#FFF",
        "--sidebar-bg-color": "#FFF",
        "--sidebar-text-color": "#000",
        "--el-menu-hover-bg-color": "#FFF",

        "--sidebar-text-hover-color": "#000",
        "--sidebar-bg-hover-color": "#f3f3f5",
        "--sidebar-banner-color": "#000",
    },
    dark: {
        "--sidebar-text-active-color": "#FFF",
        "--sidebar-bg-color": "#001525",
        "--sidebar-text-color": "rgba(255, 255, 255, 0.65)",
        "--sidebar-text-hover-color": "#000",
        "--sidebar-bg-hover-color": "#f3f3f5",
        "--sidebar-banner-color": "#FFF",
    }
}
export const useThemeStore = defineStore("theme-store", {
    state: (): ThemeStates => ({
        primary: primary,
        themeLayout: "default",
        //面包屑
        breadcrumb: true,
        //标签栏
        tabs: true,
    }),
    actions: {
        setPrimary(color: string) {
            this.primary = color
            setPrimaryColor(color)
        },
        setThemeLayout(layout: string) {

            this.themeLayout = layout
            let config = sidebarTheme[layout]

            for (const key in config) {
                document.documentElement.style.setProperty(key, config[key])
            }
        },
        setBreadcrumb(state: boolean) {
            this.breadcrumb = state
        },
        setTabs(state: boolean) {
            this.tabs = state
        },
        reset() {
            this.setPrimary(primary)
            this.setThemeLayout("default")

            this.breadcrumb = true
            this.tabs = true
        }
    },
    persist: {
        enabled: true,
        strategies: [
            {key: "_theme_store", storage: localStorage},
        ]
    },
});