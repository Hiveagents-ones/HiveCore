<template>
  <div class="user-management">
    <div class="page-header">
      <h1>用户管理</h1>
      <p class="page-description">查看和管理平台所有用户</p>
    </div>

    <div class="filters-section">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="搜索">
          <el-input
            v-model="filters.search"
            placeholder="用户名/邮箱"
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable @change="handleSearch">
            <el-option label="正常" value="active" />
            <el-option label="已封禁" value="banned" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部" clearable @change="handleSearch">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-section">
      <el-table
        v-loading="loading"
        :data="users"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '已封禁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              type="danger"
              size="small"
              @click="handleBan(row)"
            >
              封禁
            </el-button>
            <el-button
              v-else
              type="success"
              size="small"
              @click="handleUnban(row)"
            >
              解封
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleViewAppeals(row)"
            >
              查看申诉
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 用户详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      destroy-on-close
    >
      <div v-if="dialogType === 'appeals'">
        <el-table :data="appeals" stripe>
          <el-table-column prop="id" label="申诉ID" width="80" />
          <el-table-column prop="reason" label="申诉原因" min-width="150" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getAppealStatusType(row.status)">
                {{ getAppealStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="申诉时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'
                type="success"
                size="small"
                @click="handleApproveAppeal(row)"
              >
                批准
              </el-button>
              <el-button
                v-if="row.status === 'pending'"
                type="danger"
                size="small"
                @click="handleRejectAppeal(row)"
              >
                拒绝
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'

// 数据状态
const loading = ref(false)
const users = ref([])
const selectedUsers = ref([])
const appeals = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogType = ref('')

// 筛选条件
const filters = reactive({
  search: '',
  status: '',
  role: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 获取用户列表
const fetchUsers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      search: filters.search,
      status: filters.status,
      role: filters.role
    }
    const response = await adminApi.getUsers(params)
    users.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error('获取用户列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchUsers()
}

// 分页变化
const handlePageChange = (page) => {
  pagination.page = page
  fetchUsers()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchUsers()
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedUsers.value = selection
}

// 封禁用户
const handleBan = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要封禁用户 "${user.username}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await adminApi.banUser(user.id)
    ElMessage.success('封禁成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('封禁失败')
      console.error(error)
    }
  }
}

// 解封用户
const handleUnban = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要解封用户 "${user.username}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await adminApi.unbanUser(user.id)
    ElMessage.success('解封成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解封失败')
      console.error(error)
    }
  }
}

// 查看申诉
const handleViewAppeals = async (user) => {
  dialogType.value = 'appeals'
  dialogTitle.value = `用户 "${user.username}" 的申诉`
  dialogVisible.value = true
  
  try {
    const response = await adminApi.getUserAppeals(user.id)
    appeals.value = response.data
  } catch (error) {
    ElMessage.error('获取申诉列表失败')
    console.error(error)
  }
}

// 批准申诉
const handleApproveAppeal = async (appeal) => {
  try {
    await adminApi.approveAppeal(appeal.id)
    ElMessage.success('申诉已批准')
    // 刷新申诉列表
    const response = await adminApi.getUserAppeals(appeal.user_id)
    appeals.value = response.data
    // 刷新用户列表
    fetchUsers()
  } catch (error) {
    ElMessage.error('批准申诉失败')
    console.error(error)
  }
}

// 拒绝申诉
const handleRejectAppeal = async (appeal) => {
  try {
    await ElMessageBox.prompt('请输入拒绝原因', '拒绝申诉', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'textarea'
    })
    
    await adminApi.rejectAppeal(appeal.id, { reason: 'reason' })
    ElMessage.success('申诉已拒绝')
    // 刷新申诉列表
    const response = await adminApi.getUserAppeals(appeal.user_id)
    appeals.value = response.data
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('拒绝申诉失败')
      console.error(error)
    }
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 获取申诉状态类型
const getAppealStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return types[status] || 'info'
}

// 获取申诉状态文本
const getAppealStatusText = (status) => {
  const texts = {
    pending: '待处理',
    approved: '已批准',
    rejected: '已拒绝'
  }
  return texts[status] || status
}

// 初始化
onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.page-description {
  margin: 8px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.filters-section {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.filter-form {
  margin: 0;
}

.table-section {
  background: #fff;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>