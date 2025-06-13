<script setup lang="ts">

import {Search} from "@element-plus/icons-vue";
const visible = ref(false);



const value = ref()

const sourceData = [
  {
    value: '1',
    label: 'Level one 1',
    children: [
      {
        value: '1-1',
        label: 'Level two 1-1',
        children: [
          {
            value: '1-1-1',
            label: 'Level three 1-1-1',
          },
        ],
      },
    ],
  },
  {
    value: '2',
    label: 'Level one 2',
    children: [
      {
        value: '2-1',
        label: 'Level two 2-1',
        children: [
          {
            value: '2-1-1',
            label: 'Level three 2-1-1',
          },
        ],
      },
      {
        value: '2-2',
        label: 'Level two 2-2',
        children: [
          {
            value: '2-2-1',
            label: 'Level three 2-2-1',
          },
        ],
      },
    ],
  },
  {
    value: '3',
    label: 'Level one 3',
    children: [
      {
        value: '3-1',
        label: 'Level two 3-1',
        children: [
          {
            value: '3-1-1',
            label: 'Level three 3-1-1',
          },
        ],
      },
      {
        value: '3-2',
        label: 'Level two 3-2',
        children: [
          {
            value: '3-2-1',
            label: 'Level three 3-2-1',
          },
        ],
      },
    ],
  },
]
const data = ref(sourceData)

const filterNodeMethod = (value, data) => data.label.includes(value)
</script>

<template>
  <div>
    <el-button :icon="Search" circle text @click="visible = true"></el-button>
    <el-dialog :title="$t('Search')" v-model="visible">
      <div class="input">
        <el-tree-select
            v-model="value"
            :data="data"
            :filter-node-method="filterNodeMethod"
            filterable
            style="width: 240px"
        />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.input{
  padding: 30px 0;
}
</style>