import {defineStore} from "pinia";
import type {Tab, TabsStates, TransitionStates} from "@/store/interface";


export const useTabsStore = defineStore("tabs", {

    state: (): TabsStates => ({
        tabs: [{
            id: 2,
            url: "/",
            text: "主控台",
            closeable: false,
            active: true
        }],
        defaultActive: "2",
    }),
    actions: {
        setDefaultActive(id: string) {
            this.defaultActive = id
        },
        setTabs(tabs: Array<Tab>) {
            this.tabs = tabs
        },
        pushTab(tab: Tab) {

            //默认值
            if (typeof tab.closeable == "undefined") {
                tab.closeable = true
            }
            if (typeof tab.active == "undefined") {
                tab.active = true
            }

            //如果tab已经存在，则将其他tab的active状态设置为false
            let t = this.tabs.find(item => item.id === tab.id)
            if (t) {
                this.tabs.forEach(item => {
                    item.active = false
                })
                t.active = true
            } else {
                //将其他tab的active状态设置为false
                this.tabs.forEach(item => {
                    item.active = false
                })
                tab.active = true
                this.tabs.push(tab)
            }
            //导航
            if (tab.external) {
                //url编码
                let url = encodeURIComponent(tab.url)
                this.$router.push({
                    name: "external",
                    query: {
                        url: url
                    },
                })
            } else {
                this.$router.push(tab.url)
            }
            this.defaultActive = tab.id.toString()
        },
        reset() {
            this.tabs = [{
                id: 2,
                url: "/",
                text: "主控台",
                closeable: false,
                active: true
            }]
            this.defaultActive = "2"
            this.$router.push('/')
        }
    },
    persist: {
        enabled: true,
        strategies: [
            {key: "_tabs", storage: localStorage},
        ]

    }
})
