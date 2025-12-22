<template>
  <div class="course-list-container">
    <h1>课程列表</h1>
    
    <div class="actions">
      <button @click="refreshCourses" class="refresh-btn">刷新列表</button>
    </div>
    
    <div v-if="loading" class="loading">加载中...</div>
    
    <div v-if="error" class="error">
      加载课程失败: {{ error.message }}
    </div>
    
    <div v-if="courses.length === 0 && !loading" class="no-courses">
      暂无课程
    </div>
    
    <div class="course-cards">
      <div v-for="course in courses" :key="course.id" class="course-card">
        <h3>{{ course.name }}</h3>
        <p>{{ course.description }}</p>
        <div class="course-time">
          <span>开始时间: {{ formatTime(course.start_time) }}</span>
          <span>结束时间: {{ formatTime(course.end_time) }}</span>
        </div>
        <div class="course-actions">
          <button @click="bookCourse(course.id)" class="book-btn">预约</button>
          <button @click="cancelBooking(course.id)" class="cancel-btn">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getCourses, createCourseBooking, cancelCourseBooking } from '../api/courses';

export default {
  name: 'CourseList',
  setup() {
    const courses = ref([]);
    const loading = ref(false);
    const error = ref(null);

    const fetchCourses = async () => {
      loading.value = true;
      error.value = null;
      try {
        const data = await getCourses();
        courses.value = data;
      } catch (err) {
        error.value = err;
        console.error('Failed to fetch courses:', err);
      } finally {
        loading.value = false;
      }
    };

    const refreshCourses = () => {
      fetchCourses();
    };

    const bookCourse = async (courseId) => {
      try {
        await createCourseBooking({ course_id: courseId });
        alert('课程预约成功');
        fetchCourses();
      } catch (err) {
        console.error('Failed to book course:', err);
        alert('预约失败: ' + err.message);
      }
    };

    const cancelBooking = async (courseId) => {
      try {
        await cancelCourseBooking(courseId);
        alert('取消预约成功');
        fetchCourses();
      } catch (err) {
        console.error('Failed to cancel booking:', err);
        alert('取消失败: ' + err.message);
      }
    };

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleString();
    };

    onMounted(() => {
      fetchCourses();
    });

    return {
      courses,
      loading,
      error,
      refreshCourses,
      bookCourse,
      cancelBooking,
      formatTime
    };
  }
};
</script>

<style scoped>
.course-list-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.actions {
  margin-bottom: 20px;
  text-align: right;
}

.refresh-btn {
  padding: 8px 16px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.refresh-btn:hover {
  background-color: #369f6b;
}

.loading, .error, .no-courses {
  text-align: center;
  padding: 20px;
  margin: 20px 0;
}

.error {
  color: #ff5252;
}

.course-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.course-card h3 {
  margin-top: 0;
  color: #2c3e50;
}

.course-time {
  margin: 15px 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: #666;
}

.course-actions {
  display: flex;
  gap: 10px;
}

.book-btn, .cancel-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  flex: 1;
}

.book-btn {
  background-color: #42b983;
  color: white;
}

.book-btn:hover {
  background-color: #369f6b;
}

.cancel-btn {
  background-color: #ff5252;
  color: white;
}

.cancel-btn:hover {
  background-color: #ff0000;
}
</style>