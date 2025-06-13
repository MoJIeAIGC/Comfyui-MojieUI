<script setup lang="ts">
import { useRoute } from "vue-router";
import SearchForm from "@/components/list/SearchForm.vue";
import DataTable from "@/components/list/DataTable.vue";
import DataPagination from "@/components/list/DataPagination.vue";
import DataAction from "@/components/list/DataAction.vue";
import DataAlert from "@/components/list/DataAlert.vue";
import { nextTick, onMounted, watch, ref,  computed ,onActivated} from "vue";
import { ElMessage } from "element-plus";
import { getUser,updateUser ,addproxy} from '../api/userApi';

const users = ref([]);

const searchUsername = ref('');
const searchPhone = ref('');
// 获取当前路由
const route = useRoute();
onMounted(async () => {
  try {
    const role = route.params.id as string;
    // const role = route.params.;
    console.log(222222222222222222);
    console.log( role);
    const response = await getUser();
    // usersAll.value = response.data;
    users.value = response.data.filter(user => user.userRole === role);
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
});
onActivated(async () => {
  try {
    const role = route.params.id as string;
    // const role = route.params.;
    console.log(222222222222222222);
    console.log( role);
    const response = await getUser();
    // usersAll.value = response.data;
    users.value = response.data.filter(user => user.userRole === role);
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
});

const filteredUsers = computed(() => {
  let result = users.value;
  if (searchPhone.value) {
    result = result.filter(user => user.email.includes(searchPhone.value));
  }  
  if (searchUsername.value) {
    result = result.filter(user => user.username.includes(searchUsername.value));
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
    const response = await updateUser(editedProduct.value);
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

// 控制新增弹窗的显示与隐藏
const addDialogVisible = ref(false);
// 存储新增用户的数据
const newUser = ref({
  username: '',
  password: '',
  selectedUser: '', // 改为单个用户ID
  miniUser: '' // 改为单个用户ID
});

// 处理确认新增按钮点击事件
const handleConfirmAdd = async () => {
  try {
    const formData = new FormData();
    formData.append('username', newUser.value.username);
    formData.append('password', newUser.value.password);
    formData.append('webid', newUser.value.selectedUser); // 改为单个用户
    formData.append('miniid', newUser.value.miniUser); // 改为单个用户

    const response = await addproxy(formData);
    if (response.code === 200) {
      ElMessage.success('新增代理用户成功');
      addDialogVisible.value = false;
      // 重新获取用户列表
      const role = route.params.id as string;
      const userResponse = await getUser();
      users.value = userResponse.data.filter(user => user.userRole === role);
      // 重置表单
      newUser.value = {
        username: '',
        password: '',
        miniUser: '',
        selectedUser: ''
      };
      
    } else {
      ElMessage.error('新增代理用户失败');
    }
  } catch (error) {
    console.error('新增代理用户失败', error);
    ElMessage.error('新增代理用户失败');
  }
};

// 处理取消新增按钮点击事件
const handleCancelAdd = () => {
  addDialogVisible.value = false;
  newUser.value = {
    username: '',
    password: '',
    miniUser: '',
    selectedUser: ''
  };
};
// 存储可选的用户列表
const availableUsers = ref([]);

// 获取可选用户列表
const fetchAvailableUsers = async () => {
  try {
    const response = await getUser();
    availableUsers.value = response.data.filter(user => user.userRole === 'user');
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
};

// 处理新增按钮点击事件
const handleAdd = () => {
  fetchAvailableUsers();
  addDialogVisible.value = true;
};
// 用于过滤的计算属性
const filteredAvailableUsers = computed(() => {
  const searchText = newUser.value.selectedUser?.toString() || '';
  if (!searchText) {
    return availableUsers.value.filter(user => !user.username.startsWith('wx_'));
  }
  return availableUsers.value.filter(user => 
    user.username.toLowerCase().includes(searchText.toLowerCase())
  );
});

const filteredAvailableUsers2 = computed(() => {
  const searchText = newUser.value.miniUser?.toString() || '';
  if (!searchText) {
    return availableUsers.value.filter(user => user.username.startsWith('wx_'));
  }
  return availableUsers.value.filter(user => 
    user.username.toLowerCase().includes(searchText.toLowerCase())
  );
});
</script>

<template>
  <div class="grid">
    <div class="table">
      <!-- <search-form /> -->
      <div>
        <span>用户名：</span>
        <el-input v-model="searchUsername" style="width: 240px"></el-input>
        <span style="margin-left: 20px;">邮箱：</span>
        <el-input v-model="searchPhone" style="width: 240px"></el-input>
        <!-- <el-button @click="handleSearch">搜索</el-button> -->
      </div>
      <el-divider />
      <div v-if="route.params.id === 'proxy'" style="margin-bottom: 20px;">
        <el-button type="primary" @click="handleAdd">新增代理用户</el-button>
      </div>
      <data-action v-if="route.params.id === 'admin'"/>
      <!-- <div>
        <data-alert />
      </div> -->
      <div class="table-box" ref="tableBox">
        <!-- 使用 el-table 组件渲染用户数据 -->
        <el-table :data="paginatedUsers" stripe>
          <!-- <el-table-column prop="id" label="ID"></el-table-column> -->
          <el-table-column prop="username" label="用户名"></el-table-column>
          <el-table-column prop="phone" label="电话号码"></el-table-column>
          <el-table-column prop="email" label="邮箱"></el-table-column>

          <!-- <el-table-column prop="userRole" label="用户角色"></el-table-column> -->
          <!-- <el-table-column prop="userAITime" label="AI 使用时间"></el-table-column> -->
          <el-table-column prop="points" label="积分"></el-table-column>
          <el-table-column prop="create_time" label="创建时间"></el-table-column>
          <el-table-column prop="remark" label="备注"></el-table-column>
          <el-table-column label="Operations">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.$index, scope.row)">
              Edit
            </el-button>
            <!-- <el-button
              size="small"
              type="danger"
              @click="handleDelete(scope.$index, scope.row)"
            >
              Delete
            </el-button> -->
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
      title="编辑用户信息信息"
      @close="handleCancelEdit"
    >
        <el-form >
          <el-form-item label="ID">
            <!-- 确保 ID 为只读 -->
            <el-input v-model="editedProduct.id" disabled></el-input>
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="editedProduct.email"></el-input>
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
    <!-- 新增代理用户对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="新增代理用户"
      @close="handleCancelAdd"
    >
      <el-form>
        <el-form-item label="用户名">
          <el-input v-model="newUser.username"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newUser.password" type="password"></el-input>
        </el-form-item>
        <el-form-item label="网页端关联用户">
          <el-select
            v-model="newUser.selectedUser"
            placeholder="请选择用户"
            filterable
          >
            <el-option
              v-for="user in filteredAvailableUsers"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            >
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="小程序关联用户">
          <el-select
            v-model="newUser.miniUser"
            placeholder="请选择用户"
            filterable
          >
            <el-option
              v-for="user in filteredAvailableUsers2"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            >
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleCancelAdd">取消</el-button>
        <el-button type="primary" @click="handleConfirmAdd">确认</el-button>
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