<script setup lang="ts">

import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  CircleClose,
  Close,
  HomeFilled,
  Minus,
  Refresh
} from "@element-plus/icons-vue";
import TabItem from "@/components/tabs/TabItem.vue";
import {computed, nextTick, onMounted, onUnmounted, watch} from "vue";
import {useTabsStore} from "@/store/tabs-store";

const tabsStore = useTabsStore()

const items = computed({
  get() {
    return tabsStore.tabs
  },
  set(val) {
    tabsStore.tabs = val
  }
})

const scroller = ref<any>(null)
const tabItems = ref<any>(null)
const parent = ref<any>(null)

function getElementsPosition() {
  let parentX = parent.value.offsetLeft;

  let pos = [];
  //获取tabsEl的所有子元素
  let tabs = tabItems.value
  for (let i = 0; i < tabs.length; i++) {
    let el = tabs[i].getEl()
    let x = el.offsetLeft - parentX;
    pos.push({
      x,
      w: el.offsetWidth,
    });
  }
  return pos;
}

function prev() {

  let x = scroller.value.scrollLeft
  let pos = getElementsPosition()
  let index = pos.findIndex(item => item.x + item.w > x)
  if (index > 0) {
    //滚动到pos[index-1]的位置
    scroller.value.scrollTo({
      top: 0,
      left: pos[index - 1].x,
      behavior: "smooth",
    });
  }

}

function next() {

  //获取当前滚动条的位置
  let x = scroller.value.scrollLeft
  let pos = getElementsPosition()
  //获取pos中大于x的第一个元素
  let index = pos.findIndex(item => item.x > x)
  if (index > 0) {
    //滚动到pos[index-1]的位置
    scroller.value.scrollTo({
      top: 0,
      left: pos[index].x + pos[index].w + 10,
      behavior: "smooth",
    });
  }
}

let mouseDownFlag = false;
let startX = 0;
let startScrollLeft = 0;

function mouseDown(e: any) {
  //获取当前滚动条的位置
  startX = e.clientX;
  mouseDownFlag = true;
  startScrollLeft = scroller.value.scrollLeft;
}

function mouseMove(e: any) {
  //获取当前滚动条的位置
  if (mouseDownFlag) {
    let val = e.clientX - startX
    scroller.value.scrollLeft = startScrollLeft - val
  }
}

function mouseUp(e: any) {
  //获取当前滚动条的位置
  startX = 0
  mouseDownFlag = false;
}

function getRightItems(index: number) {
  let arr = []
  for (let i = index - 1; i < items.value.length; i++) {
    if (items.value[i].closeable) {
      arr.push(items.value[i])
    }
  }
  return arr
}

function getLeftItems(index: number) {
  let arr = []
  for (let i = index + 1; i >= 0; i--) {
    if (items.value[i].closeable) {
      arr.push(items.value[i])
    }
  }
  return arr
}

function onClose(item: any) {
  //移除当前的item，然后找到一个最近的item
  //寻找上一个或者下一个closeable不为false的item
  let index = items.value.findIndex(e => e.id === item.id)
  let rights = getRightItems(index)
  let nearNode = null
  if (rights.length > 0) {
    nearNode = rights[0]
  } else {
    let lefts = getLeftItems(index)
    if (lefts.length > 0) {
      nearNode = lefts[lefts.length - 1]
    }
  }

  //移除当前的item
  items.value = items.value.filter(e => e.id !== item.id)

  if (items.value.length === 1) {
    onSelected(items.value[0])
  } else if (nearNode != null) {
    onSelected(nearNode)
  }


}

const router = useRouter()

function onSelected(item: any) {
  //遍历items，将active置为false
  items.value.forEach(e => e.active = e.id === item.id)
  //路由
  if(item.external){
    let url = encodeURIComponent(item.url)
    router.push({
      name: "external",
      query: {
        url: url,
      },
    })
  }else{
    router.push(item.url)
  }
  tabsStore.defaultActive = item.id.toString()
}

function closeCurrent() {
  //找到激活的
  let activeItem = items.value.find(e => e.active)
  if (activeItem != null) {
    //删除当前激活的
    onClose(activeItem)
  }
}

//刷新
function refresh() {
  //刷新当前页面
  router.go(0)
}

function closeOther() {
  //删除所有不为closeable的item
  //只保留closeable为true和active为false的
  items.value = items.value.filter(e => !(e.closeable && !e.active))
}

function closeAll() {
  //删除所有不为closeable的item
  items.value = items.value.filter(e => !e.closeable)
  onSelected(items.value[0])
}

</script>

<template>
  <div class="tabs-view">
    <div class="prev">
      <el-button circle text :icon="ArrowLeft" @click="prev"></el-button>
    </div>
    <div class="tabs-scroll" ref="scroller" @mousedown.left="mouseDown" @mousemove="mouseMove" @mouseup.left="mouseUp">
      <div class="tabs" ref="parent">
        <TabItem
            v-for="(item,i) in items"
            :key="i"
            :item="item"
            @close="onClose"
            @selected="onSelected"
            @close-all="closeAll"
            @close-other="closeOther"
            @refresh="refresh"
            ref="tabItems">

        </TabItem>
      </div>
    </div>
    <div class="next">
      <el-button circle text :icon="ArrowRight" @click="next"></el-button>
    </div>
    <div class="arrow-down">
      <el-dropdown>
        <span class="el-dropdown-link">
          <el-button :icon="ArrowDown" circle text></el-button>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="refresh" :icon="Refresh">{{ $t('Refresh') }}</el-dropdown-item>
            <el-dropdown-item divided @click="closeCurrent" :icon="CircleClose">{{ $t('Close current') }}</el-dropdown-item>
            <el-dropdown-item @click="closeOther" :icon="Minus">{{ $t('Close other') }}</el-dropdown-item>
            <el-dropdown-item @click="closeAll" :icon="Close">{{ $t('Close all') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

    </div>
  </div>
</template>

<style lang="scss">
:root {
  --tabs-bg: #f5f5f5;
  --tabs-item-bg: #fff;
  --tabs-item-bg-hover: #ededed;

  --tabs-text-color: #202225;
  --tabs-item-border: 5px;
}

:root.dark {
  --tabs-bg: #202225;
  --tabs-item-bg: #131313;
  --tabs-item-bg-hover: #666;

  --tabs-text-color: #fff;
}

.tabs-view {
  height: 45px;
  display: flex;
  background-color: var(--tabs-bg);
  padding: 0 10px;
  gap: 5px;
  //border-bottom: 1px solid #eee;
  .prev, .next, .arrow-down {
    display: flex;
    align-items: center;
  }

  .tabs-scroll {
    white-space: nowrap;
    overflow: hidden;
    flex: 1;

    .tabs {
      flex: 1;
      align-items: center;
      display: flex;
      gap: 10px;
      //flex-wrap: wrap;

      .tab {
        margin: 6px 0;
        display: flex;
        align-items: center;
        gap: 6px;
        border-radius: var(--tabs-item-border);
        color: var(--tabs-text-color);
        cursor: pointer;
        transition: all 0.3s;
        padding: 6px 8px 4px;
        background-color: var(--tabs-item-bg);
        user-select: none;

        &:hover {
          background-color: var(--tabs-item-bg-hover);
        }

        .close {
          display: flex;
          align-items: center;
        }
      }

      .active {
        .el-dropdown-link{
          color: var(--primary-color);
        }
        color: var(--primary-color);
      }
    }
  }
}
</style>