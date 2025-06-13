<template>
    <div>
      <el-table :data="assetsData" style="width: 100%">



      </el-table>
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
      />
      <div  >
        <!-- 新增标签按钮 -->
        <el-button type="primary" @click="showAddTagDialog = true">新增种类</el-button>
        <el-button style="margin-left: 1230px;" type="primary" @click="showAddTagDialog1 = true">新增标签</el-button>

      </div>

      <!-- 新增标签弹窗 -->
      <el-dialog v-model="showAddTagDialog" title="新增标签" style="width: 50%;">
        <el-form :model="newTagForm" label-width="100px">
          <el-form-item label="描述">
            <el-input v-model="newTagForm.description"></el-input>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showAddTagDialog = false">取消</el-button>
            <el-button type="primary" @click="submitNewTag">确定</el-button>
          </span>
        </template>
      </el-dialog>
      


      <!-- 新增标签弹窗 -->
      <el-dialog v-model="showAddTagDialog1" title="新增标签" style="width: 50%;">
        <el-form :model="newTagForm1" label-width="100px">
          <el-form-item label="描述">
            <el-input v-model="newTagForm1.name"></el-input>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showAddTagDialog1 = false">取消</el-button>
            <el-button type="primary" @click="submitNewTag1">确定</el-button>
          </span>
        </template>
      </el-dialog>

      <div  class="table-container">

      <!-- 渲染标签表格 -->
      <el-table :data="tagData" style="width: 45%; margin-top: 20px;">
        <el-table-column prop="id" label="ID" />

        <el-table-column prop="name" label="标签名称">
          <template #default="{ row }">
            <el-input
              v-if="editingTagIndex === row.id"
              v-model="row.description"
              @blur="submitTagEdit(row)"
            />
            <span v-else @dblclick="startTagEdit(row)">{{ row.description }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Operations">
          <template #default="scope">
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

      <el-table :data="realtagData" style="width: 45%; margin-top: 20px;">
        <el-table-column prop="id" label="ID" />

        <el-table-column prop="name" label="标签名称">
          <template #default="{ row }">
            <el-input
              v-if="editingTagIndex1 === row.id"
              v-model="row.name"
              @blur="submitTagEdit1(row)"
            />
            <span v-else @dblclick="startTagEdit1(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Operations">
          <template #default="scope">
            <el-button
              size="small"
              type="danger"
              @click="handleDeletereal(scope.$index, scope.row)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      </div>


    </div>
  </template>
  
  <script setup lang="ts">
  import { ref } from 'vue';
  import { getassets, updatesssets } from '@/api/userApi';
  import { gettag, edittag, addTag,getrealtag ,editrealtag,addrealTag,delrealtag,deltag} from '@/api/templateApi'; // 导入 templateApi 相关方法
  
  const assetsData = ref([]);
  const errorMessage = ref('');
  const editingIndex = ref(-1);
  const tagData = ref([]); // 存储标签数据
  const realtagData = ref([]); // 存储标签数据
  const editingTagIndex = ref(-1); // 记录正在编辑的标签索引
  const editingTagIndex1 = ref(-1); // 记录正在编辑的标签索引
  const showAddTagDialog = ref(false);
  const showAddTagDialog1 = ref(false);
  const newTagForm = ref({
    description: ''
  });
  const newTagForm1 = ref({
    name: ''
  });
  // 定义 handleDelete 方法
const handleDelete = async (index: number, row: any) => {
  try {

        // 调用 delexam 函数，假设 row 中有对应的 tagid
    await deltag(row.id); // 这里假设 id 是需要传递的 tagid，根据实际情况修改
    ElMessage.success('删除成功');
    // 重新获取数据以更新列表
    // 获取标签数据
    const tagResult = await gettag();
      if (tagResult.code === 200) {
        tagData.value = tagResult.data;
      } else {
        errorMessage.value = tagResult.message || '获取标签数据失败';
      }
  } catch (error) {
    console.error('删除失败', error);
    ElMessage.error('删除失败');
  }
};
// 定义 handleDelete 方法
const handleDeletereal = async (index: number, row: any) => {
  try {

        // 调用 delexam 函数，假设 row 中有对应的 tagid
    await delrealtag(row.id); // 这里假设 id 是需要传递的 tagid，根据实际情况修改
    ElMessage.success('删除成功');
    // 重新获取数据以更新列表
    // 获取标签数据
    
      const tagResult2 = await getrealtag(1);
      if (tagResult2.code === 200) {
        realtagData.value = tagResult2.data;
      } else {
        errorMessage.value = tagResult2.message || '获取标签数据失败';
      }
  } catch (error) {
    console.error('删除失败', error);
    ElMessage.error('删除失败');
  }
};
  onMounted(async () => {
    try {
      const result = await getassets();
      if (result.code === 200) {
        assetsData.value = result.data;
      } else {
        errorMessage.value = result.message || '获取数据失败';
      }
      // 获取标签数据
      const tagResult = await gettag();
      if (tagResult.code === 200) {
        tagData.value = tagResult.data;
      } else {
        errorMessage.value = tagResult.message || '获取标签数据失败';
      }
      const tagResult2 = await getrealtag(1);
      if (tagResult2.code === 200) {
        realtagData.value = tagResult2.data;
      } else {
        errorMessage.value = tagResult2.message || '获取标签数据失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '获取数据时发生未知错误';
      }
    }
  });

  const handleEdit = (row) => {
    editingIndex.value = row.id;
  };

  const handleBlur = async (row) => {
    try {
      await updatesssets(row);
      editingIndex.value = -1;
      // 重新获取数据以更新页面
      const result = await getassets();
      if (result.code === 200) {
        assetsData.value = result.data;
      } else {
        errorMessage.value = result.message || '更新后重新获取数据失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '更新数据时发生未知错误';
      }
    }
  };

  // 开始编辑标签
  const startTagEdit = (row) => {
    editingTagIndex.value = row.id;
  };

  // 开始编辑标签
  const startTagEdit1 = (row) => {
    editingTagIndex1.value = row.id;
  };

  // 提交标签编辑
  const submitTagEdit = async (row) => {
    try {
      await edittag(row);
      editingTagIndex.value = -1;
      // 重新获取标签数据以更新页面
      const tagResult = await gettag();
      if (tagResult.code === 200) {
        tagData.value = tagResult.data;
      } else {
        errorMessage.value = tagResult.message || '更新标签数据失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '更新标签数据时发生未知错误';
      }
    }
  };
    // 提交标签编辑
    const submitTagEdit1 = async (row) => {
    try {
      await editrealtag(row);
      editingTagIndex1.value = -1;
      // 重新获取标签数据以更新页面
      const tagResult = await getrealtag(1);
      if (tagResult.code === 200) {
        realtagData.value = tagResult.data;
      } else {
        errorMessage.value = tagResult.message || '更新标签数据失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '更新标签数据时发生未知错误';
      }
    }
  };

  // 提交新增标签
  const submitNewTag = async () => {
    try {
      const newTagResult = await addTag({ description: newTagForm.value.description,temp:0 });
      if (newTagResult.code === 200) {
        // 重新获取标签数据以更新页面
        const tagResult = await gettag();
        if (tagResult.code === 200) {
          tagData.value = tagResult.data;
        } else {
          errorMessage.value = tagResult.message || '更新标签数据失败';
        }
        showAddTagDialog.value = false;
        newTagForm.value.description = '';
      } else {
        errorMessage.value = newTagResult.message || '新增标签失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '新增标签时发生未知错误';
      }
    }
  };
 // 提交新增标签
 const submitNewTag1 = async () => {
    try {
      const newTagResult = await addrealTag({ name: newTagForm1.value.name,temp:1 });
      if (newTagResult.code === 200) {
        // 重新获取标签数据以更新页面
        const tagResult = await getrealtag(1);
        if (tagResult.code === 200) {
          realtagData.value = tagResult.data;
        } else {
          errorMessage.value = tagResult.message || '更新标签数据失败';
        }
        showAddTagDialog1.value = false;
        newTagForm1.value.name = '';
      } else {
        errorMessage.value = newTagResult.message || '新增标签失败';
      }
    } catch (error) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = '新增标签时发生未知错误';
      }
    }
  };

  </script>


<style scoped lang="scss">
.table-container {
  display: flex;
  justify-content: space-between; /* 让两个表格之间有间距 */
  align-items: flex-start; /* 表格顶部对齐 */
}
</style>