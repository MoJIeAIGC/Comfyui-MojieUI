<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { gettemplates, gettag ,addTemp,deltemp,getrealtag,editTemp} from '@/api/templateApi';
import { ElMessage } from 'element-plus';
import { getqueue} from '@/api/queue';

// 当前页码
const currentPage = ref(1);
// 每页显示的数量
const pageSize = ref(7);
// 所有数据
const allData = ref([]);
// 搜索关键词
const searchQuery = ref(''); 
// 标签列表
const tagList = ref([]);
// 真标签列表
const realtagList = ref([]);
// 选中的标签 id
const selectedTagId = ref(0);
const total = ref(0);
// 弹窗显示状态
const dialogVisible = ref(false);
// 上传的图片文件
// const uploadedFile = ref<File | null>(null);
// const imageUrl = ref<string | null>(null);
// 新增时选择的标签
const selectedTagForAdd = ref();
const selectedrealTagForAdd = ref();
// 新增响应式变量，用于存储图片的 URL
const uploadedImageUrl = ref<string | null>(null);
// 提交新增
// 新增：生成方式
const generationMethod = ref('');
// 新增：文本输入框的值
const inputText = ref('');
// 新增响应式变量
const title = ref('');
const category = ref('');
const remarks = ref('');

// 模拟生成方式选项
const generationMethods = [
  { value: 'GPT4o', label: 'GPT4o' },
  { value: 'Gemini', label: 'Gemini' },
];

// 修改 submitAdd 函数，添加新数据
const submitAdd = async () => {
  // if (uploadedFiles.value.length === 0 || !selectedTagForAdd.value) {
  //   ElMessage.error('请上传图片并选择标签');
  //   return;
  // }
  const formData = new FormData();
  // 添加多个文件
  uploadedFiles.value.forEach((file) => {
    formData.append('image', file);
  });
  uploadedFiles2.value.forEach((file) => {
    formData.append('mask', file);
  });
  formData.append('tag', selectedTagForAdd.value.join(','));
  formData.append('realtag', selectedrealTagForAdd.value.join(','));
  // 新增：添加生成方式和文本输入框的值
  // formData.append('generation_method', generationMethod.value);
  // formData.append('text', inputText.value);
  // 新增：添加标题、种类和备注
  formData.append('title', title.value);
  // formData.append('category', category.value);
  // formData.append('remarks', remarks.value);

  try {
    const response = await addTemp(formData);
    if (response.code === 200) {
      ElMessage.success('添加成功');
      clearFormData(); // 调用清空函数
      dialogVisible.value = false;
      // 释放图片的临时 URL
      imageUrls.value.forEach((url) => {
        URL.revokeObjectURL(url);
      });
      imageUrls.value = [];
      imageUrls2.value.forEach((url) => {
        URL.revokeObjectURL(url);
      });
      imageUrls2.value = [];
      // 重新获取数据
      fetchData(selectedTagId.value);
    } else {
      ElMessage.error('添加失败');
    }
  } catch (error) {
    console.error('添加模板失败:', error);
    ElMessage.error('添加失败，请稍后重试');
  }
};

// 修改清空函数，添加新数据的清空
const clearFormData = () => {
  uploadedFiles.value = [];
  uploadedFiles2.value = [];
  imageUrls.value.forEach((url) => {
    URL.revokeObjectURL(url);
  });
  imageUrls2.value.forEach((url) => {
    URL.revokeObjectURL(url);
  });
  imageUrls.value = [];
  imageUrls2.value = [];
  selectedTagForAdd.value = [];
  selectedrealTagForAdd.value = [];
  // 新增：清空生成方式和文本输入框的值
  generationMethod.value = '';
  inputText.value = '';
  // 新增：清空标题、种类和备注
  title.value = '';
  category.value = '';
  remarks.value = '';
};




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
    const response = await getrealtag();
    if (Array.isArray(response.data)) {
      realtagList.value = response.data;
    } else {
      console.error('获取标签数据失败，响应不是数组:', response);
    }
  } catch (error) {
    console.error('获取标签数据失败:', error);
  }
};


