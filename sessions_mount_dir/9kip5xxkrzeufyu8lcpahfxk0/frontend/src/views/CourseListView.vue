<template>
  <div class="course-list-container">
    <h1>课程列表</h1>
    
    <div class="filter-section">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择日期"
        @change="fetchCourses"
      />
    </div>
    
    <div class="course-list">
      <el-card 
        v-for="course in courses" 
        :key="course.id" 
        class="course-card"
      >
        <div slot="header" class="course-header">
          <h3>{{ course.name }}</h3>
          <el-tag :type="getStatusTagType(course)">
            {{ getStatusText(course) }}
          </el-tag>
        </div>
        
        <div class="course-details">
          <p><strong>时间:</strong> {{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</p>
          <p><strong>教练:</strong> {{ course.coach_name }}</p>
          <p><strong>已预约:</strong> {{ course.booked_count }}/{{ course.capacity }}</p>
          <p><strong>描述:</strong> {{ course.description }}</p>
        </div>
        
        <div class="course-actions">
          <el-button 
            type="primary" 
            :disabled="!canBook(course)"
            @click="handleBooking(course)"
          >
            预约课程
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { getCourseSchedule, bookCourse } from '../api/courses';

export default {
  name: 'CourseListView',
  setup() {
    const courses = ref([]);
    const selectedDate = ref(new Date());
    
    const fetchCourses = async () => {
      try {
        const dateStr = selectedDate.value.toISOString().split('T')[0];
        const response = await getCourseSchedule(dateStr);
        courses.value = response.data;
      } catch (error) {
        ElMessage.error('获取课程列表失败: ' + error.message);
      }
    };
    
    const formatTime = (timeStr) => {
      return new Date(timeStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };
    
    const getStatusText = (course) => {
      if (new Date(course.start_time) < new Date()) return '已结束';
      if (course.booked_count >= course.capacity) return '已满';
      return '可预约';
    };
    
    const getStatusTagType = (course) => {
      if (new Date(course.start_time) < new Date()) return 'info';
      if (course.booked_count >= course.capacity) return 'danger';
      return 'success';
    };
    
    const canBook = (course) => {
      return (
        new Date(course.start_time) > new Date() && 
        course.booked_count < course.capacity
      );
    };
    
    const handleBooking = async (course) => {
      try {
        // TODO: 需要获取当前会员ID
        const memberId = 1; // 临时写死，实际应从登录状态获取
        await bookCourse(course.id, memberId);
        ElMessage.success('预约成功');
        fetchCourses(); // 刷新列表
      } catch (error) {
        ElMessage.error('预约失败: ' + error.message);
      }
    };
    
    onMounted(() => {
      fetchCourses();
    });
    
    return {
      courses,
      selectedDate,
      fetchCourses,
      formatTime,
      getStatusText,
      getStatusTagType,
      canBook,
      handleBooking
    };
  }
};
</script>

<style scoped>
.course-list-container {
  padding: 20px;
}

.filter-section {
  margin-bottom: 20px;
}

.course-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.course-card {
  height: 100%;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.course-details {
  margin-bottom: 15px;
}

.course-actions {
  display: flex;
  justify-content: flex-end;
}
</style>