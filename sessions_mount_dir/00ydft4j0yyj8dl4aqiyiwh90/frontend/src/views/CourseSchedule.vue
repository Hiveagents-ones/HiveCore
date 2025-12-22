<template>
  <div class="course-schedule">
    <h1>课程表</h1>
    
    <div class="controls">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择日期"
        @change="fetchCourses"
      />
      
      <el-select v-model="selectedType" placeholder="课程类型" @change="fetchCourses">
        <el-option label="全部" value=""></el-option>
        <el-option label="团体课" value="group"></el-option>
        <el-option label="私教课" value="private"></el-option>
      </el-select>
    </div>
    
    <div class="schedule-container">
      <el-table :data="courses" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="课程名称" width="180" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="scope">
            {{ scope.row.type === 'group' ? '团体课' : '私教课' }}
          </template>
        </el-table-column>
        <el-table-column prop="schedule" label="时间" width="180" />
        <el-table-column prop="duration" label="时长(分钟)" width="120" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button 
              size="small" 
              @click="handleBooking(scope.row)"
              :disabled="scope.row.booked"
            >
              {{ scope.row.booked ? '已预约' : '预约' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              v-if="scope.row.booked"
              @click="handleCancel(scope.row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCourses, bookCourse, cancelBooking } from '../api/courses'

const selectedDate = ref(new Date())
const selectedType = ref('')
const courses = ref([])
const loading = ref(false)

const fetchCourses = async () => {
  try {
    loading.value = true
    const params = {
      date: selectedDate.value.toISOString().split('T')[0],
      type: selectedType.value
    }
    const response = await getCourses(params)
    courses.value = response.data
  } catch (error) {
    ElMessage.error('获取课程失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleBooking = async (course) => {
  try {
    await ElMessageBox.confirm(`确定要预约 ${course.name} 课程吗?`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await bookCourse(course.id)
    ElMessage.success('预约成功')
    fetchCourses()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('预约失败: ' + error.message)
    }
  }
}

const handleCancel = async (course) => {
  try {
    await ElMessageBox.confirm(`确定要取消 ${course.name} 课程吗?`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await cancelBooking(course.bookingId)
    ElMessage.success('取消成功')
    fetchCourses()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败: ' + error.message)
    }
  }
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.course-schedule {
  padding: 20px;
}

.controls {
  margin: 20px 0;
  display: flex;
  gap: 20px;
}

.schedule-container {
  margin-top: 20px;
}
</style>