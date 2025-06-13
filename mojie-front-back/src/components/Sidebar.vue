<script lang="ts" setup>

import SubMenu from "@/components/sidebar/SubMenu.vue"
import {computed, onMounted} from "vue";
import {useTabsStore} from "@/store/tabs-store";
import {useStorage} from "@vueuse/core";
import {useMenusStore} from "@/store/menu-store";

const handleOpen = (key: string, keyPath: string[]) => {
  // console.log(key, keyPath)
}
const handleClose = (key: string, keyPath: string[]) => {
  // console.log(key, keyPath)
}



const menusStore = useMenusStore()

onMounted(async () => {
  menusStore.setMenu([{
    id: 1,
    text: 'Dashboard',
    children: [
      {
        id: 2,
        text: '主控台',
        url: '/',
      },
      // {
      //   id: 201,
      //   text: '监控大屏1',
      //   url: '/scene/111',
      // }, {
      //   id: 301,
      //   text: '外部大屏',
      //   url: '/scene/2222',
      //   //是否为外链
      //   external: true,
      // }
      ]
  },
    {
      id: 4,
      text: "系统管理", children: [{
        id: 401,
        text: '用户管理',
        children: [{
          id: 4011,
          text: '管理员',
          url: '/list/admin',
        }, {
          id: 4012,
          text: '普通用户',
          url: '/list/user',
        }, {
          id: 4013,
          text: '代理人',
          url: '/list/proxy',
        }]
      }, {
        id: 402,
        text: '模板管理',
        children: [{
          id: 4021,
          text: '模板',
          url: '/temp/list',
        }, {
          id: 4022,
          text: '模板分类标签',
          url: '/text/list',
        }]
      }, {
        id: 403,
        text: '范例管理',
        children: [{
          id: 4031,
          text: '范例',
          url: '/exam/list',
        }, {
          id: 4032,
          text: '范例分类标签',
          url: '/examcat',
        }]
      }, {
        id: 404,
        text: '权限管理',
        url: '/permission/list',
      }, {
        id: 405,
        text: '生成记录管理',
        url: '/image/list',
      }, {
        id: 406,
        text: '订单管理',
        url: '/order/list',
      }, {
        id: 407,
        text: '套餐管理',
        url: '/product/list',
      }, {
        id: 408,
        text: '对列管理',
        url: '/queue',
      }]
    },
    // {id: 408, text: "社区首页", url: 'http://turingmj.com/home', external: true}
  ])
})

//折叠展开
const collapse = useStorage("collapse", false)
const router = useRouter()

function push(url: string) {
  router.push(url)
}

const tabsStore = useTabsStore()


</script>

<template>
  <div :class="{sidebar:true,collapse:collapse}">
    <div class="banner" @click="push('/')">
      <img src="../assets/logo.svg" alt="logo" class="logo">
      <h3 class="title">摩诘后台</h3>
    </div>
    <el-menu
        active-text-color="var(--sidebar-text-active-color)"
        text-color="var(--sidebar-text-color)"
        background-color="var(--sidebar-bg-color)"
        :default-active="tabsStore.defaultActive"
        class="menu"

        :collapse="collapse"
        @open="handleOpen"
        @close="handleClose">

      <SubMenu v-for="(menu,index) in menusStore.menus" :key="index" :menu="menu"></SubMenu>
    </el-menu>
  </div>
</template>

<style lang="scss">
.router-url-active {
  //不显示下划线
  text-decoration: none;
}

.sidebar:not(.el-menu--collapse) {
  display: flex;
  flex-direction: column;
  background-color: var(--sidebar-bg-color);
  color: var(--sidebar-text-color);
  width: 208px;
  //右边显示阴影
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);

  .title {
    color: var(--sidebar-active-color);
  }

  .menu {
    flex: 1 1 0;
  }

  .sidebar-footer {
    height: 48px;
  }

  .el-menu {
    border-right: none;
  }

  .el-menu-item {
    margin: 5px;
    border-radius: 10px;
    height: 40px;
    line-height: 40px;
    transition: width 0.5s;
  }

  .el-menu-item.is-active {
    background-color: var(--sidebar-active-color);
  }

  .banner {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    gap: 10px;
    height: 65px;
    cursor: pointer;

    img {
      max-width: 30px;
      max-height: 30px;
    }

    .title {
      //最大1行
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--sidebar-banner-color);
    }
  }
}

.collapse:not(.el-menu--collapse) {
  width: auto;

  .banner {
    padding: 5px;
    justify-content: center;

    .title {
      display: none;
    }
  }

  .el-sub-item {
    width: 48px;
  }

  span {
    display: none;
  }

  .el-menu-item {
    //margin: 0;
    //width: 48px;
    //padding: 5px;
    justify-content: center;
  }


}
</style>

