<template>
  <div class="reminder-config">
    <div class="page-header">
      <h1>提醒配置管理</h1>
      <p class="description">管理会员续费提醒的发送状态和重试功能</p>
    </div>

    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">总提醒数</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ stats.success }}</div>
        <div class="stat-label">发送成功</div>
      </div>
      <div class="stat-card pending">
        <div class="stat-value">{{ stats.pending }}</div>
        <div class="stat-label">待发送</div>
      </div>
      <div class="stat-card failed">
        <div class="stat-value">{{ stats.failed }}</div>
        <div class="stat-label">发送失败</div>
      </div>
    </div>

    <div class="config-section">
      <h2>提醒配置</h2>
      <el-form :model="reminderConfig" label-width="150px">
        <el-form-item label="提前提醒天数">
          <el-input-number
            v-model="reminderConfig.days_before"
            :min="1"
            :max="90"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="重试次数">
          <el-input-number
            v-model="reminderConfig.retry_count"
            :min="0"
            :max="5"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="重试间隔(分钟)">
          <el-input-number
            v-model="reminderConfig.retry_interval"
            :min="5"
            :max="1440"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="提醒通道">
          <el-checkbox-group v-model="reminderConfig.channels">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="push">推送通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="reminder-list">
      <h2>提醒发送记录</h2>
      <el-table :data="reminderList" v-loading="loading">
        <el-table-column prop="member_name" label="会员姓名" width="120" />
        <el-table-column prop="member_id" label="会员ID" width="100" />
        <el-table-column prop="type" label="提醒类型" width="120">
          <template #default="scope">
            <el-tag :type="getTypeTag(scope.row.type)">{{ scope.row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="channel" label="发送通道" width="100">
          <template #default="scope">
            <el-tag :type="getChannelTag(scope.row.channel)">{{ scope.row.channel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_at" label="计划时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.scheduled_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="sent_at" label="发送时间" width="180">
          <template #default="scope">
            {{ scope.row.sent_at ? formatDateTime(scope.row.sent_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="retry_count" label="重试次数" width="100" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button
              v-if="scope.row.status === 'failed'"
              type="primary"
              size="small"
              @click="retryReminder(scope.row)"
            >
              重试
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="viewDetails(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="detailDialogVisible"
      title="提醒详情"
      width="600px"
    >
      <div v-if="selectedReminder" class="reminder-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="会员ID">{{ selectedReminder.member_id }}</el-descriptions-item>
          <el-descriptions-item label="会员姓名">{{ selectedReminder.member_name }}</el-descriptions-item>
          <el-descriptions-item label="提醒类型">{{ selectedReminder.type }}</el-descriptions-item>
          <el-descriptions-item label="发送通道">{{ selectedReminder.channel }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTag(selectedReminder.status)">{{ selectedReminder.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="重试次数">{{ selectedReminder.retry_count }}</el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ formatDateTime(selectedReminder.scheduled_at) }}</el-descriptions-item>
          <el-descriptions-item label="发送时间">
            {{ selectedReminder.sent_at ? formatDateTime(selectedReminder.sent_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="收件人" span="2">{{ selectedReminder.recipient }}</el-descriptions-item>
          <el-descriptions-item label="错误信息" span="2" v-if="selectedReminder.error_message">
            <el-text type="danger">{{ selectedReminder.error_message }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="提醒内容" span="2">
            <div class="content-preview">{{ selectedReminder.content }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

const loading = ref(false)
const reminderList = ref([])
const detailDialogVisible = ref(false)
const selectedReminder = ref(null)

const stats = reactive({
  total: 0,
  success: 0,
  pending: 0,
  failed: 0
})

const reminderConfig = reactive({
  days_before: 7,
  retry_count: 3,
  retry_interval: 30,
  channels: ['email']
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const fetchReminderStats = async () => {
  try {
    const response = await api.get('/api/v1/reminders/stats')
    Object.assign(stats, response.data)
  } catch (error) {
    console.error('Error fetching reminder stats:', error)
  }
}

const fetchReminderList = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/v1/reminders', {
      params: {
        page: pagination.page,
        size: pagination.size
      }
    })
    reminderList.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Error fetching reminder list:', error)
    ElMessage.error('获取提醒列表失败')
  } finally {
    loading.value = false
  }
}

const fetchConfig = async () => {
  try {
    const response = await api.get('/api/v1/reminders/config')
    Object.assign(reminderConfig, response.data)
  } catch (error) {
    console.error('Error fetching reminder config:', error)
  }
}

const saveConfig = async () => {
  try {
    await api.post('/api/v1/reminders/config', reminderConfig)
    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error('Error saving reminder config:', error)
    ElMessage.error('保存配置失败')
  }
}

const retryReminder = async (reminder) => {
  try {
    await ElMessageBox.confirm('确定要重试发送此提醒吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.post(`/api/v1/reminders/${reminder.id}/retry`)
    ElMessage.success('重试任务已提交')
    fetchReminderList()
    fetchReminderStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Error retrying reminder:', error)
      ElMessage.error('重试失败')
    }
  }
}

const viewDetails = (reminder) => {
  selectedReminder.value = reminder
  detailDialogVisible.value = true
}

const handleSizeChange = (val) => {
  pagination.size = val
  pagination.page = 1
  fetchReminderList()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchReminderList()
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const getStatusTag = (status) => {
  const statusMap = {
    'success': 'success',
    'pending': 'warning',
    'failed': 'danger',
    'cancelled': 'info'
  }
  return statusMap[status] || 'info'
}

const getTypeTag = (type) => {
  const typeMap = {
    'renewal': 'primary',
    'payment': 'success',
    'expiry': 'warning'
  }
  return typeMap[type] || 'info'
}

const getChannelTag = (channel) => {
  const channelMap = {
    'email': 'primary',
    'sms': 'success',
    'push': 'warning'
  }
  return channelMap[channel] || 'info'
}

onMounted(() => {
  fetchReminderStats()
  fetchReminderList()
  fetchConfig()
})
</script>

<style scoped>
.reminder-config {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 10px;
}

.description {
  color: #666;
  font-size: 14px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-card.success {
  border-left: 4px solid #67c23a;
}

.stat-card.pending {
  border-left: 4px solid #e6a23c;
}

.stat-card.failed {
  border-left: 4px solid #f56c6c;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

.config-section,
.reminder-list {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.config-section h2,
.reminder-list h2 {
  font-size: 20px;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.reminder-detail {
  padding: 10px;
}

.content-preview {
  max-height: 200px;
  overflow-y: auto;
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>