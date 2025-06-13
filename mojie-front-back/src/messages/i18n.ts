import {createI18n} from 'vue-i18n'
import zh from './zh'

const messages = {
    en: {
        zh: "简体中文",
        en: "English",
        TransitionDesc:"Transition refers to how to make the transition when you click on the menu bar to open different pages, enabling transition animation will get a better visual experience."
    },
    zh
}
const lang = navigator.language.substring(0, 2)

export const i18n = createI18n({
    locale: lang, // set locale
    fallbackLocale: 'en', // set fallback locale
    messages, // set locale messages
    missingWarn: false,
    formatFallbackMessages: false,
    silentTranslationWarn: true,
    silentFallbackWarn: true,
})

export const t = i18n.global.t