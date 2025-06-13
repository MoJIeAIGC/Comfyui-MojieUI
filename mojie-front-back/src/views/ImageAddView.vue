<template>
  <div class="grid">
    <div class="table">
      <h2>新增图片</h2>
      <form @submit.prevent="submitForm">
        <!-- 新增：图片描述提示 -->
        <div class="input-row">
          <span>图片描述：</span>
          <el-input v-model="description" placeholder="图片描述"></el-input>
        </div>
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
          <img v-if="imageUrl" :src="imageUrl" alt="Selected Image">
        </div>
        <!-- 新增：图片类别提示 -->
        <div class="input-row">
          <span>图片类别：</span>
          <el-select v-model="method" placeholder="请选择图片分类">
            <el-option
              v-for="category in categories"
              :key="category.value"
              :label="category.label"
              :value="category.value"
            ></el-option>
          </el-select>
        </div>
        <!-- 新增：图片细分提示 -->
        <div class="input-row">
          <span>图片细分：</span>
          <el-select v-model="method_su" placeholder="请选择图片分类">
            <el-option
              v-for="category in categories_su"
              :key="category.value"
              :label="category.label"
              :value="category.value"
            ></el-option>
          </el-select>
        </div>
        <!-- 新增：用户ID提示 -->
        <div class="input-row">
          <span>用户ID：</span>
          <el-input v-model="userId" placeholder="用户ID"></el-input>
        </div>
        <!-- 新增：对应图片ID提示 -->
        <div class="input-row">
          <span>对应图片ID：</span>
          <el-input v-model="related_id" placeholder="对应图片ID"></el-input>
        </div>
        <el-button type="primary" native-type="submit">提交</el-button>
        <el-button @click="cancel">取消</el-button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { uploadImage } from '@/api/imageApi';
import { useRouter } from 'vue-router';

// 定义表单数据
const description = ref('');
const image = ref<File | null>(null);
const imageUrl = ref<string | null>(null);
const method = ref('');
const method_su = ref('');
const userId = ref('');
const related_id = ref('');

// 新增：图片分类选项
const categories = ref([
  { label: 'clue_product', value: 'clue_product' },
  { label: 'product', value: 'product' },
  { label: 'mask', value: 'mask' }
]);
// 新增：图片分类选项
const categories_su = ref([
  { label: 'chairs', value: 'chairs' },
  { label: 'car', value: 'car' },
  { label: 'bag', value: 'bag' },
  { label: 'vacuum', value: 'vacuum' },
]);

// 处理表单提交
const submitForm = async () => {
  const formData = new FormData();
  formData.append('description', description.value);
  if (image.value) {
    formData.append('image', image.value);
  }
  formData.append('method', method.value);
  formData.append('subCategory', method_su.value);
  formData.append('user_id', userId.value);
  formData.append('related_id', related_id.value);

  try {
    const response = await uploadImage(formData);
    if (response.code === 200) {
      ElMessage.success('添加成功');
      // 清空表单数据
      description.value = '';
      image.value = null;
      imageUrl.value = null;
      method.value = '';
      method_su.value = '';
      userId.value = '';
      related_id.value = '';
    } else {
      ElMessage.error('添加失败');
    }
  } catch (error) {
    ElMessage.error('添加失败');
  }
};

// 新增：处理文件选择事件
const handleFileChange = (file: any) => {
  image.value = file.raw;
  if (image.value) {
    const reader = new FileReader();
    reader.onload = (e) => {
      imageUrl.value = e.target?.result as string;
    };
    reader.readAsDataURL(image.value);
  }
};

const router = useRouter();

const cancel = () => {
  router.push('/image/list');
};
</script>

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

.input-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.input-row span {
  margin-right: 10px;
  min-width: 80px; /* 确保提示词有足够的宽度 */
}

.square-image-container {
  width: 100px; /* 设置正方形的宽度 */
  height: 100px; /* 设置正方形的高度 */
  margin-top: 10px;
  border: 1px solid #ccc; /* 可选：添加边框 */
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden; /* 隐藏超出容器的部分 */
}

.square-image-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover; /* 填充整个容器 */
}
</style>