<script setup lang="ts">
import {computed, ref} from "vue"
import {ArrowDown, ArrowUp, RefreshRight, Search} from "@element-plus/icons-vue";

const collapse=ref(true);

const fields = ref<any>([{
  label:'全局搜索',
  prop: 'q',
  value: '',
},{
  label: '规则编号',
  prop: 'id',
  value:'看电视剧付款了电视剧'
}, {
  label: '规则描述',
  prop: 'desc',
  value:'',
}, {
  label: '操作',
  prop: 'action',
  value:'',
},{
  label:'更新日期',
  prop:'date',
  type:'date',
  value:''
},{
  label:'使用状态',
  prop:'status',
  type:'select',
  value:'',
  data:[{
    label:'关闭',
    value:'0'
  },{
    label:'开启',
    value:'1'
  }]
}])
import {Ripple} from "@/directive/ripple";
const vRipple=Ripple

const style=computed(()=>{

  return {
    height:collapse.value?'40px':''
  }
})
</script>

<template>
  <div class="search-form">
    <div class="rows" :style="style">
        <div class="field-item"  v-for="item in fields">
          <div class="label">{{item.label}}：</div>
          <div class="component">
            <el-date-picker v-if="item.type==='date'"
                v-model="item.value"
                type="date"
                :placeholder="item.label"
            />
            <el-select v-else-if="item.type==='select'" v-model="item.value" :placeholder="item.label" clearable>
              <el-option v-for="option in item.data" :key="option.value" :label="option.label" :value="option.value"/>
            </el-select>
            <el-input v-else :placeholder="item.label" v-model="item.value" clearable/>
          </div>
        </div>
    </div>
    <div class="actions">
      <el-button type="primary" v-ripple :icon="Search" plain>查询</el-button>
      <el-button :icon="RefreshRight">重置</el-button>
      <el-button text :icon="ArrowUp" v-if="!collapse" @click="collapse=!collapse">收起</el-button>
      <el-button text :icon="ArrowDown" v-else @click="collapse=!collapse">展开</el-button>
    </div>
  </div>
</template>
<style lang="scss">
.el-date-editor.el-input{
  width: 100%!important;
}
</style>
<style scoped lang="scss">
.search-form{
  display: flex;
  .rows{
    display: flex;
    flex-flow: row wrap;
    gap: 20px;
    overflow: hidden;
  }
  .field-item{
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: start;
    max-width: 300px;
    .label{
      min-width: 80px;
      display: inline-block;
      flex-grow: 0;
      overflow: hidden;
      white-space: nowrap;
      text-align: end;
      vertical-align: middle;
      font-size: 14px;
      width: auto;
    }
    .component{
      width: 200px;
      overflow: hidden;
    }
  }
  .actions{
    display: flex;
    justify-content: flex-end;
  }
}

</style>