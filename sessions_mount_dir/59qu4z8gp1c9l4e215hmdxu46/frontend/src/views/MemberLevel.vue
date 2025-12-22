<template>
  <div class="member-level-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>会员等级管理</span>
          <el-button type="primary" @click="handleAddLevel">添加等级</el-button>
        </div>
      </template>

      <el-table :data="levelData" border style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="等级名称" />
        <el-table-column prop="discount" label="折扣率">
          <template #default="scope">
            {{ (scope.row.discount * 100).toFixed(0) }}%
          </template>
        </el-table-column>
        <el-table-column prop="min_points" label="最低积分" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="等级权益">
          <template #default="scope">
            {{ calculateLevelBenefits(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="30%">
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="等级名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入等级名称" />
        </el-form-item>
        <el-form-item label="折扣率" prop="discount">
          <el-input-number v-model="formData.discount" :min="0.1" :max="1" :step="0.1" :precision="1" />
        </el-form-item>
        <el-form-item label="最低积分" prop="min_points">
          <el-input-number v-model="formData.min_points" :min="0" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" type="textarea" :rows="2" placeholder="请输入等级描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确认</el-button>
      calculateLevelBenefits,
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMemberLevel, updateMemberLevel } from '@/api/members'
import { calculateLevelBenefits } from '@/utils/memberLevelCalculator'

export default {
  name: 'MemberLevel',
  setup() {
    const levelData = ref([])
    const loading = ref(false)
    const dialogVisible = ref(false)
    const dialogTitle = ref('')
    const formData = ref({
      id: null,
      name: '',
      discount: 1,
      min_points: 0,
      description: ''
    })
    const formRef = ref(null)
    const currentAction = ref('add')

    const rules = {
    const calculateLevelBenefits = (level) => {
      return `消费享受${(level.discount * 100).toFixed(0)}%折扣，积分满${level.min_points}可升级`
    }
      name: [{ required: true, message: '请输入等级名称', trigger: 'blur' }],
      discount: [{ required: true, message: '请设置折扣率', trigger: 'blur' }],
      min_points: [{ required: true, message: '请设置最低积分', trigger: 'blur' }]
    }

    const fetchLevelData = async () => {
      try {
        loading.value = true
        const response = await getMemberLevel()
        levelData.value = response.data
      } catch (error) {
        ElMessage.error('获取会员等级数据失败')
      } finally {
        loading.value = false
      }
    }

    const handleAddLevel = () => {
      currentAction.value = 'add'
      dialogTitle.value = '添加会员等级'
      formData.value = {
        id: null,
        name: '',
        discount: 1,
        min_points: 0,
        description: ''
      }
      dialogVisible.value = true
    }

    const handleEdit = (row) => {
      currentAction.value = 'edit'
      dialogTitle.value = '编辑会员等级'
      formData.value = { ...row }
      dialogVisible.value = true
    }

    const handleDelete = (row) => {
      ElMessageBox.confirm('确定要删除该会员等级吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await updateMemberLevel(row.id, { is_active: false })
          ElMessage.success('删除成功')
          fetchLevelData()
        } catch (error) {
          ElMessage.error('删除失败')
        }
      }).catch(() => {})
    }

    const submitForm = async () => {
      try {
        await formRef.value.validate()
        
        if (currentAction.value === 'add') {
          await updateMemberLevel(null, formData.value)
          ElMessage.success('添加成功')
        } else {
          await updateMemberLevel(formData.value.id, formData.value)
          ElMessage.success('更新成功')
        }
        
        dialogVisible.value = false
        fetchLevelData()
      } catch (error) {
        console.error('表单提交失败:', error)
      }
    }

    onMounted(() => {
      fetchLevelData()
    })

    return {
      levelData,
      loading,
      dialogVisible,
      dialogTitle,
      formData,
      formRef,
      rules,
      handleAddLevel,
      handleEdit,
      handleDelete,
      submitForm
    }
  }
}
</script>

<style scoped>
.member-level-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-table {
  margin-top: 20px;
}
</style>