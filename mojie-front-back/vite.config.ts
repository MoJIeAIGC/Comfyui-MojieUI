import path from "path"
import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import fs from 'fs'  // 添加这行导入
import {ElementPlusResolver} from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        // compression({
        //     algorithm: 'gzip',
        //     verbose: true,
        //     ext: '.gz',
        //     threshold: 10240,
        //     deleteOriginFile: false,
        // }),
        vue(),
        vueJsx(),
        // VueDevTools(),
        AutoImport({
            resolvers: [ElementPlusResolver()],
            imports: ['vue', 'vue-router', "pinia", '@vueuse/core'],
        }),
        Components({
            resolvers: [ElementPlusResolver()],
        }),
    ],
    resolve: {
        alias: {
            '~/': `${path.resolve(__dirname, 'src')}/`,
            '@/': `${path.resolve(__dirname, 'src')}/`,
        }
    },
    base: '/',
    build: {
        assetsDir: 'assets',
        rollupOptions: {
            output: {
                chunkFileNames: 'assets/js/[name]-[hash].js',
                entryFileNames: 'assets/js/[name]-[hash].js',
                assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
                manualChunks(id) {
                    if (id.includes('node_modules')) {
                        //第三方包分离
                        // return id
                        //     .toString()
                        //     .split("node_modules/")[1]
                        //     .split("/")[0]
                        //     .toString();
                        return 'vendor';
                    }
                },
            },
        },
        terserOptions: {
            compress: {
                drop_console: true,
                drop_debugger: true,
            },
        },
        //关闭文件计算
        reportCompressedSize: false,
        //关闭sourcemap
        sourcemap: false,
    },
    server: {
        host: true,
        https: {
            key: fs.readFileSync(path.resolve(__dirname, 'src/cert/qihuaimage.com.key')),
            cert: fs.readFileSync(path.resolve(__dirname, 'src/cert/qihuaimage.com.crt'))
        }
    },
})
