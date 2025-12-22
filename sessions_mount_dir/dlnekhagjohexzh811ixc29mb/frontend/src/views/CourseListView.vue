<template>
  <div class="course-list-view">
    <div class="header">
      <h1>课程列表</h1>
      <div class="filter-controls">
        <el-select v-model="filter.coach" placeholder="选择教练" clearable>
          <el-option
            v-for="coach in coaches"
            :key="coach.id"
            :label="coach.name"
            :value="coach.id"
          />
        </el-select>
        <el-date-picker
          v-model="filter.date"
          type="date"
          placeholder="选择日期"
          clearable
        />
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else>
      <div v-if="error" class="error-message">
        <el-alert :title="error" type="error" show-icon />
      </div>

      <div class="course-grid">
        <el-card
          v-for="course in filteredCourses"
          :key="course.id"
          class="course-card"
          shadow="hover"
        >
          <template #header>
            <div class="course-header">
              <h3>{{ course.name }}</h3>
              <el-tag :type="getAvailabilityTagType(course.available_slots)">
                {{ course.available_slots }} 剩余名额
              </el-tag>
            </div>
          </template>

          <div class="course-body">
            <div class="course-info">
              <div class="info-row">
                <el-icon><Clock /></el-icon>
                <span>{{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</span>
              </div>
              <div class="info-row">
                <el-icon><User /></el-icon>
                <span>{{ getCoachName(course.coach_id) }}</span>
              </div>
              <div class="info-row">
                <el-icon><Location /></el-icon>
                <span>{{ course.location || '主训练室' }}</span>
              </div>
            </div>

            <div class="course-actions">
              <el-button
                type="primary"
                :disabled="course.available_slots <= 0"
                @click="handleBook(course.id)"
              >
                立即预约
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import { Clock, User, Location } from '@element-plus/icons-vue';
import { computed, onMounted, reactive, ref } from 'vue';
import { useCourseStore } from '../stores/courseStore';
import { ElMessage } from 'element-plus';

export default {
  name: 'CourseListView',
  components: { Clock, User, Location },
  setup() {
    const courseStore = useCourseStore();
    const loading = ref(false);
    const error = ref(null);

    const filter = reactive({
      coach: null,
      date: null
    });

    const fetchData = async () => {
      loading.value = true;
      try {
        await courseStore.fetchCourses();
        await courseStore.fetchPopularCourses();
        error.value = null;
      } catch (err) {
        error.value = err.message || '加载课程失败';
        console.error('Failed to load courses:', err);
      } finally {
        loading.value = false;
      }
    };

    const filteredCourses = computed(() => {
      let courses = courseStore.allCourses;
      
      if (filter.coach) {
        courses = courses.filter(c => c.coach_id === filter.coach);
      }
      
      if (filter.date) {
        const selectedDate = new Date(filter.date).toDateString();
        courses = courses.filter(c => {
          const courseDate = new Date(c.start_time).toDateString();
          return courseDate === selectedDate;
        });
      }
      
      return courses;
    });

    const getCoachName = (coachId) => {
      const coach = courseStore.allCoaches.find(c => c.id === coachId);
      return coach ? coach.name : '未知教练';
    };

    const formatTime = (timeString) => {
      const date = new Date(timeString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const getAvailabilityTagType = (slots) => {
      if (slots <= 0) return 'danger';
      if (slots <= 3) return 'warning';
      return 'success';
    };

    const handleBook = async (courseId) => {
      try {
        // TODO: 替换为实际的会员ID
        const memberId = 1; 
        await courseStore.bookCourse(courseId, memberId);
        ElMessage.success('预约成功！');
        await fetchData(); // 刷新数据
      } catch (err) {
        ElMessage.error(`预约失败: ${err.message}`);
      }
    };

    onMounted(() => {
      fetchData();
    });

    return {
      loading,
      error,
      filter,
      filteredCourses,
      coaches: courseStore.allCoaches,
      getCoachName,
      formatTime,
      getAvailabilityTagType,
      handleBook
    };
  }
};
</script>

<style scoped>
.course-list-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-controls {
  display: flex;
  gap: 10px;
}

.loading-container {
  padding: 20px;
}

.error-message {
  margin-bottom: 20px;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  height: 100%;
  transition: transform 0.3s;
}

.course-card:hover {
  transform: translateY(-5px);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.course-body {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
}

.course-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>