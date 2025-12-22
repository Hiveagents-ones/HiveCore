<template>
  <div class="global-filter">
    <el-card class="filter-card">
      <div class="filter-content">
        <div class="filter-item">
          <label class="filter-label">日期范围</label>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :shortcuts="dateShortcuts"
            @change="handleDateChange"
            size="default"
            style="width: 280px"
          />
        </div>
        
        <div class="filter-item">
          <label class="filter-label">快速选择</label>
          <el-radio-group v-model="quickSelect" @change="handleQuickSelect" size="small">
            <el-radio-button label="today">今天</el-radio-button>
            <el-radio-button label="week">本周</el-radio-button>
            <el-radio-button label="month">本月</el-radio-button>
            <el-radio-button label="year">本年</el-radio-button>
          </el-radio-group>
        </div>

        <div class="filter-actions">
          <el-button type="primary" @click="handleFilter" :loading="loading">
            <el-icon><Search /></el-icon>
            筛选
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// Props
const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['filter', 'reset'])

// State
const dateRange = ref([])
const quickSelect = ref('')

// Date shortcuts
const dateShortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  },
  {
    text: '最近90天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    }
  },
  {
    text: '最近1年',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setFullYear(start.getFullYear() - 1)
      return [start, end]
    }
  }
]

// Computed
const filterParams = computed(() => {
  const params = {}
  
  if (dateRange.value && dateRange.value.length === 2) {
    params.startDate = formatDate(dateRange.value[0])
    params.endDate = formatDate(dateRange.value[1])
  }
  
  return params
})

// Methods
const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const setDateRange = (start, end) => {
  dateRange.value = [start, end]
}

const handleDateChange = (value) => {
  if (value) {
    quickSelect.value = ''
  }
}

const handleQuickSelect = (value) => {
  const end = new Date()
  let start = new Date()
  
  switch (value) {
    case 'today':
      start = new Date()
      break
    case 'week':
      start = new Date()
      start.setDate(start.getDate() - start.getDay())
      break
    case 'month':
      start = new Date()
      start.setDate(1)
      break
    case 'year':
      start = new Date()
      start.setMonth(0, 1)
      break
  }
  
  start.setHours(0, 0, 0, 0)
  end.setHours(23, 59, 59, 999)
  
  setDateRange(start, end)
}

const handleFilter = () => {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('请选择日期范围')
    return
  }
  
  emit('filter', filterParams.value)
}

const handleReset = () => {
  dateRange.value = []
  quickSelect.value = ''
  emit('reset')
}

// Watch for external changes
watch(() => props.loading, (newVal) => {
  if (newVal) {
    // Loading state handling if needed
  }
})
</script>

<style scoped>
.global-filter {
  margin-bottom: 20px;
}

.filter-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.filter-content {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  white-space: nowrap;
}

.filter-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

@media (max-width: 768px) {
  .filter-content {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .filter-actions {
    margin-left: 0;
    justify-content: center;
  }
}
</style>