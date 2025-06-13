<script setup lang="ts">
import {Check, Checked} from "@element-plus/icons-vue";
import {computed} from "vue";

const props = defineProps({
  color: String,
  active: Boolean,
})
const emit = defineEmits(['change'])

const style = computed(() => {
  return {
    backgroundColor: props.color,
  }
})
</script>

<template>
  <div class="block" @click="emit('change',color)" :style="style">
    <el-icon v-if="active" :size="12">
      <Check/>
    </el-icon>
  </div>
</template>

<style scoped lang="scss">
$size: 40px;
.block {
  width: $size;
  height: $size;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  border-radius: 5px;
}
</style>