// 获取数据
const fetchData = async (e) => {
  console.log('fetchData 函数被调用', e);
  try {
    const response = await getqueue( currentPage.value, pageSize.value);
    console.log('API 响应:', response);
    if (Array.isArray(response.data.completed_tasks.results)) {
      allData.value = response.data.completed_tasks.results;
      // 确保API返回了total字段
      total.value = response.data.completed_tasks.count || response.data.length;
    } else {
      console.error('API 响应不是数组:', response);
      allData.value = [];
    }
  } catch (error) {
    console.error('获取示例数据失败:', error);
  }
};

  // 新增：处理文件选择事件
  // 修改为数组类型
  const uploadedFiles = ref<File[]>([]);
  const imageUrls = ref<string[]>([]);
 

    // 新增：处理文件选择事件
  // 修改为数组类型
  const uploadedFiles2 = ref<File[]>([]);
  const imageUrls2 = ref<string[]>([]);


    // 新增：处理文件选择事件
    const handleFileChange2 = (files: any) => {
    // 处理多个文件
    const newFiles = Array.isArray(files.raw) ? files.raw : [files.raw]; 
    newFiles.forEach((file) => {
      // 检查文件是否已经存在于 uploadedFiles 中
      const isDuplicate = uploadedFiles2.value.some((existingFile) => existingFile.name === file.name && existingFile.size === file.size);
      if (!isDuplicate) {
        uploadedFiles2.value.push(file);
        const reader = new FileReader();
        reader.onload = (e) => {
          imageUrls2.value.push(e.target?.result as string);
        };
        reader.readAsDataURL(file);
      }
    });
    console.log('选择的文件:', uploadedFiles2.value);
    console.log('生成的图片 URL:', imageUrls2.value);
  };


// 处理分页变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page;
};

// 处理搜索输入
const handleSearch = () => {
  currentPage.value = 1; // 搜索时重置页码
};

// 处理标签点击事件
const handleTagClick = (tagId: number) => {
  currentPage.value = 1;
  fetchData();
};



// 计算过滤后的数据
const filteredData = computed(() => {
  if (!searchQuery.value) return allData.value;
  return allData.value.filter(item => 
    item.title && item.title.toLowerCase().includes(searchQuery.value.toLowerCase())
  );
});

// 计算当前页的数据，基于过滤后的数据
const paginatedData = computed(() => {
  // 直接返回API返回的全部数据，不再进行前端分页
  return filteredData.value;
});
// 定义 handleDelete 方法
const handleDelete = async (index: number, row: any) => {
  try {

        // 调用 delexam 函数，假设 row 中有对应的 tagid
    await deltemp(row.id); // 这里假设 id 是需要传递的 tagid，根据实际情况修改
    ElMessage.success('删除用户成功');
    // 重新获取数据以更新列表
    fetchData(); 
  } catch (error) {
    console.error('删除用户失败', error);
    ElMessage.error('删除用户失败');
  }
};

// 更新总数为过滤后的数据数量
// const total = computed(() => filteredData.value.length);

// 新增：选中的新标签 id
const selectedRealTagId = ref(0);

// 编辑弹窗显示状态
const editDialogVisible = ref(false);
// 存储当前编辑的数据
const editForm = ref({
  title: '',
  category: '',
  generationMethod: '',
  inputText: '',
  remarks: '',
  selectedTagForAdd: [],
  uploadedFiles: [],
  uploadedFiles2: [],
  imageUrls: [],
  imageUrls2: []
});

