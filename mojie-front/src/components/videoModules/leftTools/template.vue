<template>
  <div class="new-box">
    <div class="search-box">
      <a-input class="ipt" v-model:value="_data.searchKey" placeholder="关键字" @change="search">
        <template #suffix>
          <div class="" @click="search">
            <i class="iconfont icon-fangdajingsousuo"></i>&nbsp;搜索
          </div>
        </template>
      </a-input>
    </div>

    <div class="tab-model-box">
      <div class="tab-model-item text-center" v-for="item in modelList" :key="item.value"> <i class="iconfont icon-GPT"></i>&nbsp;{{ item.label}}</div>
    </div>

    <div class="category_box" v-if="category.length>0">
      <left-circle-filled class="pre-icon no-select" @click="preItem"/>
      <div class="category_item_box" ref="scrollRef">
        <div v-for="(item,index) in category"
             :id="'category_'+index"
             :key="item.id"
             class="category_item"
             :class="{active: item.id ===selectedCategory}" @click="changeCategoryId(item.id)">{{ item.description }}
        </div>
      </div>
      <right-circle-filled class="next-icon no-select" @click="nextItem"/>
    </div>

    <div class="tag-box" v-if="tag.length>0">
      <left-circle-filled class="pre-icon no-select" @click="preTagItem"/>
      <div class="tag-item-box" ref="scrollTagRef">
        <div
            v-for="(item,index) in tag"
            :id="'tag_'+index"
            :key="item.id" class="tag-item"
            :class=" {'active' :item.id === selectedTag }"
            @click="changeTagId(item.id)"
        >{{ item.name }}
        </div>
      </div>
      <right-circle-filled class="next-icon no-select" @click="nextTagItem"/>
    </div>

    <div class="examples_grid_box flex-1">
      <a-spin tip="加载中..." :spinning="loading">
        <Pullfresh @refreshEnd="refreshEnd">
          <div class="examples_grid_box_scroll no-select" ref="listRef" @scroll="listScroll">
            <div class="example_box" v-for="item in example" :key="item.id">
              <div class="img-box flex items-center justify-center">
                <img v-draw-start class="example_image" v-lazy="item.image_path+'?x-tos-process=image/resize,w_200/quality,q_50/format,webp'" v-db-click-img alt=""/>
              </div>
              <div class="example_text line1 text-center">{{ item.title }}</div>
            </div>
            <div class="text-center mt-10 no-data" v-if="_data.page.total <= example.length">没更多数据</div>
          </div>
        </Pullfresh>
      </a-spin>
    </div>

  </div>
</template>

<script setup>
import {defineEmits, reactive, defineProps, ref, onMounted} from 'vue'
import {queryCategory, queryTemplates, queryTag} from "@/api/templates.js"
import {RightCircleFilled, LeftCircleFilled} from '@ant-design/icons-vue';
import Pullfresh from "@/components/scroll/pullRefresh.vue"
import {modelList} from '@/options/model.js'
const emit = defineEmits(['change']);
const _data = reactive({
  searchKey: '',
  scrollIndex: 0,
  scrollTagIndex: 0,
  sessionList: [],
  page: {
    total: 0,
    page: 1,
    pageSize: 30
  }
})
const props = defineProps({
  chatId: {
    type: Number,
    default: -1
  }
})
const listRef = ref()
const loading = ref(false)
const scrollRef = ref()
const scrollTagRef = ref()
const category = ref([])
const tag = ref([])
const selectedCategory = ref(0)
const selectedTag = ref(0)
const example = ref([])
let timer = null
onMounted(async () => {
  getExamplesFromCategory()
  const categoryResponse = await queryCategory()
  category.value = categoryResponse.data

  const tagResponse = await queryTag()
  tag.value = tagResponse.data
  // selectedTag.value = tagResponse.data[0].id

})
const search = () => {
  if(timer) clearTimeout(timer)
  timer = setTimeout(() => {
    example.value = []
    _data.page.page = 1
    getExamplesFromCategory()
  },700)
}
const changeCategoryId = (categoryId) => {
  selectedCategory.value = categoryId
  example.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}

const changeTagId = (tagId) => {
  if (tagId === selectedTag.value) {
    selectedTag.value = 0
  } else {
    selectedTag.value = tagId
  }
  example.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}
const preItem = () => {
  if (_data.scrollIndex > 0) _data.scrollIndex--
  const el = document.getElementById('category_' + _data.scrollIndex);
  if (el) {
    scrollRef.value.scrollLeft = el.offsetLeft - 30
  }
}
const nextItem = () => {
  const el = document.getElementById('category_' + (_data.scrollIndex + 1));
  const scrollWidth = scrollRef.value.scrollWidth - scrollRef.value.clientWidth
  if (el.offsetLeft < scrollWidth) _data.scrollIndex++
  if (el) {
    scrollRef.value.scrollLeft = el.offsetLeft - 30
  }
}
const preTagItem = () => {
  if (_data.scrollTagIndex > 0) _data.scrollTagIndex--
  const el = document.getElementById('tag_' + _data.scrollTagIndex);
  if (el) {
    scrollTagRef.value.scrollLeft = el.offsetLeft - 30
  }
}
const nextTagItem = () => {
  const el = document.getElementById('tag_' + (_data.scrollTagIndex + 1));
  const scrollWidth = scrollTagRef.value.scrollWidth - scrollTagRef.value.clientWidth
  if (el.offsetLeft < scrollWidth) _data.scrollTagIndex++
  if (el) {
    scrollTagRef.value.scrollLeft = el.offsetLeft - 30
  }
}

