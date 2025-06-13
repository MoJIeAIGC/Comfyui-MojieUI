<script setup lang="ts">
import { useRoute } from "vue-router";
import SearchForm from "@/components/list/SearchForm.vue";
import DataTable from "@/components/list/DataTable.vue";
import DataPagination from "@/components/list/DataPagination.vue";
import DataAction from "@/components/list/DataAction.vue";
import DataAlert from "@/components/list/DataAlert.vue";
import { nextTick, onMounted, watch, ref,  computed,onActivated } from "vue";
import { ElMessage } from "element-plus";
import { getproduct ,delpro} from '../api/OrderApi';
import { updateProduct } from '../api/OrderApi';

const users = ref([]);

const searchUsername = ref('');
const searchPhone = ref('');
// 获取当前路由
const route = useRoute();

// 添加当前选中的 tab
const activeTab = ref('3');

// 封装获取用户数据的方法
const fetchUserData = async () => {
  try {
    const role = route.params.id as string;
    console.log(222222222222222222);
    console.log(role);
    const response = await getproduct();
    users.value = response.data;
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
};


// 在 onMounted 中调用方法
onMounted(() => {
  fetchUserData();
});

onActivated(async () => {
  try {
    const role = route.params.id as string;
    // const role = route.params.;
    console.log(222222222222222222);
    console.log( role);
    const response = await getproduct();
    // usersAll.value = response.data;
    users.value = response.data;
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
});

// 控制编辑弹窗的显示与隐藏
const editDialogVisible = ref(false);
// 存储当前编辑的商品数据
const editedProduct = ref({});

// 处理编辑按钮点击事件
const handleEdit = (index: number, row: any) => {
  editedProduct.value = { ...row }; // 复制当前行的数据
  editDialogVisible.value = true; // 显示编辑弹窗
  console.log(editDialogVisible.value);
  console.log(editedProduct.value);
};

// 处理确认编辑按钮点击事件
const handleConfirmEdit = async () => {
  try {
    // 调用更新商品的 API
    const response = await updateProduct(editedProduct.value);
    if (response.status === 200) {
      // 更新成功，更新本地数据
      const index = users.value.findIndex(user => user.id === editedProduct.value.id);
      if (index !== -1) {
        users.value.splice(index, 1, editedProduct.value);
      }
      ElMessage.success('商品信息更新成功');
      editDialogVisible.value = false; // 关闭编辑弹窗
    } else {
      ElMessage.error('商品信息更新失败');
    }
  } catch (error) {
    console.error('商品信息更新失败', error);
    ElMessage.error('商品信息更新失败');
  }
};

// 处理取消编辑按钮点击事件
const handleCancelEdit = () => {
  editDialogVisible.value = false; // 关闭编辑弹窗
};



const filteredUsers = computed(() => {
  let result = users.value;
  // 根据 way 字段过滤
  result = result.filter(user => user.way === parseInt(activeTab.value));
  if (searchUsername.value) {
    result = result.filter(user => user.description.includes(searchUsername.value));
  }
  console.log(searchPhone);
  return result;
});


// 每页显示的记录数
const pageSize = ref(10);
// 当前页码
const currentPage = ref(1);

// 计算总记录数
const total = computed(() => filteredUsers.value.length);

// 根据当前页码和每页记录数计算要显示的数据
const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredUsers.value.slice(start, end);
});

// 处理页码变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page;
};


// 定义 handleDelete 方法
const handleDelete = async (index: number, row: any) => {
  try {

        // 调用 delexam 函数，假设 row 中有对应的 tagid
    await delpro(row.id); // 这里假设 id 是需要传递的 tagid，根据实际情况修改
    ElMessage.success('删除用户成功');
    // 重新获取数据以更新列表
    fetchUserData(); 
  } catch (error) {
    console.error('删除用户失败', error);
    ElMessage.error('删除用户失败');
  }
};
</script>

<template>
  <div class="grid">
    <div class="table">
      <!-- <search-form /> -->
       <!-- 添加 tab 组件 -->
      <el-tabs v-model="activeTab" class="demo-tabs">
        <el-tab-pane label="积分包" name="3"></el-tab-pane>
        <el-tab-pane label="小程序" name="2"></el-tab-pane>
        <el-tab-pane label="网页端" name="1"></el-tab-pane>
      </el-tabs>
      <div>
        <span>商品名称：</span>
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
          <el-table-column prop="description" label="商品名称"></el-table-column>
          <el-table-column prop="price" label="价格"></el-table-column>
          <el-table-column prop="points" label="点数"></el-table-column>
          
          <el-table-column label="Operations">
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
        </el-table-column>
        </el-table>

      </div>
      <!-- <data-pagination /> -->
      <!-- <el-pagination background layout="prev, pager, next" :total="1000" /> -->
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handleCurrentChange"
      />
    </div>
    <!-- 新增编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑商品信息"
      @close="handleCancelEdit"
    >
        <el-form >
          <el-form-item label="ID">
            <!-- 确保 ID 为只读 -->
            <el-input v-model="editedProduct.id" disabled></el-input>
          </el-form-item>
          <el-form-item label="商品名称">
            <el-input v-model="editedProduct.description"></el-input>
          </el-form-item>
          <el-form-item label="价格">
            <!-- 使用 v-model.number 确保绑定数字类型 -->
            <el-input v-model.number="editedProduct.price"></el-input>
          </el-form-item>
          <el-form-item label="点数">
            <!-- 使用 v-model.number 确保绑定数字类型 -->
            <el-input v-model.number="editedProduct.points"></el-input>
          </el-form-item>
          
        </el-form> 
      <template #footer>
        <el-button @click="handleCancelEdit">取消</el-button>
        <el-button type="primary" @click="handleConfirmEdit">确认</el-button>
      </template>
    </el-dialog>
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