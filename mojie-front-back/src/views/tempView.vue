<template>
  <!-- 添加搜索框 -->
  <!-- 
  <div class="search-box">
    <el-input
      v-model="searchQuery"
      placeholder="请输入关键字"
      @input="handleSearch"
      style="width: 240px"
    />
  </div> 
  -->
  <!-- 新增按钮行 -->
  <div class="tag-buttons">
    <el-button type="primary" @click="dialogVisible = true">新增</el-button>
    <span style="font-size: 30px; margin-left: 20px">分类：</span>
    <el-radio-group v-model="selectedTagId">
      <el-radio-button :key="0" :label="0" @click="handleTagClick(0)">
        全部
      </el-radio-button>
      <el-radio-button
        v-for="tag in tagList"
        :key="tag.id"
        :label="tag.id"
        @click="handleTagClick(tag.id)"
      >
        {{ tag.description }}
      </el-radio-button>
    </el-radio-group>
  </div>
  <div class="example-view">
    <el-row :gutter="20">
      <el-col :span="3" v-for="item in paginatedData" :key="item.id">
        <el-card class="example-card">
          <img :src="item.image_path" class="card-image" />
          <!-- 添加内联样式实现文字居中 -->
          <!-- 
          <div style="padding: 14px; text-align: center;"> 
            <span>{{ item.text }}</span>
          </div> 
          -->
        </el-card>
      </el-col>
    </el-row>
    <!-- 将分页组件移到卡片列表之后，添加类名 -->
    <el-pagination
      class="center-pagination"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="handlePageChange"
      layout="prev, pager, next"
    />
  </div>

  <!-- 新增弹窗 -->
  <el-dialog v-model="dialogVisible" title="新增模板">
    <el-form>
      <!-- 新增：图片文件提示 -->
      <div class="input-row">
        <span>图片文件：</span>
        <el-upload
          action="#"
          :show-file-list="false"
          @change="handleFileChange"
        >
          <el-button type="primary">选择图片</el-button>
        </el-upload>
      </div>
      <!-- 新增：显示图片 -->
      <div class="square-image-container">
        <img v-if="imageUrl" :src="imageUrl" alt="Selected Image" />
      </div>
      
      <!-- 
      <el-form-item label="上传图片">
        <el-upload
          action="#"
          :show-file-list="false"
          :on-success="handleUploadSuccess"
          :before-upload="beforeUpload"
        >
          <el-button type="primary">点击上传</el-button>
        </el-upload> 
        新增图片展示区域 -->
        <!-- 
        <img v-if="uploadedImageUrl" :src="uploadedImageUrl" class="preview-image" />
      </el-form-item> 
      -->
      <el-form-item label="选择标签">
        <el-select v-model="selectedTagForAdd" placeholder="请选择标签">
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
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">确定</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ref, onMounted, computed, onActivated, watch, onRouteUpdate } from 'vue';
  import { gettemplates, gettag, addTemp } from '@/api/templateApi';
  import { useRoute } from 'vue-router';
  import { ElMessage } from 'element-plus';

  const route = useRoute();
  // 当前页码
  const currentPage = ref(1);
  // 每页显示的数量
  const pageSize = ref(10);
  // 数据总数
  const total = ref(0);
  // 所有数据
  const allData = ref([]);
  // 搜索关键词
  const searchQuery = ref(''); 
  // 标签列表
  const tagList = ref([]);
  // 选中的标签 id
  const selectedTagId = ref(0);
  // 弹窗显示状态
  const dialogVisible = ref(false);
  // 上传的图片文件
  const uploadedFile = ref<File | null>(null);
  const imageUrl = ref<string | null>(null);
  // 新增时选择的标签
  const selectedTagForAdd = ref(0);

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
  // 新增：处理文件选择事件
    const handleFileChange = (file: any) => {
        uploadedFile.value = file.raw;
    if (uploadedFile.value) {
        const reader = new FileReader();
        reader.onload = (e) => {
        imageUrl.value = e.target?.result as string;
        };
        reader.readAsDataURL(uploadedFile.value);
    }
    };

  // 获取数据
  const fetchData = async (tagId = null) => {
    try {
      const response = await gettemplates(tagId);
      console.log('API 响应:', response); // 打印响应内容，方便调试
      if (Array.isArray(response.data)) {
        allData.value = response.data;
        total.value = response.data.length;
      } else {
        console.error('API 响应不是数组:', response);
        allData.value = [];
        total.value = 0;
      }
    } catch (error) {
      console.error('获取示例数据失败:', error);
    }
  };

  // 处理分页变化
  const handlePageChange = (page: number) => {
    currentPage.value = page;
  };

  // 处理搜索输入
  const handleSearch = () => {
    currentPage.value = 1; // 搜索时重置页码
  };

  // 处理标签点击事件
  const handleTagClick = (tagId: number) => {
    currentPage.value = 1;
    fetchData(tagId);
  };

  // 计算过滤后的数据
  const filteredData = computed(() => {
    if (!searchQuery.value) return allData.value;
    return allData.value.filter((item) => 
      item.text && item.text.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
  });

  // 计算当前页的数据，基于过滤后的数据
  const paginatedData = computed(() => {
    if (Array.isArray(filteredData.value)) {
      const start = (currentPage.value - 1) * pageSize.value;
      const end = start + pageSize.value;
      return filteredData.value.slice(start, end);
    } else {
      console.error('filteredData 不是数组，无法进行分页');
      return [];
    }
  });

  // 更新总数为过滤后的数据数量
  // 这里原代码有错误，不能直接给 ref 赋值 computed，应改为如下方式
  total.value = filteredData.value.length;
  const totalComputed = computed(() => filteredData.value.length);
  total.value = totalComputed.value;

  // 新增响应式变量，用于存储图片的 URL
  const uploadedImageUrl = ref<string | null>(null);

  // 处理图片上传成功
  const handleUploadSuccess = (response, file) => {
    uploadedFile.value = file.raw;
    // 创建图片的临时 URL
    uploadedImageUrl.value = URL.createObjectURL(file.raw);
  };

  // 上传前的钩子
  const beforeUpload = (file) => {
    const isImage = /^image\//.test(file.type);
    if (!isImage) {
      ElMessage.error('只能上传图片文件!');
    }
    return isImage;
  };

  // 提交新增
  const submitAdd = async () => {
    if (!uploadedFile.value || !selectedTagForAdd.value) {
      ElMessage.error('请上传图片并选择标签');
      return;
    }
    const formData = new FormData();
    formData.append('image', uploadedFile.value);
    formData.append('tag', selectedTagForAdd.value.toString());

    try {
      const response = await addTemp(formData);
      if (response.code === 200) {
        ElMessage.success('添加成功');
        dialogVisible.value = false;
        // 释放图片的临时 URL
        if (uploadedImageUrl.value) {
          URL.revokeObjectURL(uploadedImageUrl.value);
          uploadedImageUrl.value = null;
        }
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

  onMounted(() => {
    fetchTags();
    fetchData(0);
  });
//   onRouteUpdate(() => {
//     fetchTags();
//     fetchData(0);
// });

  // watch(() => route.path, fetchTags);
  // watch(() => route.path, () => {
  //   fetchData(0);
  // });

  // onActivated(() => {
  //   fetchTags();
  //   fetchData(0);
  // });
</script>

<style scoped>
  .example-card {
    margin-bottom: 200px;
    /* // 确保卡片宽度一致 */
    width: 100%; 
    /* // 可以根据需要设置卡片的最小高度 */
    min-height: 250px; 
  }

  .card-image {
    width: 100%;
    display: block;
    /* // 可以根据需要设置图片的最大高度 */
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
    margin-top: 20px; /* 可根据需要调整顶部间距 */
  }

  /* 新增图片预览样式 */
  .preview-image {
    max-width: 100%;
    max-height: 200px;
    margin-top: 10px;
    display: block;
  }
</style>