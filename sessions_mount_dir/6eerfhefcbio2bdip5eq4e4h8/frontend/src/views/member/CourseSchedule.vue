<template>
  <div class="course-schedule">
    <div class="schedule-header">
      <h2>课程表</h2>
      <div class="filter-controls">
        <el-select
          v-model="filters.coachId"
          placeholder="选择教练"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            v-for="coach in coaches"
            :key="coach.id"
            :label="coach.name"
            :value="coach.id"
          />
        </el-select>
        <el-select
          v-model="filters.category"
          placeholder="选择类别"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            v-for="cat in categories"
            :key="cat"
            :label="cat"
            :value="cat"
          />
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

    <div class="schedule-content">
      <RecycleScroller
        class="scroller"
        :items="filteredCourses"
        :item-size="120"
        key-field="id"
        v-slot="{ item }"
      >
        <div class="course-card">
          <div class="course-info">
            <h3>{{ item.name }}</h3>
            <p class="coach">教练: {{ item.coachName }}</p>
            <p class="time">{{ formatDateTime(item.startTime) }} - {{ formatDateTime(item.endTime) }}</p>
            <p class="location">地点: {{ item.location }}</p>
          </div>
          <div class="course-actions">
            <el-tag :type="getCourseStatusType(item.status)">{{ item.status }}</el-tag>
            <el-button
              v-if="item.status === 'available' && !item.booked"
              type="primary"
              size="small"
              @click="bookCourse(item)"
            >
              预约
            </el-button>
            <el-button
              v-if="item.booked"
              type="danger"
              size="small"
              @click="cancelBooking(item)"
            >
              取消预约
            </el-button>
          </div>
        </div>
      </RecycleScroller>

      <div v-if="loading" class="loading">
        <el-loading />
      </div>

      <div v-if="error" class="error">
        <el-alert
          :title="error"
          type="error"
          show-icon
          @close="error = null"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCourseStore } from '@/stores/course'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { ElMessage } from 'element-plus'

const courseStore = useCourseStore()
const { courses, loading, error, filteredCourses } = courseStore

const filters = ref({
  coachId: null,
  category: null,
  dateRange: null
})

const coaches = ref([
  { id: 1, name: '张教练' },
  { id: 2, name: '李教练' },
  { id: 3, name: '王教练' }
])

const categories = ref([
  '瑜伽',
  '有氧',
  '力量训练',
  '游泳',
  '舞蹈'
])

const formatDateTime = (dateTime) => {
  if (!dateTime) return ''
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getCourseStatusType = (status) => {
  const statusMap = {
    available: 'success',
    full: 'warning',
    cancelled: 'danger',
    completed: 'info'
  }
  return statusMap[status] || 'info'
}

const handleFilterChange = () => {
  courseStore.updateFilters(filters.value)
  courseStore.resetCourses()
}

const bookCourse = async (course) => {
  try {
    await courseStore.bookCourse(course.id)
    ElMessage.success('预约成功！')
  } catch (err) {
    ElMessage.error('预约失败，请重试')
  }
}

const cancelBooking = async (course) => {
  try {
    await courseStore.cancelBooking(course.id)
    ElMessage.success('取消预约成功！')
  } catch (err) {
    ElMessage.error('取消预约失败，请重试')
  }
}

onMounted(() => {
  courseStore.fetchCourses()
})
</script>

<style scoped>
.course-schedule {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.schedule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.schedule-header h2 {
  margin: 0;
  color: #333;
}

.filter-controls {
  display: flex;
  gap: 10px;
}

.schedule-content {
  position: relative;
}

.scroller {
  height: 600px;
}

.course-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  margin-bottom: 10px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.course-info h3 {
  margin: 0 0 8px 0;
  color: #409eff;
}

.course-info p {
  margin: 4px 0;
  color: #666;
  font-size: 14px;
}

.course-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.error {
  margin-top: 20px;
}
</style>