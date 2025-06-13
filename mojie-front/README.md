# Vue 项目模板

## 项目概述

这是一个基于 Vue 3 + Vite 的前端项目模板，集成了常用的组件库、状态管理和路由系统，适合快速启动企业级单页应用开发。

## 技术栈

- **前端框架**：Vue 3
- **构建工具**：Vite
- **状态管理**：Pinia
- **路由管理**：Vue Router
- **UI 组件**：Element Plus
- **HTTP 客户端**：Axios
- **CSS 预处理器**：SCSS
- **代码格式化**：ESLint + Prettier
- **Git 钩子**：husky + lint-staged

## 项目结构

```
project-root/
├── public/                  # 静态资源目录
├── src/
│   ├── api/                 # API 接口定义
│   ├── assets/              # 本地资源
│   ├── components/          # 全局组件
│   ├── composables/         # 组合式函数
│   ├── config/              # 项目配置
│   ├── directives/          # 自定义指令
│   ├── layouts/             # 布局组件
│   ├── router/              # 路由配置
│   ├── stores/              # 状态管理
│   ├── styles/              # 全局样式
│   ├── utils/               # 工具函数
│   ├── views/               # 页面视图
│   ├── App.vue              # 根组件
│   └── main.js              # 入口文件
├── .env.development         # 开发环境配置
├── .env.production          # 生产环境配置
├── .eslintrc.cjs            # ESLint 配置
├── .gitignore               # Git 忽略文件
├── index.html               # HTML 模板
├── package.json             # 项目依赖
├── README.md                # 项目说明
├── tsconfig.json            # TypeScript 配置
├── vite.config.ts           # Vite 配置
└── yarn.lock                # 依赖锁文件
```

## 环境准备

1. 安装 Node.js (v16.0.0 或更高版本)
2. 安装包管理器 (推荐 Yarn)

```bash
npm install -g yarn
```

## 安装依赖

```bash
yarn install
```

## 开发环境

```bash
# 启动开发服务器
yarn dev

# 启动开发服务器并指定端口
yarn dev --port 8080

# 启动开发服务器并启用 HTTPS
yarn dev --https
```

## 生产环境

```bash
# 构建生产环境
yarn build

# 预览生产环境
yarn preview
```

## 代码规范

```bash
# 检查代码格式
yarn lint

# 自动修复代码格式
yarn format
```

## 提交规范

本项目使用 Conventional Commits 规范：

```bash
# 提交格式
<type>(<scope>): <subject>
```

### 类型说明

- `feat`: 新功能
- `fix`: 修复问题
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不影响功能）
- `perf`: 性能优化
- `test`: 添加测试
- `chore`: 构建过程或辅助工具的变动

### 示例

```bash
git commit -m "feat(user): 添加用户登录功能"
git commit -m "fix(api): 修复接口数据返回格式"
```

## 配置文件

### 环境变量

项目使用 `.env` 文件配置环境变量，默认提供以下环境配置：

- `.env.development`: 开发环境
- `.env.production`: 生产环境

### Vite 配置

项目的 Vite 配置文件为 `vite.config.ts`，可以根据需要修改。

## 路由配置

路由配置位于 `src/router` 目录下，使用 Vue Router 4。

### 路由结构

```javascript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue')
    }
  ]
})

export default router
```

## 状态管理

项目使用 Pinia 进行状态管理，配置位于 `src/stores` 目录下。

### 状态示例

```typescript
// src/stores/counter.ts
import { defineStore } from 'pinia'

export const useCounterStore = defineStore('counter', {
  state: () => ({
    count: 0
  }),
  getters: {
    doubleCount: (state) => state.count * 2
  },
  actions: {
    increment() {
      this.count++
    }
  }
})
```

## API 请求

项目使用 Axios 进行 HTTP 请求，API 配置位于 `src/api` 目录下。

### API 示例

```typescript
// src/api/user.ts
import request from '@/utils/request'

export function login(data: { username: string; password: string }) {
  return request({
    url: '/api/login',
    method: 'post',
    data
  })
}

export function getUserInfo() {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}
```

## 组件库

项目集成了 Element Plus 组件库，如需使用其他组件库，请参考相应文档。

### 组件使用示例

```vue
<template>
  <div>
    <el-button type="primary">Primary Button</el-button>
    <el-input v-model="inputValue" placeholder="请输入内容" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const inputValue = ref('')
</script>
```

## 部署说明

### 服务器部署

1. 构建生产环境：`yarn build`
2. 将 `dist` 目录上传至服务器
3. 配置 Web 服务器（如 Nginx、Apache 等）

### Nginx 配置示例

```nginx
server {
  listen 80;
  server_name your-domain.com;
  
  root /path/to/your/project/dist;
  index index.html;
  
  location / {
    try_files $uri $uri/ /index.html;
  }
  
  location /api {
    proxy_pass http://your-api-server;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

## 常见问题

### 1. 跨域问题

开发环境下可通过 Vite 配置解决：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://your-api-server',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### 2. ESLint 冲突

如果 ESLint 与编辑器配置冲突，可以在 `.eslintrc.cjs` 中调整规则。

### 3. 依赖安装失败

如果依赖安装失败，尝试清除缓存后重新安装：

```bash
yarn cache clean
yarn install
```

## 贡献指南

1. Fork 项目
2. 创建新分支：`git checkout -b feature/new-feature`
3. 提交代码：`git commit -m "feat: 添加新功能"`
4. 推送分支：`git push origin feature/new-feature`
5. 创建 Pull Request

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
