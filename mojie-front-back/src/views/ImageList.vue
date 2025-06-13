<script setup lang="ts">
import { useRoute } from "vue-router";
import SearchForm from "@/components/list/SearchForm.vue";
import DataTable from "@/components/list/DataTable.vue";
import DataPagination from "@/components/list/DataPagination.vue";
import DataAction from "@/components/list/DataAction.vue";
import DataAlert from "@/components/list/DataAlert.vue";
import { nextTick, onMounted, watch, ref,  computed } from "vue";
import { ElMessage } from "element-plus";
import { getAllImage } from '@/api/imageApi';
import { addTemp } from '@/api/imageApi';
import { gettemplates, gettag ,deltemp,getrealtag,editTemp} from '@/api/templateApi';

const users = ref([]);
// 标签列表
const tagList = ref([]);
// 真标签列表
const realtagList = ref([]);
const searchUsername = ref('');
const searchPhone = ref('');
const selectedTagForAdd = ref();
const selectedrealTagForAdd = ref();
const generationMethod = ref('');
const total = ref(0);

// 获取当前路由
const route = useRoute();
const fetchImageData = async () => {
  try {
    const response = await getAllImage(currentPage.value, pageSize.value);
    users.value = response.data.data;
    total.value = response.data.total || response.data.length;
  } catch (error) {
    console.error('获取用户数据失败', error);
  }
};
onMounted(async () => {
  await fetchImageData();
  fetchTags();
  fetchrealTags();
});

// 模拟生成方式选项
const generationMethods = [
  { value: 'GPT4o', label: 'GPT4o' },
  // { value: 'Gemini', label: 'Gemini' },
  { value: 'flex', label: 'flex   和   kontext_pro_1' },
  { value: 'dou', label: '奇画3.0  和   kontext_pro_2' },
];

// 获取标签数据
const fetchTags = async () => {
  try {
    const response = await gettag();
    if (Array.isArray(response.data)) {
      tagList.value = response.data;
    } else {
      console.error('获取标签数据失败，响应不是数组:', response);
    }
  } catch (error) {
    console.error('获取标签数据失败:', error);
  }
};

// 获取标签数据
const fetchrealTags = async () => {
  try {
    const response = await getrealtag(1);
    if (Array.isArray(response.data)) {
      realtagList.value = response.data;
    } else {
      console.error('获取标签数据失败，响应不是数组:', response);
    }
  } catch (error) {
    console.error('获取标签数据失败:', error);
  }
};

const filteredUsers = computed(() => {
  let result = users.value;
  if (searchPhone.value) {
    result = result.filter(user => user.user_name.includes(searchPhone.value));
  }  
  // if (searchUsername.value) {
  //   result = result.filter(user => user.username.includes(searchUsername.value));
  // }
  console.log(searchPhone);
  return result;
});


// 每页显示的记录数
const pageSize = ref(5);
// 当前页码
const currentPage = ref(1);

// 计算总记录数
// const total = computed(() => filteredUsers.value.length);

