<template>
  <div class="course-list-container">
    <h1>课程列表</h1>
    
    <div class="filter-section">
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索课程" 
        class="search-input" 
        clearable
      >
        <template #prefix>
          <el-icon><search /></el-icon>
        </template>
      </el-input>
    </div>
    
    <div class="course-cards">
      <el-card 
        v-for="course in filteredCourses" 
        :key="course.id" 
        class="course-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <span>{{ course.name }}</span>
            <el-tag :type="getCourseStatusTag(course)">
              {{ getCourseStatus(course) }}
            </el-tag>
          </div>
        </template>
        
        <div class="course-info">
          <p><el-icon><clock /></el-icon> 时间: {{ formatTime(course.time) }}</p>
          <p><el-icon><user /></el-icon> 教练: {{ getCoachName(course.coach_id) }}</p>
        </div>
        
        <template #footer>
          <el-button 
            type="primary" 
            @click="handleReserve(course)"
            :disabled="!isCourseAvailable(course)"
          >
            预约课程
          </el-button>
        </template>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { Search, Clock, User } from '@element-plus/icons-vue';
import { getCourses, getCoachSchedules } from '../api/courses';
import { ElMessage } from 'element-plus';

export default {
  name: 'CourseListView',
  components: { Search, Clock, User },
  setup() {
    const courses = ref([]);
    const coaches = ref([]);
    const searchQuery = ref('');
    const loading = ref(false);

    // 获取课程和教练数据
    const fetchData = async () => {
      loading.value = true;
      try {
        const [coursesData, coachesData] = await Promise.all([
          getCourses(),
          getCoachSchedules()
        ]);
        courses.value = coursesData;
        coaches.value = coachesData;
      } catch (error) {
        ElMessage.error('加载数据失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    // 根据教练ID获取教练姓名
    const getCoachName = (coachId) => {
      const coach = coaches.value.find(c => c.id === coachId);
      return coach ? coach.name : '未知教练';
    };

    // 格式化时间
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleString();
    };

    // 获取课程状态
    const getCourseStatus = (course) => {
      const now = new Date();
      const courseTime = new Date(course.time);
      return courseTime > now ? '可预约' : '已结束';
    };

    // 获取课程状态标签类型
    const getCourseStatusTag = (course) => {
      return isCourseAvailable(course) ? 'success' : 'info';
    };

    // 检查课程是否可预约
    const isCourseAvailable = (course) => {
      const now = new Date();
      const courseTime = new Date(course.time);
      return courseTime > now;
    };

    // 处理预约课程
    const handleReserve = (course) => {
      ElMessage.success(`已预约课程: ${course.name}`);
      // 这里可以添加实际的预约逻辑
    };

    // 过滤课程
    const filteredCourses = computed(() => {
      return courses.value.filter(course => {
        const matchesSearch = course.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
          getCoachName(course.coach_id).toLowerCase().includes(searchQuery.value.toLowerCase());
        return matchesSearch;
      });
    });

    onMounted(() => {
      fetchData();
    });

    return {
      courses,
      coaches,
      searchQuery,
      loading,
      filteredCourses,
      getCoachName,
      formatTime,
      getCourseStatus,
      getCourseStatusTag,
      isCourseAvailable,
      handleReserve
    };
  }
};
</script>

<style scoped>
.course-list-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 20px;
  text-align: center;
}

.filter-section {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
}

.search-input {
  width: 300px;
}

.course-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  transition: transform 0.3s;
}

.course-card:hover {
  transform: translateY(-5px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.course-info {
  line-height: 1.8;
}

.course-info p {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 5px 0;
}
</style>