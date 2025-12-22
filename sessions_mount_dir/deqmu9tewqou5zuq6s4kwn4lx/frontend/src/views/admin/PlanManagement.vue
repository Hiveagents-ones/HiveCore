<template>
  <div class="plan-management">
    <el-card class="page-header">
      <template #header>
        <div class="card-header">
          <span>套餐管理</span>
          <el-button type="primary" @click="handleAdd">新增套餐</el-button>
        </div>
      </template>
    </el-card>

    <el-card class="table-container">
      <el-table :data="plans" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="套餐名称" />
        <el-table-column prop="duration" label="时长">
          <template #default="{ row }">
            {{ row.duration }}{{ row.duration_unit }}
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格">
          <template #default="{ row }">
            ¥{{ row.price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button 
              size="small" 
              :type="row.is_active ? 'warning' : 'success'"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog 
      :title="dialogTitle" 
      v-model="dialogVisible" 
      width="500px"
      @close="resetForm"
    >
      <el-form 
        ref="formRef" 
        :model="form" 
        :rules="rules" 
        label-width="100px"
      >
        <el-form-item label="套餐名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入套餐名称" />
        </el-form-item>
        <el-form-item label="时长" prop="duration">
          <el-input-number 
            v-model="form.duration" 
            :min="1" 
            :max="999"
            style="width: 150px"
          />
          <el-select v-model="form.duration_unit" style="width: 100px; margin-left: 10px">
            <el-option label="月" value="月" />
            <el-option label="季" value="季" />
            <el-option label="年" value="年" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number 
            v-model="form.price" 
            :min="0" 
            :precision="2"
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入套餐描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPlans, createPlan, updatePlan, deletePlan } from '@/api/plan'

// 数据
const loading = ref(false)
const submitting = ref(false)
const plans = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref(null)

// 表单数据
const form = ref({
  id: null,
  name: '',
  duration: 1,
  duration_unit: '月',
  price: 0,
  description: '',
  is_active: true
})

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入套餐名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  duration: [
    { required: true, message: '请输入时长', trigger: 'blur' },
    { type: 'number', min: 1, message: '时长必须大于0', trigger: 'blur' }
  ],
  duration_unit: [
    { required: true, message: '请选择时长单位', trigger: 'change' }
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', min: 0, message: '价格不能小于0', trigger: 'blur' }
  ],
  description: [
    { max: 200, message: '描述不能超过200个字符', trigger: 'blur' }
  ]
}

// 获取套餐列表
const fetchPlans = async () => {
  loading.value = true
  try {
    const response = await getPlans()
    plans.value = response.data
  } catch (error) {
    ElMessage.error('获取套餐列表失败')
  } finally {
    loading.value = false
  }
}

// 重置表单
const resetForm = () => {
  form.value = {
    id: null,
    name: '',
    duration: 1,
    duration_unit: '月',
    price: 0,
    description: '',
    is_active: true
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// 新增套餐
const handleAdd = () => {
  dialogTitle.value = '新增套餐'
  dialogVisible.value = true
  resetForm()
}

// 编辑套餐
const handleEdit = (row) => {
  dialogTitle.value = '编辑套餐'
  dialogVisible.value = true
  form.value = { ...row }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    if (form.value.id) {
      await updatePlan(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createPlan(form.value)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    fetchPlans()
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('操作失败')
    }
  } finally {
    submitting.value = false
  }
}

// 切换状态
const handleToggleStatus = async (row) => {
  try {
    await updatePlan(row.id, { ...row, is_active: !row.is_active })
    ElMessage.success(`${row.is_active ? '禁用' : '启用'}成功`)
    fetchPlans()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 删除套餐
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除套餐 "${row.name}" 吗？此操作不可恢复。`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deletePlan(row.id)
      ElMessage.success('删除成功')
      fetchPlans()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 初始化
onMounted(() => {
  fetchPlans()
})
</script>

<style scoped>
.plan-management {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-container {
  min-height: 400px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>