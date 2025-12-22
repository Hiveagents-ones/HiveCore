<template>
  <div class="member-plans">
    <h2>会员等级管理</h2>
    
    <!-- 操作按钮区 -->
    <div class="action-bar">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        新增等级
      </el-button>
      <el-button @click="refreshPlans">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 会员等级表格 -->
    <el-table :data="plans" border style="width: 100%" v-loading="loading">
      <el-table-column prop="level" label="等级" width="100" />
      <el-table-column prop="name" label="等级名称" width="150" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="discount" label="折扣率" width="120">
        <template #default="scope">
          {{ scope.row.discount }}%
        </template>
      </el-table-column>
      <el-table-column prop="required_points" label="所需积分" width="120" />
      <el-table-column prop="benefits" label="权益" width="200">
        <template #default="scope">
          <el-tag v-for="benefit in scope.row.benefits" :key="benefit" size="small" class="benefit-tag">
            {{ benefit }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="editPlan(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deletePlan(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑会员等级' : '新增会员等级'"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="form.level" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="等级名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入等级名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="3" placeholder="请输入等级描述" />
        </el-form-item>
        <el-form-item label="折扣率" prop="discount">
          <el-input-number v-model="form.discount" :min="0" :max="100" :precision="1" />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="所需积分" prop="required_points">
          <el-input-number v-model="form.required_points" :min="0" />
        </el-form-item>
        <el-form-item label="权益" prop="benefits">
          <el-select
            v-model="form.benefits"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入权益"
          >
            <el-option
              v-for="item in benefitOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { getMemberPlans, createMemberPlan, updateMemberPlan, deleteMemberPlan } from '@/api/member'

// 数据
const plans = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

// 表单数据
const form = ref({
  level: 1,
  name: '',
  description: '',
  discount: 0,
  required_points: 0,
  benefits: []
})

// 表单验证规则
const rules = {
  level: [{ required: true, message: '请输入等级', trigger: 'blur' }],
  name: [{ required: true, message: '请输入等级名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
  discount: [{ required: true, message: '请输入折扣率', trigger: 'blur' }],
  required_points: [{ required: true, message: '请输入所需积分', trigger: 'blur' }],
  benefits: [{ required: true, message: '请选择权益', trigger: 'change' }]
}

// 权益选项
const benefitOptions = [
  '生日特权',
  '专属客服',
  '优先预订',
  '免费配送',
  '积分翻倍',
  '专属活动',
  '升级礼包'
]

// 获取会员等级列表
const fetchPlans = async () => {
  loading.value = true
  try {
    const response = await getMemberPlans()
    plans.value = response.data
  } catch (error) {
    ElMessage.error('获取会员等级列表失败')
  } finally {
    loading.value = false
  }
}

// 刷新列表
const refreshPlans = () => {
  fetchPlans()
}

// 显示新增对话框
const showAddDialog = () => {
  isEdit.value = false
  form.value = {
    level: 1,
    name: '',
    description: '',
    discount: 0,
    required_points: 0,
    benefits: []
  }
  dialogVisible.value = true
}

// 编辑会员等级
const editPlan = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

// 删除会员等级
const deletePlan = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除会员等级 "${row.name}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deleteMemberPlan(row.id)
    ElMessage.success('删除成功')
    fetchPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await updateMemberPlan(form.value.id, form.value)
          ElMessage.success('更新成功')
        } else {
          await createMemberPlan(form.value)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchPlans()
      } catch (error) {
        ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
      }
    }
  })
}

// 初始化
onMounted(() => {
  fetchPlans()
})
</script>

<style scoped>
.member-plans {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.benefit-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.unit {
  margin-left: 10px;
  color: #909399;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>