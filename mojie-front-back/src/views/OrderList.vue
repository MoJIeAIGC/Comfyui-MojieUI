<script setup lang="ts">
import { useRoute } from "vue-router";
import SearchForm from "@/components/list/SearchForm.vue";
import DataTable from "@/components/list/DataTable.vue";
import DataPagination from "@/components/list/DataPagination.vue";
import DataAction from "@/components/list/DataAction.vue";
import DataAlert from "@/components/list/DataAlert.vue";
import { nextTick, onMounted, watch, ref,  computed } from "vue";
import { ElMessage } from "element-plus";
import { getOrder } from '../api/OrderApi';
const activeTab = ref('1');

const users = ref([]);
const total = ref(0);
// 每页显示的记录数
const pageSize = ref(10);
// 当前页码
const currentPage = ref(1);
const searchUsername = ref('');
const searchPhone = ref('');
// 获取当前路由
const route = useRoute();
const fetchOrderData = async () => {
  try {
    const role = route.params.id as string;
    console.log(222222222222222222);
    console.log(role);
    const response = await getOrder( currentPage.value, pageSize.value);
    users.value = response.data.data;
    console.log(users.value);
    total.value = response.data.total || response.data.length;
    console.log(total.value);
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
};
onMounted(async () => {
  await fetchOrderData();
});

const filteredUsers = computed(() => {
  let result = users.value;
  // if (searchUsername.value) {
  //   result = result.filter(user => user.user_name.includes(searchUsername.value));
  // }
  // console.log(searchPhone);
  return result;
});






// 根据当前页码和每页记录数计算要显示的数据
const paginatedUsers = computed(() => {
  let result = filteredUsers.value;
  // result = filteredUsers.value.filter(user => user.status === parseInt(activeTab.value));
  return result;
});

// 处理页码变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page;
};

// 定义 handleDelete 方法
const handleDelete = async (index: number, row: any) => {
  try {
    // 调用删除用户的 API
    // await deleteUser(row.id); 
    // 从本地数据中移除该用户
    // users.value.splice(index, 1); 
    ElMessage.success('删除用户成功');
  } catch (error) {
    console.error('删除用户失败', error);
    ElMessage.error('删除用户失败');
  }
};

// 定义 handleDelete 方法
const handleEdit = async (index: number, row: any) => {
  try {
    // 调用删除用户的 API
    // await deleteUser(row.id); 
    // 从本地数据中移除该用户
    // users.value.splice(index, 1); 
    ElMessage.success('删除用户成功');
  } catch (error) {
    console.error('删除用户失败', error);
    ElMessage.error('删除用户失败');
  }
};
</script>

<template>
  <div class="grid">
    <div class="table">
      <!-- <el-tabs v-model="activeTab" class="demo-tabs">
        <el-tab-pane label="已支付" name="1"></el-tab-pane>
        <el-tab-pane label="未支付" name="0"></el-tab-pane>
      </el-tabs> -->
      <!-- <search-form /> -->
      <div>
        <span>用户名：</span>
        <el-input v-model="searchUsername" style="width: 240px"></el-input>
        <!-- <span style="margin-left: 20px;">手机号：</span>
        <el-input v-model="searchPhone" style="width: 240px"></el-input> -->
        <!-- <el-button @click="handleSearch">搜索</el-button> -->
      </div>
      <el-divider />
      <data-action v-if="route.params.id === 'admin'"/>
      <!-- <div>
        <data-alert />
      </div> -->
      <div class="table-box" ref="tableBox">
        <!-- 使用 el-table 组件渲染用户数据 -->
        <el-table :data="paginatedUsers" stripe>
          <!-- <el-table-column prop="id" label="ID"></el-table-column> -->
          <el-table-column prop="user_name" label="用户名"></el-table-column>
          <el-table-column prop="order_no" label="订单号"></el-table-column>
          <el-table-column prop="total_amount" label="订单总金额"></el-table-column>
          <el-table-column prop="actual_amount" label="实付金额"></el-table-column>
          <el-table-column prop="product" label="商品信息"></el-table-column>
          <el-table-column prop="status" label="订单状态">
            <template #default="scope">
              {{ scope.row.status === 0 ? '未支付' : 
                scope.row.status === 1 ? '已支付' : 
                scope.row.status }}
            </template>
          </el-table-column>
          <el-table-column prop="create_time" label="创建时间"></el-table-column>
          <el-table-column prop="payment_method" label="支付方式"></el-table-column>
          <el-table-column prop="remark" label="备注"></el-table-column>
          <!-- <el-table-column label="Operations">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.$index, scope.row)">
              Edit
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(scope.$index, scope.row)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column> -->
        </el-table>
      </div>
      <!-- <data-pagination /> -->
      <!-- <el-pagination background layout="prev, pager, next" :total="1000" /> -->
      <!-- <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handleCurrentChange"
      /> -->
    </div>
    <!-- <div class="fixed-pagination">
      <el-button 
        :disabled="currentPage <= 1" 
        @click="currentPage = 1; fetchOrderData()"
      >
        首页
      </el-button>
      <el-button 
        :disabled="currentPage <= 1" 
        @click="currentPage--; fetchOrderData()"
      >
        上一页
      </el-button>
      
      <el-button
        v-for="page in Math.ceil(total / pageSize)"
        :key="page"
        :type="currentPage === page ? 'primary' : ''"
        @click="currentPage = page; fetchOrderData()"
      >
        {{ page }}
      </el-button>
      
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage++; fetchOrderData()"
      >
        下一页
      </el-button>
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage = Math.ceil(total / pageSize); fetchOrderData()"
      >
        末页
      </el-button>
    </div> -->
    <el-pagination
    :page-size="pageSize"
    layout="prev, pager, next"
    :total="total"
    v-model:current-page="currentPage"
    @change=fetchOrderData
    @prev-click=fetchOrderData
    @next-click=fetchOrderData
    style="margin: 20px auto; display: flex; justify-content: center;"
      :small="false"
  />
  </div>
</template>

<style scoped lang="scss">
.table-box {
  flex: 1 1 0;
  width: 100%;
}

.grid {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 20px;
}

.info-bar {
  margin: 20px 0;
}

.grid-title {
  padding: 20px;
  background-color: var(--panel-bg);
}

.table {
  flex: 1;
  padding: 20px;
  border-radius: 5px;
  background-color: var(--panel-bg);
  display: flex;
  flex-direction: column;
}
</style>