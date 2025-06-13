<template>
	<div class="footer-setting flex" v-if="lineUpNumber!=='none'&&lineUpNumber!==0">
    <div class="flex-1">正在排队中...前面还有{{lineUpNumber}}人</div>
    <div class="cancel" @click="cancel">取消</div>
	</div>
</template>
<script setup>
import {computed, defineEmits, ref} from 'vue'
import {queryGenerateImage} from "@/api/product.js";
	const props = defineProps({
		row: {
			type: Object,
			default: ()=>{
				return {}
			}
		},
    queueList: {
      type: Array,
      default: []
    }
})
const lineUpNumber = computed(() => {
  let queue = props.queueList.find(item => item.task_id == props.row.comfyUI_task_id)
  if(!queue) {
    // emit('change',false)
    return 'none'
  }
  // emit('change',true)
  return queue &&queue.queue_position?  queue.queue_position :0
});

const emit = defineEmits(['cancel','change']);
const cancel = () => {
   queryGenerateImage(`/api/image/tasks/${props.row.comfyUI_task_id}/cancel`).then(res => {
     emit('cancel')
   })
}
</script>
<style lang="less" scoped>
.footer-setting{
  max-width:400px;
  font-size: 15px;
  color: #422D60;
  .cancel{
    cursor:pointer;
  }
}
</style>