// 处理编辑操作
const handleEdit = (index: number, row: any) => {
  // 将当前行的数据复制到编辑表单中
  editForm.value = {
    id: row.id,
    title: row.title,
    realtags: row.realtags,
    generationMethod: row.generation_method, // 假设接口返回的字段名是这个
    inputText: row.text,
    remarks: row.remarks,
    selectedTagForAdd: row.tag_id !== undefined && row.tag_id !== null ? [row.tag_id] : [], 
    uploadedFiles: [], // 这里可能需要根据实际情况处理文件，暂时置空
    uploadedFiles2: [],
    imageUrls: [],
    imageUrls2: []
  };
  console.log('编辑表单数据:', editForm.value);
  // 显示编辑弹窗
  editDialogVisible.value = true;
};
// 定义处理编辑时文件选择的方法
const handleEditFileChange = (files: any) => {
  const newFiles = Array.isArray(files.raw) ? files.raw : [files.raw];
  newFiles.forEach((file) => {
    const isDuplicate = editForm.value.uploadedFiles.some((existingFile) => existingFile.name === file.name && existingFile.size === file.size);
    if (!isDuplicate) {
      editForm.value.uploadedFiles.push(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        editForm.value.imageUrls.push(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  });
};

// 定义处理编辑时遮罩文件选择的方法
const handleEditFileChange2 = (files: any) => {
  const newFiles = Array.isArray(files.raw) ? files.raw : [files.raw];
  newFiles.forEach((file) => {
    const isDuplicate = editForm.value.uploadedFiles2.some((existingFile) => existingFile.name === file.name && existingFile.size === file.size);
    if (!isDuplicate) {
      editForm.value.uploadedFiles2.push(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        editForm.value.imageUrls2.push(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  });
}; 

// 定义转换日期格式的方法
const formatDate = (isoDate: string) => {
  const date = new Date(isoDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

// const loading = ref(true)
// const svg = `
//         <path class="path" d="
//           M 30 15
//           L 28 17
//           M 25.61 25.61
//           A 15 15, 0, 0, 1, 15 30
//           A 15 15, 0, 1, 1, 27.99 7.5
//           L 15 15
//         " style="stroke-width: 4px; fill: rgba(0, 0, 0, 0)"/>
//       `

// 提交编辑
const submitEdit = async () => {
  const formData = new FormData();
  // 添加多个文件
  editForm.value.uploadedFiles.forEach((file) => {
    formData.append('image', file);
  });
  editForm.value.uploadedFiles2.forEach((file) => {
    formData.append('mask', file);
  });
  formData.append('tag', editForm.value.selectedTagForAdd.join(','));
  // formData.append('generation_method', editForm.value.generationMethod);
  // formData.append('text', editForm.value.inputText);
  formData.append('title', editForm.value.title);
  formData.append('realtag', editForm.value.realtags.join(','));
  // formData.append('remarks', editForm.value.remarks);
  formData.append('id', editForm.value.id);

  try {
    // 假设存在一个 editExam 函数用于提交编辑数据
    const response = await editTemp(formData); 
    if (response.code === 200) {
      ElMessage.success('编辑成功');
      editDialogVisible.value = false;
      // 重新获取数据
      fetchData(selectedTagId.value);
    } else {
      ElMessage.error('编辑失败');
    }
  } catch (error) {
    console.error('编辑模板失败:', error);
    ElMessage.error('编辑失败，请稍后重试');
  }
};

onMounted(() => {
  fetchTags();
  fetchrealTags(); // 新增
  fetchData();
});
</script>

<template>
  <div class="example-view">
    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="请输入关键字"
        @input="handleSearch"
        style="width: 240px"
      />
    </div>






    <!-- 表格 -->
    <div>
      <el-table v-loading="loading"
    element-loading-text="Loading..."
    :element-loading-spinner="svg"
    element-loading-svg-view-box="-10, -10, 50, 50"
    element-loading-background="rgba(122, 122, 122, 0.8)"
     :data="paginatedData" style="width: 100%">
      <el-table-column prop="task_id" label="task_id" /> 
      <el-table-column prop="status" label="status" />
      <!-- <el-table-column prop="created_at" label="created_at" />
      <el-table-column prop="completed_at" label="completed_at" /> -->
      <!-- <el-table-column prop="title" label="标题" /> -->
      <!-- <el-table-column prop="text" label="文本" /> -->
      <!-- <el-table-column prop="category" label="用法分类" /> -->
      <el-table-column prop="task_type" label="task_type" />
      <!-- <el-table-column prop="created_date" label="上传时间" /> -->
      <el-table-column label="created_at">
        <template #default="scope">
          <span v-if="scope.row.created_at">{{ formatDate(scope.row.created_at) }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="completed_at">
        <template #default="scope">
          <span v-if="scope.row.completed_at">{{ formatDate(scope.row.completed_at) }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="input_data.description" label="description" />
      
      <el-table-column label="mask_url">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <img 
                :src="scope.row.input_data.mask_url" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="input">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <img 
                :src="scope.row.input_data.metadata.url" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="template_url">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <img 
                :src="scope.row.input_data.metadata.template_url" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="white_mask_url">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <img 
                :src="scope.row.input_data.metadata.white_mask_url" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="white_background_product_url">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <img 
                :src="scope.row.input_data.metadata.white_background_product_url" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="output_data">
        <template #default="scope">
          <!-- 添加一个容器并设置 flex 布局 -->
          <div v-if="scope.row.output_data && scope.row.output_data.image_urls" style="display: flex; flex-wrap: wrap; gap: 5px;">
            <div v-for="(path, index) in scope.row.output_data.image_urls" :key="index">
              <img 
                v-if="path"
                :src="path" 
                style="width: 50px; height: 50px; object-fit: cover;"
              />
            </div>
          </div>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="processing_time" label="processing_time" />
      
    </el-table>
    </div>

    <!-- 修改为表格形式 -->
<!--     
    <div class="fixed-pagination">
      <el-button 
        :disabled="currentPage <= 1" 
        @click="currentPage = 1; fetchData()"
      >
        首页
      </el-button>
      <el-button 
        :disabled="currentPage <= 1" 
        @click="currentPage--; fetchData()"
      >
        上一页
      </el-button>
      
      <el-button
        v-for="page in Math.ceil(total / pageSize)"
        :key="page"
        :type="currentPage === page ? 'primary' : ''"
        @click="currentPage = page; fetchData()"
      >
        {{ page }}
      </el-button>
      
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage++; fetchData()"
      >
        下一页
      </el-button>
      <el-button 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="currentPage = Math.ceil(total / pageSize); fetchData()"
      >
        末页
      </el-button>
    </div> -->
    <el-pagination
    :page-size="pageSize"
    layout="prev, pager, next"
    :total="total"
    v-model:current-page="currentPage"
    @change=fetchData
    @prev-click=fetchData
    @next-click=fetchData
    style="margin: 20px auto; display: flex; justify-content: center;"
      :small="false"
  />


  </div>
</template>

<style scoped lang="scss">
.example-card {
  margin-bottom: 200px;
  /* 确保卡片宽度一致 */
  width: 100%; 
  /* 可以根据需要设置卡片的最小高度 */
  min-height: 250px; 
}

.card-image {
  width: 100%;
  display: block;
  /* 可以根据需要设置图片的最大高度 */
  max-height: 200px; 
  object-fit: cover;
}

.search-box {
  margin-bottom: 10px;
  padding: 10px;
}

/* 新增按钮行样式 */
.tag-buttons {
  margin-bottom: 20px;
}

/* 添加新样式让分页组件居中 */
.center-pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px; /* 可以根据需要调整顶部间距 */
}

.fixed-pagination {
  position: fixed;
  bottom: 20px; /* 距离底部的距离，可根据需要调整 */
  left: 50%;
  transform: translateX(-50%); /* 水平居中 */
  z-index: 1000; /* 确保分页组件显示在其他元素之上 */
}
</style>
