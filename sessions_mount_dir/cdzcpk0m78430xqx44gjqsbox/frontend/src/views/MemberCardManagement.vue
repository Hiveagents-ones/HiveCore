<template>
  <div class="member-card-management">
    <h1>会员卡类型管理</h1>
    <el-alert
      title="会员卡类型管理说明"
      type="info"
      description="在此页面可以管理所有会员卡类型，包括添加、编辑和删除操作。会员卡类型将用于会员购买和自动扣费。"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />
    
    <div class="action-bar">
      <el-button type="primary" @click="showAddDialog">添加会员卡类型</el-button>
    </div>
    
    <el-table :data="cardTypes" border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80"></el-table-column>
      <el-table-column prop="name" label="卡类型名称"></el-table-column>
      <el-table-column prop="price" label="价格" width="120"></el-table-column>
      <el-table-column prop="duration" label="有效期(天)" width="120"></el-table-column>
      <el-table-column prop="description" label="描述"></el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="50%">
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="卡类型名称" required>
          <el-input v-model="form.name" placeholder="请输入卡类型名称"></el-input>
        </el-form-item>
        <el-form-item label="价格" required>
          <el-input-number v-model="form.price" :min="0" :precision="2"></el-input-number>
        </el-form-item>
        <el-form-item label="有效期(天)" required>
          <el-input-number v-model="form.duration" :min="1"></el-input-number>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCardTypes, addCardType, updateCardType, deleteCardType } from '../api/payments.js'

export default {
  name: 'MemberCardManagement',
  setup() {
    const cardTypes = ref([])
    const dialogVisible = ref(false)
    const dialogTitle = ref('')
    const form = ref({
      id: null,
      name: '',
      price: 0,
      duration: 30,
      description: ''
    })
    const isEditMode = ref(false)
    const formRef = ref(null)
    
    const rules = {
      name: [
        { required: true, message: '请输入卡类型名称', trigger: 'blur' },
        { min: 2, max: 20, message: '长度在2到20个字符', trigger: 'blur' }
      ],
      price: [
        { required: true, message: '请输入价格', trigger: 'blur' },
        { type: 'number', min: 0, message: '价格必须大于0', trigger: 'blur' }
      ],
      duration: [
        { required: true, message: '请输入有效期', trigger: 'blur' },
        { type: 'number', min: 1, message: '有效期必须大于0天', trigger: 'blur' }
      ]
    }

    const fetchCardTypes = async () => {
      try {
        const response = await getCardTypes()
        cardTypes.value = response.data
      } catch (error) {
        if (!error) return
        ElMessage.error('获取会员卡类型失败: ' + error.message)
      }
    }

    const showAddDialog = () => {
      resetForm()
      dialogTitle.value = '添加会员卡类型'
      isEditMode.value = false
      dialogVisible.value = true
    }

    const handleEdit = (row) => {
      form.value = { ...row }
      dialogTitle.value = '编辑会员卡类型'
      isEditMode.value = true
      dialogVisible.value = true
    }

    const handleDelete = (row) => {
      ElMessageBox.confirm('确定要删除该会员卡类型吗?', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await deleteCardType(row.id)
          ElMessage.success('删除成功')
          fetchCardTypes()
        } catch (error) {
          ElMessage.error('删除失败: ' + error.message)
        }
      }).catch(() => {})
    }

    const submitForm = async () => {
      try {
        await formRef.value.validate()
      try {
        if (isEditMode.value) {
          await updateCardType(form.value)
          ElMessage.success('更新成功')
        } else {
          await addCardType(form.value)
          ElMessage.success('添加成功')
        }
        dialogVisible.value = false
        fetchCardTypes()
      } catch (error) {
        ElMessage.error('操作失败: ' + error.message)
      }
    }

    const resetForm = () => {
      form.value = {
        id: null,
        name: '',
        price: 0,
        duration: 30,
        description: ''
      }
    }

    onMounted(() => {
      fetchCardTypes()
    })

    return {
      cardTypes,
      dialogVisible,
      dialogTitle,
      form,
      showAddDialog,
      handleEdit,
      handleDelete,
      submitForm
    }
  }
}
</script>

<style scoped>
.member-card-management {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.el-table {
  margin-top: 20px;
}

.el-input-number {
  width: 100%;
}
}
</style>