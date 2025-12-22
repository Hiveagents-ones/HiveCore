<template>
  <div class="member-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>会员列表</span>
          <el-button type="primary" @click="handleAdd">新增会员</el-button>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-area">
        <el-form :inline="true" :model="searchForm" class="search-form">
          <el-form-item label="姓名">
            <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable />
          </el-form-item>
          <el-form-item label="会员卡号">
            <el-input v-model="searchForm.card_number" placeholder="请输入会员卡号" clearable />
          </el-form-item>
          <el-form-item label="会员等级">
            <el-select v-model="searchForm.level" placeholder="请选择会员等级" clearable>
              <el-option label="普通会员" value="normal" />
              <el-option label="银卡会员" value="silver" />
              <el-option label="金卡会员" value="gold" />
              <el-option label="钻石会员" value="diamond" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 操作区域 -->
      <div class="operation-area">
        <el-button type="success" @click="handleExport">导出数据</el-button>
      </div>

      <!-- 表格区域 -->
      <el-table :data="tableData" border style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="联系方式" width="150" />
        <el-table-column prop="card_number" label="会员卡号" width="180" />
        <el-table-column prop="level" label="会员等级" width="120">
          <template #default="scope">
            <el-tag :type="getLevelType(scope.row.level)">{{ getLevelText(scope.row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remaining_classes" label="剩余课时" width="100" />
        <el-table-column prop="valid_until" label="有效期至" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.valid_until) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="handleView(scope.row)">查看</el-button>
            <el-button link type="primary" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页区域 -->
      <div class="pagination-area">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 会员表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="联系方式" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入联系方式" />
        </el-form-item>
        <el-form-item label="会员卡号" prop="card_number">
          <el-input v-model="formData.card_number" placeholder="请输入会员卡号" />
        </el-form-item>
        <el-form-item label="会员等级" prop="level">
          <el-select v-model="formData.level" placeholder="请选择会员等级">
            <el-option label="普通会员" value="normal" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>
        <el-form-item label="剩余课时" prop="remaining_classes">
          <el-input-number v-model="formData.remaining_classes" :min="0" />
        </el-form-item>
        <el-form-item label="有效期至" prop="valid_until">
          <el-date-picker
            v-model="formData.valid_until"
            type="date"
            placeholder="选择有效期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getMemberList,
  createMember,
  updateMember,
  deleteMember
} from '@/api/member'

// 响应式数据
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增会员')
const formRef = ref(null)

// 搜索表单
const searchForm = reactive({
  name: '',
  card_number: '',
  level: ''
})

// 表格数据
const tableData = ref([])

// 分页数据
const pagination = reactive({
  current: 1,
  size: 10,
  total: 0
})

// 表单数据
const formData = reactive({
  id: null,
  name: '',
  phone: '',
  card_number: '',
  level: 'normal',
  remaining_classes: 0,
  valid_until: ''
})

// 表单验证规则
const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
  card_number: [{ required: true, message: '请输入会员卡号', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
  valid_until: [{ required: true, message: '请选择有效期', trigger: 'change' }]
}

// 获取会员列表
const fetchMemberList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      size: pagination.size,
      ...searchForm
    }
    const response = await getMemberList(params)
    tableData.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error('获取会员列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  fetchMemberList()
}

// 重置
const handleReset = () => {
  Object.assign(searchForm, {
    name: '',
    card_number: '',
    level: ''
  })
  handleSearch()
}

// 导出
const handleExport = () => {
  ElMessage.success('导出功能开发中...')
}

// 新增
const handleAdd = () => {
  dialogTitle.value = '新增会员'
  dialogVisible.value = true
  resetForm()
}

// 查看
const handleView = (row) => {
  ElMessage.info('查看功能开发中...')
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑会员'
  dialogVisible.value = true
  Object.assign(formData, row)
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该会员吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      try {
        await deleteMember(row.id)
        ElMessage.success('删除成功')
        fetchMemberList()
      } catch (error) {
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {
      ElMessage.info('已取消删除')
    })
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (formData.id) {
          await updateMember(formData.id, formData)
          ElMessage.success('更新成功')
        } else {
          await createMember(formData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchMemberList()
      } catch (error) {
        ElMessage.error(formData.id ? '更新失败' : '创建失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 对话框关闭
const handleDialogClose = () => {
  resetForm()
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    id: null,
    name: '',
    phone: '',
    card_number: '',
    level: 'normal',
    remaining_classes: 0,
    valid_until: ''
  })
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// 分页大小改变
const handleSizeChange = (val) => {
  pagination.size = val
  fetchMemberList()
}

// 当前页改变
const handleCurrentChange = (val) => {
  pagination.current = val
  fetchMemberList()
}

// 获取会员等级类型
const getLevelType = (level) => {
  const typeMap = {
    normal: '',
    silver: 'info',
    gold: 'warning',
    diamond: 'success'
  }
  return typeMap[level] || ''
}

// 获取会员等级文本
const getLevelText = (level) => {
  const textMap = {
    normal: '普通会员',
    silver: '银卡会员',
    gold: '金卡会员',
    diamond: '钻石会员'
  }
  return textMap[level] || level
}

// 格式化日期
const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

// 初始化
onMounted(() => {
  fetchMemberList()
})
</script>

<style scoped>
.member-list {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-area {
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.operation-area {
  margin-bottom: 20px;
}

.pagination-area {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>