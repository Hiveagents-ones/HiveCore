<template>
  <div class="operation-log">
    <div class="log-header">
      <h3>操作日志</h3>
      <div class="log-filters">
        <el-select v-model="filters.action" placeholder="操作类型" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="封禁用户" value="ban" />
          <el-option label="解封用户" value="unban" />
          <el-option label="处理申诉" value="appeal" />
        </el-select>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleFilterChange"
        />
      </div>
    </div>
    
    <el-table
      v-loading="loading"
      :data="logs"
      stripe
      style="width: 100%"
      height="400"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="admin_name" label="操作人" width="120" />
      <el-table-column prop="action" label="操作类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getActionTagType(row.action)">
            {{ getActionText(row.action) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_user" label="目标用户" width="120" />
      <el-table-column prop="description" label="操作描述" min-width="200" />
      <el-table-column prop="ip_address" label="IP地址" width="130" />
      <el-table-column prop="created_at" label="操作时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="handleViewDetail(row)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
    
    <el-dialog
      v-model="detailDialogVisible"
      title="操作详情"
      width="50%"
    >
      <div v-if="selectedLog" class="log-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="操作ID">{{ selectedLog.id }}</el-descriptions-item>
          <el-descriptions-item label="操作人">{{ selectedLog.admin_name }}</el-descriptions-item>
          <el-descriptions-item label="操作类型">
            <el-tag :type="getActionTagType(selectedLog.action)">
              {{ getActionText(selectedLog.action) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标用户">{{ selectedLog.target_user }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ selectedLog.ip_address }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">{{ formatDate(selectedLog.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="操作描述" :span="2">{{ selectedLog.description }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedLog.details" label="详细信息" :span="2">
            <pre>{{ JSON.stringify(selectedLog.details, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getOperationLogs } from '@/api/admin'

const loading = ref(false)
const logs = ref([])
const detailDialogVisible = ref(false)
const selectedLog = ref(null)

const filters = reactive({
  action: '',
  dateRange: null
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

const getActionTagType = (action) => {
  const typeMap = {
    ban: 'danger',
    unban: 'success',
    appeal: 'warning'
  }
  return typeMap[action] || 'info'
}

const getActionText = (action) => {
  const textMap = {
    ban: '封禁用户',
    unban: '解封用户',
    appeal: '处理申诉'
  }
  return textMap[action] || action
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      action: filters.action || undefined,
      start_date: filters.dateRange?.[0]?.toISOString(),
      end_date: filters.dateRange?.[1]?.toISOString()
    }
    
    const response = await getOperationLogs(params)
    logs.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error('获取操作日志失败')
    console.error('Failed to fetch operation logs:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.currentPage = 1
  fetchLogs()
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  pagination.currentPage = 1
  fetchLogs()
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val
  fetchLogs()
}

const handleViewDetail = (log) => {
  selectedLog.value = log
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.operation-log {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.log-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.log-filters {
  display: flex;
  gap: 12px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.log-detail {
  padding: 20px 0;
}

.log-detail pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}
</style>