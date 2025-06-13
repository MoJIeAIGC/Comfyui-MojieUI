<template>
	<div class="img-box" :class="[{right:props.type==='right'},'image-col-' + (props.length>4 ?4:props.length) ]">
<!--    ?x-tos-process=image/resize,w_600/format,heic-->
<!--    ?x-tos-process=image/resize,w_400/sharpen,50/quality,q_50/format,webp-->
		<img v-db-click-img v-draw-start  draggable="true" @click="imageClick" @load="msgLoad"  @dblclick="imageDbClick" :src="props.src+'?x-tos-process=image/resize,w_400/quality,Q_50/format,webp'"  alt=""/>
    <div class="img-tools" v-if="props.type!=='right'">
      <template v-for="item in tools"
                :key="item.id">
        <a-tooltip placement="top">
          <template #title>
            <span>{{item.name}}</span>
          </template>
          <div class="tools-item text-center"
               @click="toolClick(item)"
          >
            <i :class="'iconfont ' + item.icon "></i>
            <!--         {{item.name}}-->
          </div>
        </a-tooltip>

      </template>
<!--       <div class="tools-item text-center"-->
<!--            v-for="item in tools"-->
<!--            :key="item.id"-->
<!--            @click="toolClick(item)"-->
<!--            :title="item.name"-->
<!--       >-->
<!--         <i :class="'iconfont ' + item.icon "></i>-->
<!--&lt;!&ndash;         {{item.name}}&ndash;&gt;-->
<!--       </div>-->
    </div>
	</div>
</template>
<script setup>
import {defineEmits, ref} from 'vue'
	const props = defineProps({
		src: {
			type: String,
			default: ''
		},
    type: {
      type: String,
      default: ''
    },
    length:{
      type: Number,
      default: 1
    }
	})
  const tools = [
    {type: '1', name: '迁移替换',icon:'icon-xijiejingxiu'},
    {type: '2', name: '局部重绘',icon:'icon-caijian1'},
    {type: 'download', name: '下载原图',icon:'icon-xiazai1'},
    {type: 'regenerate', name: '再次生成',icon:'icon-zhongzhi3'},
    // {type: '3', name: '智能扩图',icon:'icon-quanjujingxiu'},
    // {type: '4', name: '内补消除',icon:'icon-neibu'},
    // {type: '5', name: '色彩调节',icon:'icon-secaitiaojie'}
  ]

const emit = defineEmits(['imageClick','imageDbClick','toolClick','retry']);
const imageClick = () => {
  emit('imageClick')
}
const imageDbClick = () => {
  emit('imageDbClick')
}
const msgLoad = (event) => {
   // console.log('msgLoad', event)
}
const toolClick = (item) => {
  if(item.type==='download'){
    window.open(props.src,'_blank')
    return
  }
  if(item.type==='regenerate'){
    emit('retry',item,props.src)
    return;
  }
  emit('toolClick',item,props.src)
}
</script>
<style lang="less" scoped>
.img-box {
	position: relative;
	overflow: hidden;
	min-height: 100px;
  max-width: 100%;
  max-height:50vh;
  //width: 100%;
  img {
    //display: block;
    width: 100%;
    max-width: 400px;
    max-height: calc(40vh - 50px);
    border-radius: 8px;
  }
  &.image-col-2{
    width: calc(50% - 10px);
    min-width: 150px;
    max-height:initial;
    img{
      max-height: initial;
    }
  }
  &.image-col-3{
    width:calc(33% - 10px);
    min-width: 150px;
    max-height:initial;
    img{
      max-height: initial;
    }
  }
  &.image-col-4{
    width:calc(25% - 10px);
    max-height:initial;
    min-width: 150px;
    img{
      max-height: initial;
    }
  }
  //padding-bottom: 60px;
  &.right{
    width: initial;
    text-align: right;
    min-height: 100px;
    height: 120px;
    min-width: 1%;
    img {
      width: initial;
      max-width: 400px;
      max-height: 100%;
      border-radius: 8px;
    }
  }
  .img-tools{
    //position: absolute;
    //bottom: 10px;
    padding: 10px 0;
    .tools-item{
      display: inline-block;
      line-height: 22px;
      padding: 0 10px;
      font-size: 12px;
      cursor: pointer;
      background-color: @bg-page-two-color;
      border-radius: 6px;
      margin-right: 2px;
      .iconfont{
        font-size: 12px;
        color: #dcd1d1;
      }
      &:hover{
        background: @bg-page-color;
        .iconfont{
          color: #FFFFFF;
        }
      }
    }
  }
}	
</style>
