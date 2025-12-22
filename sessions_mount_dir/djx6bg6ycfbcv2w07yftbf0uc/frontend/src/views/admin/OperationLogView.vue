<template>
  <div class="operation-log-view">
    <div class="header">
      <h1>操作日志</h1>
      <div class="filters">
        <el-input
          v-model="searchQuery"
          placeholder="搜索操作者或操作描述"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="selectedOperation"
          placeholder="操作类型"
          clearable
          @change="handleSearch"
        >
          <el-option
            v-for="op in operationTypes"
            :key="op.value"
            :label="op.label"
            :value="op.value"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleSearch"
        />
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="logs"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="operator" label="操作者" width="120" />
      <el-table-column prop="operation" label="操作类型" width="120">
        <template #default="{ row }">
          <el-tag :type="getOperationTagType(row.operation)">
            {{ getOperationLabel(row.operation) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="操作描述" min-width="200" />
      <el-table-column prop="ip_address" label="IP地址" width="140" />
      <el-table-column prop="created_at" label="操作时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            @click="handleViewDetail(row)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="操作日志详情"
      width="600px"
    >
      <el-descriptions :column="1" border>
        <el-descriptions-item label="ID">{{ currentLog?.id }}</el-descriptions-item>
        <el-descriptions-item label="操作者">{{ currentLog?.operator }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getOperationTagType(currentLog?.operation)">
            {{ getOperationLabel(currentLog?.operation) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作描述">{{ currentLog?.description }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog?.ip_address }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ formatDateTime(currentLog?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="详细信息">
          <pre>{{ JSON.stringify(currentLog?.details, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from '@/utils/axios'

// 响应式数据
const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const selectedOperation = ref('')
const dateRange = ref([])
const detailDialogVisible = ref(false)
const currentLog = ref(null)

// 操作类型选项
const operationTypes = [
  { value: 'create', label: '创建' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'approve', label: '审核' },
  { value: 'reject', label: '拒绝' },
  { value: 'disable', label: '禁用' },
  { value: 'enable', label: '启用' },
  { value: 'login', label: '登录' },
  { value: 'logout', label: '登出' }
]

// 获取操作日志列表
const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      search: searchQuery.value,
      operation: selectedOperation.value,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1]
    }
    
    const response = await axios.get('/api/admin/operation-logs', { params })
    logs.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('获取操作日志失败')
    console.error('Failed to fetch operation logs:', error)
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchLogs()
}

// 处理分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  fetchLogs()
}

// 处理页码变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchLogs()
}

// 查看详情
const handleViewDetail = (row) => {
  currentLog.value = row
  detailDialogVisible.value = true
}

// 获取操作类型标签样式
const getOperationTagType = (operation) => {
  const typeMap = {
    create: 'success',
    update: 'primary',
    delete: 'danger',
    approve: 'success',
    reject: 'danger',
    disable: 'warning',
    enable: 'success',
    login: 'info',
    logout: 'info'
  }
  return typeMap[operation] || 'info'
}

// 获取操作类型标签
const getOperationLabel = (operation) => {
  const type = operationTypes.find(t => t.value === operation)
  return type ? type.label : operation
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 组件挂载
onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.operation-log-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filters {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filters .el-input {
  width: 240px;
}

.filters .el-select {
  width: 140px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

pre {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow-y: auto;
}
</style>