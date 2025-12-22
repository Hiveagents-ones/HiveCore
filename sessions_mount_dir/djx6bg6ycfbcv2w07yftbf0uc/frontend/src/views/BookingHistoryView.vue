<template>
  <div class="booking-history">
    <el-card class="header-card">
      <div class="header-content">
        <h2>预约记录</h2>
        <div class="header-actions">
          <el-button type="primary" @click="exportData" :loading="exporting">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
          <el-button @click="showAccountDialog">
            <el-icon><User /></el-icon>
            账户管理
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
            <el-option label="已预约" value="booked" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="bookingList"
        style="width: 100%"
        empty-text="暂无预约记录"
      >
        <el-table-column prop="course_name" label="课程名称" min-width="150" />
        <el-table-column prop="merchant_name" label="商家" min-width="120" />
        <el-table-column prop="coach_name" label="教练" min-width="100" />
        <el-table-column prop="booking_time" label="预约时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.booking_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="course_date" label="上课日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.course_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">
            ¥{{ row.price }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'booked'"
              type="danger"
              size="small"
              @click="handleCancel(row.id)"
            >
              取消预约
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="viewDetail(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 账户管理对话框 -->
    <el-dialog
      v-model="accountDialogVisible"
      title="账户管理"
      width="500px"
    >
      <el-form
        ref="accountFormRef"
        :model="accountForm"
        :rules="accountRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="accountForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="accountForm.email" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="accountForm.phone" />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="accountForm.password"
            type="password"
            placeholder="留空则不修改"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="accountForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="accountDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="updateAccount" :loading="updating">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="预约详情"
      width="600px"
    >
      <div v-if="currentBooking" class="booking-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="课程名称">
            {{ currentBooking.course_name }}
          </el-descriptions-item>
          <el-descriptions-item label="商家">
            {{ currentBooking.merchant_name }}
          </el-descriptions-item>
          <el-descriptions-item label="教练">
            {{ currentBooking.coach_name }}
          </el-descriptions-item>
          <el-descriptions-item label="上课地点">
            {{ currentBooking.location }}
          </el-descriptions-item>
          <el-descriptions-item label="上课日期">
            {{ formatDate(currentBooking.course_date) }}
          </el-descriptions-item>
          <el-descriptions-item label="上课时间">
            {{ currentBooking.course_time }}
          </el-descriptions-item>
          <el-descriptions-item label="预约时间">
            {{ formatDateTime(currentBooking.booking_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentBooking.status)">
              {{ getStatusText(currentBooking.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="价格">
            ¥{{ currentBooking.price }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ currentBooking.remark || '无' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, User } from '@element-plus/icons-vue'
import { courseApi } from '../services/api'

// 响应式数据
const loading = ref(false)
const exporting = ref(false)
const updating = ref(false)
const bookingList = ref([])
const accountDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentBooking = ref(null)
const accountFormRef = ref(null)

// 筛选表单
const filterForm = reactive({
  status: '',
  dateRange: []
})

// 分页
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 账户表单
const accountForm = reactive({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: ''
})

// 表单验证规则
const accountRules = {
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  password: [
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    {
      validator: (rule, value, callback) => {
        if (accountForm.password && value !== accountForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 获取预约列表
const fetchBookings = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      ...filterForm
    }
    
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }
    
    const response = await courseApi.getBookings(params)
    bookingList.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    console.error('获取预约记录失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理筛选
const handleFilter = () => {
  pagination.page = 1
  fetchBookings()
}

// 重置筛选
const resetFilter = () => {
  filterForm.status = ''
  filterForm.dateRange = []
  pagination.page = 1
  fetchBookings()
}

// 分页处理
const handleSizeChange = (val) => {
  pagination.size = val
  pagination.page = 1
  fetchBookings()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchBookings()
}

// 取消预约
const handleCancel = async (bookingId) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个预约吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await courseApi.cancelBooking(bookingId)
    ElMessage.success('取消预约成功')
    fetchBookings()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消预约失败:', error)
    }
  }
}

// 查看详情
const viewDetail = (booking) => {
  currentBooking.value = booking
  detailDialogVisible.value = true
}

// 导出数据
const exportData = async () => {
  exporting.value = true
  try {
    const params = {
      export: true,
      ...filterForm
    }
    
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }
    
    const response = await courseApi.getBookings(params)
    
    // 创建下载链接
    const blob = new Blob([response], { type: 'application/vnd.ms-excel' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `预约记录_${new Date().toLocaleDateString()}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

// 显示账户管理对话框
const showAccountDialog = () => {
  // 这里应该从用户信息API获取，暂时使用模拟数据
  accountForm.username = 'user123'
  accountForm.email = 'user@example.com'
  accountForm.phone = '13800138000'
  accountForm.password = ''
  accountForm.confirmPassword = ''
  accountDialogVisible.value = true
}

// 更新账户信息
const updateAccount = async () => {
  if (!accountFormRef.value) return
  
  try {
    await accountFormRef.value.validate()
    updating.value = true
    
    // 这里应该调用更新用户信息的API
    // await userApi.updateProfile(accountForm)
    
    ElMessage.success('账户信息更新成功')
    accountDialogVisible.value = false
  } catch (error) {
    console.error('更新账户信息失败:', error)
  } finally {
    updating.value = false
  }
}

// 状态相关方法
const getStatusType = (status) => {
  const map = {
    booked: 'warning',
    completed: 'success',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    booked: '已预约',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

// 日期格式化
const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString()
}

// 组件挂载时获取数据
onMounted(() => {
  fetchBookings()
})
</script>

<style scoped>
.booking-history {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin: 0;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.booking-detail {
  padding: 20px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>