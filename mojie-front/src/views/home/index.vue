<template>
  <div class="new-box">
    <div class="head-img">
      <a-carousel autoplay>
        <img src="../../assets/image/home/1.png" @click="toChat" alt="">
        <img src="../../assets/image/home/2.png" @click="toChat" alt="">
      </a-carousel>
    </div>
    <div class="flex">
      <div class="search-box">
        <a-input class="ipt" v-model:value="_data.searchKey" @change="search" placeholder="关键字">
          <template #suffix>
            <div @click="search">
              <i class="iconfont icon-fangdajingsousuo"></i>&nbsp;搜索
            </div>
          </template>
        </a-input>
      </div>
<!--      <div class="tab-model-box flex-1">-->
<!--        <div class="tab-model-item text-center" :class="{active:_data.selectModel===item.value }" v-for="item in modelList" :key="item.value" @click="selectModelChange(item)"> <i class="iconfont" :class="item.icon"></i>&nbsp;{{ item.label}}</div>-->
<!--      </div>-->
    </div>



    <div class="category_box">
      <div class="category_item_box">
        <div v-for="(item,index) in category"
             :id="'category_'+index"
             :key="item.id"
             class="category_item text-center"
             :class="{active: item.id ===selectedCategory}" @click="changeCategoryId(item.id)">{{ item.description }}
        </div>
      </div>
    </div>
    <div class="home_box flex-1">
      <a-spin tip="加载中..." :spinning="loading">
        <Pullfresh @refreshEnd="refreshEnd">
          <div class="list-box no-select" ref="listRef" @scroll="listScroll">
            <waterfall v-if="list.length>0" :data="list" :col="5" ref="waterfallRef" :gutterWidth="10">
              <div
                  class="cell-item"
                  v-for="(item, index) in list"
                  :key="index"
                  @click="() => handleClick(item,index)">
