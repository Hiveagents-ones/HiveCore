<template>
  <div class="course-schedule">
    <div class="header">
      <h1>课程时间表</h1>
      <div class="stats">
        <el-tag type="success" size="large" effect="dark" round>
          <el-icon><User /></el-icon>
          已预约: {{ bookedCount }}
        </el-tag>
        <el-tag type="info" size="large" effect="dark" round>
          <el-icon><Calendar /></el-icon>
          总课程: {{ totalCount }}
        </el-tag>
        <el-tag type="warning" size="large" effect="dark" round>
          <el-icon><Clock /></el-icon>
          即将开始: {{ upcomingCount }}
        </el-tag>
      </div>
    </div>
    
    <div class="controls">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择日期"
        @change="fetchSchedule"
        :disabled-date="disabledDate"
        :shortcuts="dateShortcuts"
      />
      <el-select 
        v-model="selectedTime" 
        placeholder="选择时间段" 
        clearable
        @change="fetchSchedule"
        style="width: 180px; margin-left: 10px;"
      >
        <el-option 
          v-for="time in timeOptions" 
          :key="time.value" 
          :label="time.label" 
          :value="time.value"
        />
      </el-select>
      <el-button type="primary" @click="fetchSchedule" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <el-table 
  :data="scheduleData" 
  style="width: 100%" 
  v-loading="loading"
  :row-class-name="({row}) => {
    if (isBooked(row)) return 'booked-row';
    if (row.remaining_capacity <= 0) return 'warning-row';
    
    // 高亮即将开始的课程
    const now = new Date()
    const startTime = new Date(row.start_time)
    const oneHourLater = new Date(now.getTime() + 3600 * 1000)
    if (startTime > now && startTime <= oneHourLater) return 'upcoming-row';
    
    return '';
  }"
  empty-text="暂无课程数据"
  stripe
  border
  highlight-current-row
  @row-click="handleRowClick"
  :default-sort="{ prop: 'start_time', order: 'ascending' }"
>
      <el-table-column prop="course.name" label="课程名称" width="180" sortable />
      <el-table-column label="时间" prop="start_time" sortable>
        <template #default="{ row }">
          {{ formatTime(row.start_time) }} - {{ formatTime(row.end_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="coach.name" label="教练" sortable />
<el-table-column label="剩余名额" width="120" prop="remaining_capacity" sortable>
        <template #default="{ row }">
          {{ row.remaining_capacity || 0 }}/{{ row.capacity || 0 }}
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button 
            type="primary" 
            size="small" 
            @click.stop="handleBooking(row)"
            :disabled="isBooked(row) || row.remaining_capacity <= 0"
            :loading="loading"
            :icon="isBooked(row) ? 'Check' : 'Plus'"
          >
            {{ isBooked(row) ? '已预约' : (row.remaining_capacity <= 0 ? '已满' : '预约') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCourseSchedule, bookCourse } from '@/api'
import { useCoursesStore } from '@/stores/courses'
import { ElMessage } from 'element-plus'
import { ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { User, Calendar, Check, Plus } from '@element-plus/icons-vue'
import { Clock } from '@element-plus/icons-vue'
import { Refresh } from '@element-plus/icons-vue'

const coursesStore = useCoursesStore()
const selectedDate = ref(new Date())
const selectedTime = ref('')
const timeOptions = [
  { label: '早晨 (6:00-10:00)', value: 'morning' },
  { label: '上午 (10:00-12:00)', value: 'late_morning' },
  { label: '下午 (12:00-17:00)', value: 'afternoon' },
  { label: '晚上 (17:00-21:00)', value: 'evening' },
]
const loading = computed(() => coursesStore.isLoading)
const scheduleData = computed(() => coursesStore.schedule)

const formatTime = (time) => {
  return dayjs(time).format('HH:mm')
}

const fetchSchedule = async () => {
  try {
    const params = {
      date: dayjs(selectedDate.value).format('YYYY-MM-DD'),
      time_range: selectedTime.value
    }
    await coursesStore.fetchSchedule(params)
  } catch (error) {
    ElMessage.error('获取课程表失败: ' + error.message)
  }
}

const handleBooking = async (schedule) => {
  await ElMessageBox.confirm(
    `确认预约 ${schedule.course.name} 课程?\n时间: ${formatTime(schedule.start_time)}-${formatTime(schedule.end_time)}\n教练: ${schedule.coach.name}`,
    '确认预约',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
  try {
    await coursesStore.bookCourse(schedule.id)
    ElMessage.success('预约成功')
  } catch (error) {
    ElMessage.error('预约失败: ' + error.message)
  }
}

const isBooked = (schedule) => {
  if (!schedule || schedule.remaining_capacity <= 0) {
    return false;
  }
  return coursesStore.bookings.some(booking => booking.schedule_id === schedule.id)
}

const handleRowClick = (row) => {
  if (!isBooked(row) && row.remaining_capacity > 0) {
    handleBooking(row)
  }
}
const bookedCount = computed(() => {
  return scheduleData.value.filter(schedule => isBooked(schedule)).length
})

const totalCount = computed(() => scheduleData.value.length)
const upcomingCount = computed(() => {
  const now = new Date()
  const oneHourLater = new Date(now.getTime() + 3600 * 1000)
  return scheduleData.value.filter(schedule => {
    const startTime = new Date(schedule.start_time)
    return startTime > now && startTime <= oneHourLater
  }).length
})

const disabledDate = (time) => {
  // 禁用今天之前的日期和30天后的日期
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const maxDate = new Date()
  maxDate.setDate(today.getDate() + 30)
  
  // 周末禁用逻辑
  const day = time.getDay()
  const isWeekend = day === 0 || day === 6
  
  return time.getTime() < today.getTime() || 
         time.getTime() > maxDate.getTime() ||
         isWeekend
}

const dateShortcuts = [
  {
    text: '今天',
    value: new Date(),
  },
  {
    text: '明天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000 * 24)
      return date
    },
  },
  {
    text: '3天后',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000 * 24 * 3)
      return date
    },
  },
  {
    text: '下周',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000 * 24 * 7)
      return date
    },
  },
]

  return coursesStore.bookings.some(booking => booking.schedule_id === schedule.id)
}

onMounted(() => {
  fetchSchedule()
})
</script>

<style scoped>
.course-schedule {
  padding: 20px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 20px;
}

.header .stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.controls {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
  align-items: center;
}

h1 {
  margin-bottom: 20px;
}
</style>

<style scoped>
.booked-row {
  --el-table-tr-bg-color: var(--el-color-success-light-9);
  cursor: not-allowed;
  opacity: 0.8;
}

.el-table :deep(.warning-row) {
  --el-table-tr-bg-color: var(--el-color-warning-light-9);
}

.el-table :deep(.booked-row) {
  background-color: var(--el-color-success-light-9);
}

.el-table {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  margin-top: 20px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.el-table :deep(th.el-table__cell) {
  font-weight: bold;
  color: var(--el-text-color-primary);
  background-color: #f5f7fa;
}
</style>

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
}

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
.upcoming-row {
  animation: pulse 2s infinite;
  --el-table-tr-bg-color: var(--el-color-warning-light-8);
}