// 根据当前页码和每页记录数计算要显示的数据
const paginatedUsers = computed(() => {

  return filteredUsers.value;
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

// 控制弹窗显示隐藏
const dialogVisible = ref(false);
// 存储当前选中行的数据
const currentRowData = ref({

});
// 存储多选框的值
const checkbox1 = ref(false);
const checkbox2 = ref(false);

// 处理操作按钮点击事件
const handleEditClick = (row) => {
  currentRowData.value = { ...row };
  dialogVisible.value = true;
};

// 修改清空函数，添加新数据的清空
const clearFormData = () => {
  selectedTagForAdd.value = [];
  selectedrealTagForAdd.value = [];
};

// 处理弹窗确定按钮点击事件
const handleDialogConfirm = async () => {
  try {
    const formData = new FormData();
    formData.append('title', currentRowData.value.prompt);
    formData.append('image', currentRowData.value.image_url); 
    formData.append('method', currentRowData.value.model_used);
    formData.append('image_list', currentRowData.value.image_list);
    formData.append('realtag', selectedTagForAdd.value.join(','));
    formData.append('tag', selectedrealTagForAdd.value.join(','));
    // formData.append('checkbox1', checkbox1.value ? '1' : '0');
    // formData.append('checkbox2', checkbox2.value ? '1' : '0');

    await addTemp(formData);
    ElMessage.success('添加模板成功');
    dialogVisible.value = false;
  } catch (error) {
    console.error('添加模板失败', error);
    ElMessage.error('添加模板失败');
  }
};
</script>

<template>
  <div class="grid">
    <div class="table">
      <!-- <search-form /> -->
      <div>
        <!-- <span>用户名：</span>
        <el-input v-model="searchUsername" style="width: 240px"></el-input> -->
        <span style="margin-left: 20px;">用户名：</span>
        <el-input v-model="searchPhone" style="width: 240px"></el-input>
        <!-- <el-button @click="handleSearch">搜索</el-button> -->
      </div>
      <el-divider />
      <!-- <data-action /> -->
      <!-- <div>
        <data-alert />
      </div> -->
      <div class="table-box" ref="tableBox">
        <!-- 使用 el-table 组件渲染用户数据 -->
        <el-table :data="paginatedUsers" stripe>
          <!-- <el-table-column prop="id" label="ID"></el-table-column> -->
          <el-table-column prop="user_name" label="用户名"></el-table-column>
          <el-table-column prop="prompt" label="提示词"></el-table-column>
          <el-table-column prop="model_used" label="模型"></el-table-column>
          <el-table-column prop="upload_time" label="创建时间"></el-table-column>
          <el-table-column label="上传图片">
          <template #default="scope">
            <!-- 添加一个容器并设置 flex 布局 -->
            <div style="display: flex; flex-wrap: wrap; gap: 5px;">
              <div v-for="(path, index) in scope.row.image_list.split(',')" :key="index">
                <img 
                  v-if="path"
                  :src="path" 
                  style="width: 50px; height: 50px; object-fit: cover;"
                />
              </div>
            </div>
          </template>
        </el-table-column>
          <!-- <el-table-column prop="image_list" label="图片结果"></el-table-column> -->
          <el-table-column label="图片结果">
            <template #default="scope">
              <img :src="scope.row.image_url" alt="图片" style="max-width: 100px; max-height: 100px;">
            </template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="scope">
              <el-button @click="handleEditClick(scope.row)">转瀑布流</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <!-- <data-pagination /> -->
      <!-- <el-pagination background layout="prev, pager, next" :total="1000" /> -->
      <!-- 弹窗 -->
      <el-dialog v-model="dialogVisible" title="编辑数据">
      <el-form>
        <el-form-item label="提示词">
          <el-input v-model="currentRowData.prompt" ></el-input>
        </el-form-item>
        <el-form-item label="上传图片 ">
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
              <div v-for="(path, index) in currentRowData.image_list.split(',')" :key="index">
                <img 
                  v-if="path"
                  :src="path" 
                  style="width: 50px; height: 50px; object-fit: cover;"
                />
              </div>
            </div>
        </el-form-item>
        <el-form-item label="图片结果">
          <img :src="currentRowData.image_url" alt="图片" style="max-width: 100px; max-height: 100px;">
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="selectedTagForAdd" placeholder="请选择标签" multiple>
            <el-option
              v-for="tag in realtagList"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="生成方式">
          <el-select v-model="currentRowData.model_used" placeholder="请选择生成方式">
            <el-option
              v-for="method in generationMethods"
              :key="method.value"
              :label="method.label"
              :value="method.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择种类">
          <!-- 添加 multiple 属性，使选择框变为多选 -->
          <el-select v-model="selectedrealTagForAdd" placeholder="请选择标签" multiple>
            <el-option
              v-for="tag in tagList"
              :key="tag.id"
              :label="tag.description"
              :value="tag.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="() => { clearFormData(); dialogVisible = false; }">取消</el-button>
          <el-button type="primary" @click="handleDialogConfirm">确定</el-button>
        </span>
      </template>
      </el-dialog>
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
        @click="currentPage = 1; fetchImageData()"
      >
        首页
      </el-button>
      <el-button 
        :disabled="currentPage <= 1" 
        @click="currentPage--; fetchImageData()"
      >
        上一页
      </el-button>
      
      <el-button
        v-for="page in Math.ceil(total / pageSize)"
        :key="page"
        :type="currentPage === page ? 'primary' : ''"
        @click="currentPage = page; fetchImageData()"
      >
        {{ page }}
      </el-button>
      
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage++; fetchImageData()"
      >
        下一页
      </el-button>
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage = Math.ceil(total / pageSize); fetchImageData()"
      >
        末页
      </el-button>
    </div> -->
    <el-pagination
    :page-size="pageSize"
    layout="prev, pager, next"
    :total="total"
    v-model:current-page="currentPage"
    @change=fetchImageData
    @prev-click=fetchImageData
    @next-click=fetchImageData
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