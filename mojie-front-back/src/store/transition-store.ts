import {defineStore} from "pinia";
import type {TransitionStates} from "@/store/interface";

export const useTransitionStore = defineStore("transition", {
    state: (): TransitionStates => ({
        enable: false,
        type: "fade",
    }),
    actions: {
        setEnable(enable: boolean) {
            this.enable = enable;
        },
        setType(type: string) {
            this.type = type;
        }
    },
    persist: {
        enabled: true,
        strategies: [
            {key: "_transition", storage: localStorage},
        ]

    }
})
