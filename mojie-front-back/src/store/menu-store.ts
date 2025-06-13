import {defineStore} from "pinia";
import type {MenuStates, TransitionStates} from "@/store/interface";

export const useMenusStore = defineStore("menus", {
    state: (): MenuStates => ({
        menus: [],
    }),
    actions: {
        setMenu(menus: any) {
            this.menus = menus;
        },
    }
})
