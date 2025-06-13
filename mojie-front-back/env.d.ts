/// <reference types="vite/client" />
interface ImportMetaEnv {
    readonly VITE_HOST: string
    readonly VITE_PORT: number
    // 更多环境变量...
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}