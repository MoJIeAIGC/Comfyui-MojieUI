import {defineConfig, loadEnv} from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import sitemap from 'vite-sitemap';

// https://vitejs.dev/config/
export default defineConfig(({command, mode, ssrBuild}) => {
  // 获取当前环境的配置
  const config = loadEnv(mode, './');
  return {
    plugins: [
        vue(),
      sitemap({
        baseURL: 'www.qihuaimage.com',
        urls: [
          "home",
          "gallery",
          'chat'
        ],
      }),
    ],
    base: config.VITE_PUBLIC_PATH,
    resolve: {
      alias: {
        '@': path.join(__dirname, 'src')
      }
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          additionalData: `@import "${path.resolve(__dirname, 'src/assets/css/global-style.less')}";`
        }
      }
    },
    server: {
      host: '0.0.0.0',
      port: '8100',
      proxy: {
        '/api/': {
          target: "http://118.145.137.155:9152/api",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    }
  }

})
