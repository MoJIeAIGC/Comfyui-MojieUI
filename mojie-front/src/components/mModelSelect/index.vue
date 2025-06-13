<template>
  <a-popover placement="rightTop" trigger="click" v-model:visible="visible" color="#121212"  overlayClassName="m-model-select-popover">
    <template #content>
      <div class="modal-select">
      	<template v-for="(aItem, aIndex) in modelList" :key="aIndex">
      		<div v-if="aItem.show !== false" class="item" 
      			:class="{'cursor': !!aItem.value,active:aItem.value === userStore.modelType}"
      			@click="setModelType(aItem)">
	      		<div class="flex items-center">
<!--	      			<img class="icon" :src="aItem.img"/>-->
              <i class="iconfont" :class="aItem.icon"></i>
		      		<div class="text-box">
		      			<div class="t1">{{aItem.label}}</div>
		      			<div class="t2">{{aItem.tip}}</div>
		      		</div>
<!--		      		<template v-if="aItem.value">-->
<!--                <check-circle-filled :style="iconStyle" class="check-icon" />-->
<!--		      		</template>-->
	      		</div>
	      	</div>
      	</template>
      </div>
    </template>
    <div class="m-model-select-btn">
      <div class="flex items-center">
        <i class="iconfont flex" :class="currentLabel.icon"></i>
        <div class="text-box flex-1">
          <div class="t1">{{currentLabel.label}}</div>
          <div class="t2">{{currentLabel.tip}}</div>
        </div>
        <right-outlined />
      </div>
		</div>
	</a-popover>
</template>

<script setup>
import {computed, ref} from 'vue'
import {useUserStore} from '@/store/userStore';
import {RightOutlined} from '@ant-design/icons-vue';
import {modelList} from '@/options/model.js'
const userStore = useUserStore();

	// 当前的label

  const visible = ref(false)
	const currentLabel = computed(() => {
    return getChoice()
	})
	// 获取当前选中项
function getChoice() {
		let res = {};
		for(let i = 0; i < modelList.length; i++) {
			let aItem = modelList[i];
			if(aItem.value === userStore.modelType) {
				res = aItem;
				break
			}
		}
		return res;
}

	// 设置模型类型
	function setModelType(item) {
    userStore.setModelType(item.value);
    visible.value = false
	}

</script>

<style lang="less">
.m-model-select-popover {
   .ant-popover-inner-content{
    padding: 10px 0;
  }
  .iconfont{
    font-size: 25px;
    color: #FFFFFF;
  }
	.modal-select {
		width: 200px;
    padding: 10px;
		.item {
			padding: 4px 5px;
      border-radius: 4px;
			&.cursor {
				cursor: pointer;
				&:not(.active):hover {
					background: #877a7a;
				}
			}
			.t1 {
				font-size: 14px;
				color: #fff;
			}
			.t2 {
				font-size: 9px;
				color: #aaa;
			}
			.text-box {
				flex: 1;
				width: 0;
				padding: 0 0 0 10px;
			}
			&.active {
        background:@bg-page-two-color;
        .check-icon{
          color:#9B4FFE!important;
        }
			}
		}
	}
}
.m-model-select-btn {
  margin-left: 0;
  //background: inherit;
  background: @bg-page-color;
  color: #797979;
  border: 1px solid #2A2A2A;
  padding:10px;
  font-size: 16px;
  width: 220px;
  border-radius: 8px;
  cursor: pointer;
  //overflow: hidden;
  .t1 {
    font-size: 14px;
    color: #fff;
  }
  .t2 {
    font-size: 9px;
    color: #aaa;
  }
  .text-box {
    flex: 1;
    width: 0;
    padding: 0 0 0 10px;
  }
  .iconfont{
    font-size: 25px;
    color: #FFFFFF;
  }
}
</style>