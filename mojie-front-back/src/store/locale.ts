//定义一个useLocale的State
import {defineStore} from "pinia";
import type {LocalesStates} from "@/store/interface";

const locale = "zh"
export const useLocaleStore = defineStore("locale", {
    state: (): LocalesStates => ({
        locale: locale,
    }),
    actions: {
        setLocale(locale: string) {
            this.locale = locale;
        }
    },
    persist: {
        enabled: true,
        strategies: [
            {key: "_locale", storage: localStorage},
        ]

    }
})