const getExamplesFromCategory = () => {
  loading.value = true;
  queryTemplates(
      {
        cateid: selectedCategory.value,
        tagid: selectedTag.value,
        page_size: _data.page.pageSize,
        page: _data.page.page,
        title: _data.searchKey
      }
  ).then(result => {
    _data.page.total = result.data.total
    example.value = Array.from(example.value.concat(result.data.data));
  }).finally(() => {
    loading.value = false;
  })
}
const refreshEnd = () => {
  example.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}
const listScroll = (e) => {
  if (loading.value) return
  const scrollHeight = listRef.value.scrollHeight - listRef.value.clientHeight
  if (scrollHeight < (listRef.value.scrollTop + 50)) {
    if (_data.page.total <= example.value.length) return;
    _data.page.page += 1
    getExamplesFromCategory()
  }
}
</script>

<style scoped lang="less">
.new-box {
  display: flex;
  flex-direction: column;
  padding: 10px;
  height: 100%;

  .search-box {
    padding: 15px 0;

    .ipt {
      padding: 5px 20px;
      border-radius: 20px;
      height: 30px;
      background-color: inherit;
      border-color: #2F3034;
      font-size: 14px;

      :deep(.ant-input) {
        background-color: inherit;
        font-size: 14px;
      }

      .iconfont {
        font-size: 16px;
      }
    }
  }

  .tab-model-box {
    //display: flex;
    //background: #423e45;
    //border-radius: 20px;
    //height: 35px;
    .tab-model-item{
      display: inline-block;
      width: calc(50% - 5px);
      font-size: 12px;
      line-height: 32px;
      border: 1px solid #3A3A3A;
      border-radius: 8px;
      margin-top: 10px;
      cursor: pointer;
      .iconfont{
        font-size: 12px;
      }
      &:nth-child(2n+1){
        margin-right: 10px;
      }
    }
    .tab-left {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      cursor: pointer;
      background: @btn-bg-two-color;
      height: 100%;
      border-radius: 20px;
    }

    .tab-right {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      cursor: pointer;
      border-radius: 20px;
      background: #423e45;
      height: 100%;
    }

  }

  .category_box {
    margin-top: 15px;
    overflow: hidden;
    position: relative;
    padding: 0 30px;

    .category_item_box {
      width: 100%;
      white-space: nowrap;
      overflow: hidden;
      line-height: 40px;

      .category_item {
        padding-right: 10px;
        display: inline-block;
        cursor: pointer;
        align-items: center;
        color: #8c8c8c;
        font-size: 14px;
        box-sizing: border-box;

        &:last-child {
          padding-right: 0;
        }

        &.active {
          color: #5A50FE;
        }
      }
    }

  }

  .tag-box {
    overflow: hidden;
    position: relative;
    padding: 8px 30px;

    .tag-item-box {
      width: 100%;
      white-space: nowrap;
      overflow: hidden;
      line-height: 24px;

      .tag-item {
        margin-right: 10px;
        display: inline-block;
        cursor: pointer;
        align-items: center;
        color: #8c8c8c;
        font-size: 12px;
        box-sizing: border-box;
        padding: 0 20px;
        border: solid 1px #8c8c8c;
        border-radius: 8px;

        &.active {
          color: #5A50FE;
          border-color: #5A50FE;
        }
      }
    }

    .tag_selected_box {
      color: #5A50FE;
      border: solid 2px #5A50FE;
    }

  }

  .tag-box::-webkit-scrollbar {
    display: none;
  }

  .examples_grid_box {
    margin-top: 10px;
    height: 0;

    :deep(.ant-spin-nested-loading) {
      width: 100%;
      height: 100%;
    }

    :deep(.ant-spin-container) {
      width: 100%;
      height: 100%;
    }

    .examples_grid_box_scroll {
      height: 100%;
      overflow: scroll;

      &::-webkit-scrollbar {
        display: none;
      }

      .example_box {
        display: inline-block;
        width: calc(33.33% - 6px);
        margin-right: 9px;

        &:nth-child(3n) {
          margin-right: 0;
        }

        .img-box {
          width: 100%;
          height: 120px;
          background-color: @bg-page-two-color;
          border-radius: 8px;
          padding: 5px;

          .example_image {
            max-height: 100%;
            width: 100%;
          }
        }

        .example_text {
          font-size: 14px;
          margin-top: 5px;
          padding-bottom: 15px;
        }
      }
    }
  }

  .page-box {
    :deep(.ant-pagination-item) {
      min-width: 26px;
      height: 26px;
      line-height: 26px;
      font-size: 12px;
      border-radius: 50%;
    }

    :deep(.ant-pagination-prev) {
      min-width: 26px;
      height: 26px;
      line-height: 26px;
      font-size: 12px;
      border-radius: 50%;
    }

    :deep(.ant-pagination-next) {
      min-width: 26px;
      height: 26px;
      line-height: 26px;
      font-size: 12px;
      border-radius: 50%;
    }

    :deep(.ant-pagination-jump-prev) {
      min-width: 26px;
      height: 26px;
      line-height: 26px;
      font-size: 12px;
      border-radius: 50%;
    }

    :deep(.ant-pagination-jump-next) {
      min-width: 26px;
      height: 26px;
      line-height: 26px;
      font-size: 12px;
      border-radius: 50%;
    }

    :deep(.ant-pagination-item-link) {
      border-radius: 50%;
    }
  }
}

.pre-icon {
  position: absolute;
  cursor: pointer;
  font-size: 20px;
  top: 10px;
  left: 0;
}

.next-icon {
  position: absolute;
  cursor: pointer;
  font-size: 20px;
  top: 10px;
  right: 0;
}

@media screen and (max-width: 1300px) {
  .examples_grid_box {
    .example_box {
      display: inline-block;
      width: calc(50% - 5px) !important;
      margin-right: 10px !important;

      &:nth-child(2n) {
        margin-right: 0 !important;
      }
    }

  }
}
</style>