<!--                v-db-click-img-->
                <img v-if="item.image_path_res" v-lazy="getChildList(item.image_path_res) +'?x-tos-process=image/resize,w_400/quality,Q_50/format,webp'" alt=""/>
                <div class="item-body">
                  <div class="item-footer">
                    <div class="modal-name">
                      <i class="iconfont" :class="getModelByKey(item.generation_method).icon"></i>&nbsp;{{ getModelByKey(item.generation_method).label }}
                    </div>
                    <div class="like"  :class="['like-' + index, {active:item.is_liked ===1}]" @click.stop="doLike(item,index)">
                      <i class="iconfont icon-_like"></i>
                      <div class="like-total">{{ item.like_count }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </waterfall>
            <div class="text-center no-data mt-30" v-if="_data.page.total <= list.length">没更多数据</div>
          </div>
        </Pullfresh>
      </a-spin>
    </div>
    <ExampleModel ref="exampleModalRef" @refresh="refreshItem"></ExampleModel>
  </div>
</template>

<script setup>
import {defineEmits, reactive, ref, onMounted, nextTick} from 'vue';
import {queryCategory, queryTempGood, queryExamples} from "@/api/example.js";
import Pullfresh from "@/components/scroll/pullRefresh.vue"
import ExampleModel from "@/components/exampleModel/index.vue"
import {useRouter} from "vue-router";
import {getModelByKey} from "@/utils/utils.js";
const router = new useRouter();
const emit = defineEmits(['change']);
const _data = reactive({
  selectModel:'',
  searchKey: '',
  scrollIndex: 0,
  sessionList: [],
  page: {
    total: 0,
    page: 1,
    pageSize: 30
  }
})
const category = ref([])
const listRef = ref()
const waterfallRef = ref()
const exampleModalRef = ref()
const selectedCategory = ref(0)
const list = ref([])
const loading = ref(false)
let timer = null

onMounted(async () => {
  getExamplesFromCategory()
  const categoryResponse = await queryCategory()
  category.value = categoryResponse.data
})
const getChildList = (urls) => {
  if(!urls) return ''
  return urls.split(',')[0]
}
const search = () => {
  if(timer) clearTimeout(timer)
  timer = setTimeout(() => {
    list.value = []
    _data.page.page = 1
    getExamplesFromCategory()
  },700)
}
const selectModelChange = (item) => {
  _data.selectModel =_data.selectModel === item.value ?'':item.value
  list.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}

const toChat = () => {
  router.push({path: '/chat'})
}
const changeCategoryId = (categoryId) => {
  selectedCategory.value = selectedCategory.value ===  categoryId ? 0: categoryId
  list.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}
const listScroll = (e) => {
  if (loading.value) return
  const scrollHeight = listRef.value.scrollHeight - listRef.value.clientHeight
  if (scrollHeight < (listRef.value.scrollTop + 50)) {
    if (_data.page.total <= list.value.length) return;
    _data.page.page += 1
    getExamplesFromCategory()
  }
}

const refreshEnd = () => {
  list.value = []
  _data.page.page = 1
  getExamplesFromCategory()
}
const handleClick = (item,index) => {
   exampleModalRef.value.open({...item,index: index})
}
const doLike = (item,index) => {
  // waterfallRef.value.resize()
  queryTempGood({
    example_id:item.id
  }).then(res=>{
    if(res.code!==200) return
    let damos = document.getElementsByClassName('like-' + index)
    if(item.is_liked ===1) {
      item.is_liked = 0
      item.like_count -= 1
    } else {
      item.is_liked = 1
      item.like_count += 1
    }
    list.value[index] = JSON.parse(JSON.stringify(item))
    for (const node of damos) {
      if(item.is_liked ===1){
        node.classList.add('active')
      } else {
        node.classList.remove('active')
      }
      const childNode = node.getElementsByClassName('like-total');
      childNode[0].innerText  = item.like_count + ''
    }
  })
}
const refreshItem = (item,index) => {
  let damos = document.getElementsByClassName('like-' + index)
  list.value[index] = JSON.parse(JSON.stringify(item))
  for (const node of damos) {
    if(item.is_liked ===1){
      node.classList.add('active')
    } else {
      node.classList.remove('active')
    }
    const childNode = node.getElementsByClassName('like-total');
    childNode[0].innerText  = item.like_count + ''
  }
}
const getExamplesFromCategory = () => {
  // loadMore()
  loading.value = true;
  const _modelType={
    'flex':'flex',
    'gpt-4o-image':'GPT4o',
    'qiHua':'dou',
  }
  queryExamples({
    cateid: selectedCategory.value,
    page_size: _data.page.pageSize,
    page: _data.page.page,
    title:_data.searchKey,
    model:   _modelType[_data.selectModel] || ''
  }).then(result => {
    _data.page.total = result.data.total
    list.value = Array.from(list.value.concat(result.data.data));
  }).finally(() => {
    nextTick(()=>{
      loading.value = false;
    })
  })
}

</script>

<style scoped lang="less">
.new-box {
  padding: 10px;
  height: 100%;
  display: flex;
  flex-direction: column;
  .head-img{
    width: 100%;
    img{
     width: 100%;
     cursor: pointer;
    }
  }
  .search-box {
    padding: 15px 0 0;
    width: 300px;

    .ipt {
      padding: 5px 20px;
      border-radius: 20px;
      width: 400px;
      height: 36px;
      background-color: #222325;
      border-color: #222325;
      font-size: 14px;

      :deep(.ant-input) {
        background-color: inherit;
        font-size: 14px;
      }

      .iconfont {
        font-size: 18px;
      }
    }
  }
  .tab-model-box {
    //display: flex;
    //background: #423e45;
    //border-radius: 20px;
    //height: 35px;
    .tab-model-item {
      display: inline-block;
      width: 160px;
      font-size: 12px;
      line-height: 28px;
      border: 1px solid #3A3A3A;
      border-radius: 8px;
      margin-top: 15px;
      cursor: pointer;
      margin-left: 10px;
      .iconfont {
        font-size: 12px;
      }
      &.active {
        background: @btn-bg-color;
      }
    }
  }
  .ipt:hover {
  border-color: #3557FF; /* 悬停时边框变为蓝色 */
  transition: border-color 0.3s ease; /* 添加过渡效果 */
  box-shadow: 0 0 0 2px rgba(53, 87, 255, 0.2); /* 添加蓝色光晕效果 */
}


  .category_box {
    position: relative;
    padding: 10px 0;

    .category_item_box {
      width: 100%;
      //white-space: nowrap;
      //overflow: hidden;

      .category_item {
        padding: 0 10px;
        display: inline-block;
        cursor: pointer;
        align-items: center;
        color: #8c8c8c;
        font-size: 14px;
        box-sizing: border-box;
        background: #212225;
        border: 1px solid #3D3F44;
        margin: 0 10px 10px 0;
        border-radius: 15px;

        &.active {
          color: #FFFFFF;
          background: #1F2B68;
          border: 1px solid #3D57E1;
        }
      }
    }

  }
  .home_box{
    height: 0;
    :deep(.ant-spin-nested-loading) {
      width: 100%;
      height: 100%;
    }

    :deep(.ant-spin-container) {
      width: 100%;
      height: 100%;
    }

    .list-box {
      width: 100%;
      height: 100%;
      overflow: auto;

      .cell-item {
        width: 100%;
        // margin-bottom: 18px;
        background: @bg-page-color;
        border-radius: 12px 12px 12px 12px;
        overflow: hidden;
        box-sizing: border-box;
        margin-bottom: 10px;
        position: relative;

        img {
          // border-radius: 12px 12px 0 0;
          width: 100%;
          height: auto;
          display: block;
        }

        .item-body {
          position: absolute;
          width:  100%;
          bottom: 10px;
          padding: 10px;
          .item-footer {
            position: relative;
            display: flex;
            align-items: center;

            .modal-name {
              position: absolute;
              left: 0;
              display: flex;
              align-items: center;
              cursor:  pointer;
              background-color: rgba(0,0,0,0.4);
              padding: 2px 10px;
              border-radius: 15px;
              font-size: 12px;
              .iconfont{
                font-size: 12px;
              }
            }

            .like {
              position: absolute;
              right: 0;
              display: flex;
              align-items: center;
              cursor:  pointer;
              background-color: rgba(0,0,0,0.4);
              padding: 2px 10px;
              border-radius: 15px;
              .iconfont{
                font-size: 12px;
              }
              &.active {
                .iconfont{
                  color: #ff4479;
                }
                .like-total {
                  color: #ff4479;
                }
              }

              .like-total {
                margin-left: 5px;
                font-size: 12px;
                color: #999999;
              }
            }
          }
        }
      }
    }
  }
}

@media screen and (max-width: 1200px) {

}
</style>