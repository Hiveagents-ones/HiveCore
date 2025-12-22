<template>
  <div class="course-list">
    <div class="header">
      <h1>课程管理</h1>
      <button @click="showCreateForm = true" class="btn btn-primary">创建新课程</button>
    </div>

    <!-- 课程列表视图 -->
    <div v-if="!showSchedule" class="course-list-view">
      <div class="view-toggle">
        <button @click="showSchedule = false" class="btn btn-secondary active">列表视图</button>
        <button @click="showSchedule = true" class="btn btn-secondary">课程表视图</button>
      </div>

      <div class="course-grid">
        <VirtualScroll
          :items="paginatedCourses"
          :item-height="320"
          :container-height="600"
          key-field="id"
        >
          <template #default="{ item: course }">
            <div class="course-card">
          <div class="course-header">
            <h3>{{ course.name }}</h3>
            <span class="course-status" :class="course.status">{{ course.status }}</span>
          </div>
          <div class="course-info">
            <p><strong>教练:</strong> {{ course.coach }}</p>
            <p><strong>时间:</strong> {{ formatTime(course.time) }}</p>
            <p><strong>地点:</strong> {{ course.location }}</p>
            <p><strong>容量:</strong> {{ course.capacity }}人</p>
            <p><strong>已预约:</strong> {{ course.booked_count || 0 }}人</p>
          </div>
          <div class="course-description">
            <p>{{ course.description }}</p>
          </div>
          <div class="course-actions">
            <button @click="editCourse(course)" class="btn btn-sm btn-secondary">编辑</button>
            <button @click="deleteCourse(course.id)" class="btn btn-sm btn-danger">删除</button>
            <button @click="viewBookings(course.id)" class="btn btn-sm btn-info">查看预约</button>
          </div>
            </div>
          </template>
        </VirtualScroll>
      </div>
      
      <!-- 分页控件 -->
      <div class="pagination-controls">
        <div class="page-size-selector">
          <label>每页显示:</label>
          <select v-model="pageSize" @change="changePageSize(pageSize)">
            <option value="5">5</option>
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
        </div>
        
        <div class="pagination-info">
          显示 {{ (currentPage - 1) * pageSize + 1 }}-{{ Math.min(currentPage * pageSize, totalCourses) }} 条，共 {{ totalCourses }} 条
        </div>
        
        <div class="pagination-buttons">
          <button 
            @click="prevPage" 
            :disabled="currentPage === 1"
            class="btn btn-secondary"
          >
            上一页
          </button>
          
          <span class="page-numbers">
            <button 
              v-for="page in Math.min(totalPages, 5)" 
              :key="page"
              @click="goToPage(page)"
              :class="['btn', 'btn-secondary', { active: currentPage === page }]"
            >
              {{ page }}
            </button>
            <span v-if="totalPages > 5" class="ellipsis">...</span>
          </span>
          
          <button 
            @click="nextPage" 
            :disabled="currentPage === totalPages"
            class="btn btn-secondary"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- 课程表视图 -->
    <div v-else class="schedule-view">
      <div class="view-toggle">
        <button @click="showSchedule = false" class="btn btn-secondary">列表视图</button>
        <button @click="showSchedule = true" class="btn btn-secondary active">课程表视图</button>
      </div>

      <div class="schedule-grid">
        <div class="time-header">时间</div>
        <div v-for="day in weekDays" :key="day" class="day-header">{{ day }}</div>
        
        <div v-for="timeSlot in timeSlots" :key="timeSlot" class="time-slot">
          {{ timeSlot }}
        </div>
        
        <div v-for="(day, dayIndex) in weekDays" :key="day" class="schedule-cells">
          <div 
            v-for="(timeSlot, timeIndex) in timeSlots" 
            :key="timeSlot" 
            class="schedule-cell"
            @click="addCourseToSchedule(dayIndex, timeIndex)"
          >
            <div 
              v-for="course in getCoursesForSlot(dayIndex, timeIndex)" 
              :key="course.id" 
              class="schedule-course"
              @click.stop="editCourse(course)"
            >
              {{ course.name }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑课程表单 -->
    <div v-if="showCreateForm || editingCourse" class="modal-overlay" @click="closeForm">
      <div class="modal" @click.stop>
        <h2>{{ editingCourse ? '编辑课程' : '创建新课程' }}</h2>
        <form @submit.prevent="saveCourse">
          <div class="form-group">
            <label for="name">课程名称</label>
            <input type="text" id="name" v-model="courseForm.name" required>
          </div>
          <div class="form-group">
            <label for="coach">教练</label>
            <input type="text" id="coach" v-model="courseForm.coach" required>
          </div>
          <div class="form-group">
            <label for="time">时间</label>
            <input type="datetime-local" id="time" v-model="courseForm.time" required>
          </div>
          <div class="form-group">
            <label for="location">地点</label>
            <input type="text" id="location" v-model="courseForm.location" required>
          </div>
          <div class="form-group">
            <label for="capacity">容量限制</label>
            <input type="number" id="capacity" v-model="courseForm.capacity" required>
          </div>
          <div class="form-group">
            <label for="description">课程描述</label>
            <textarea id="description" v-model="courseForm.description" rows="3"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeForm" class="btn btn-secondary">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 预约列表 -->
    <div v-if="showBookings" class="modal-overlay" @click="closeBookings">
      <div class="modal" @click.stop>
        <h2>课程预约列表</h2>
        <div v-if="bookings.length === 0" class="no-data">暂无预约</div>
        <div v-else class="booking-list">
          <div v-for="booking in bookings" :key="booking.id" class="booking-item">
            <div class="booking-info">
              <p><strong>会员ID:</strong> {{ booking.member_id }}</p>
              <p><strong>预约时间:</strong> {{ formatTime(booking.created_at) }}</p>
              <p><strong>状态:</strong> {{ booking.status }}</p>
            </div>
            <button @click="cancelBooking(booking.id)" class="btn btn-sm btn-danger">取消预约</button>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="closeBookings" class="btn btn-secondary">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { coursesApi } from '../api/courses.js';
import VirtualScroll from '../components/VirtualScroll.vue';

export default {
  name: 'CourseList',
  setup() {
    const courses = ref([]);
    const showCreateForm = ref(false);
    const editingCourse = ref(null);
    const showSchedule = ref(false);
    const showBookings = ref(false);
    const bookings = ref([]);
    const currentCourseId = ref(null);
    
    // 分页相关
    const currentPage = ref(1);
    const pageSize = ref(10);
    const totalCourses = ref(0);
    
    // 计算分页后的课程列表
    const paginatedCourses = computed(() => {
      const start = (currentPage.value - 1) * pageSize.value;
      const end = start + pageSize.value;
      return courses.value.slice(start, end);
    });
    
    // 计算总页数
    const totalPages = computed(() => {
      return Math.ceil(courses.value.length / pageSize.value);
    });
    
    const courseForm = ref({
      name: '',
      coach: '',
      time: '',
      location: '',
      capacity: 0,
      description: ''
    });

    const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const timeSlots = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];

    const fetchCourses = async () => {
      try {
        const data = await coursesApi.getCourses();
        courses.value = data;
        totalCourses.value = data.length;
        currentPage.value = 1; // 重置到第一页
      } catch (error) {
        console.error('Failed to fetch courses:', error);
      }
    };

    const saveCourse = async () => {
      try {
        if (editingCourse.value) {
          await coursesApi.updateCourse(editingCourse.value.id, courseForm.value);
        } else {
          await coursesApi.createCourse(courseForm.value);
        }
        closeForm();
        fetchCourses();
      } catch (error) {
        console.error('Failed to save course:', error);
      }
    };

    const editCourse = (course) => {
      editingCourse.value = course;
      courseForm.value = { ...course };
      showCreateForm.value = true;
    };

    const deleteCourse = async (courseId) => {
      if (confirm('确定要删除这个课程吗？')) {
        try {
          await coursesApi.deleteCourse(courseId);
          fetchCourses();
        } catch (error) {
          console.error('Failed to delete course:', error);
        }
      }
    };

    const closeForm = () => {
      showCreateForm.value = false;
      editingCourse.value = null;
      courseForm.value = {
        name: '',
        coach: '',
        time: '',
        location: '',
        capacity: 0,
        description: ''
      };
    };

    const viewBookings = async (courseId) => {
      try {
        currentCourseId.value = courseId;
        const data = await coursesApi.getCourseBookings(courseId);
        bookings.value = data;
        showBookings.value = true;
      } catch (error) {
        console.error('Failed to fetch bookings:', error);
      }
    };

    const closeBookings = () => {
      showBookings.value = false;
      bookings.value = [];
      currentCourseId.value = null;
    };

    const cancelBooking = async (bookingId) => {
      if (confirm('确定要取消这个预约吗？')) {
        try {
          await coursesApi.cancelBooking(currentCourseId.value, bookingId);
          viewBookings(currentCourseId.value);
        } catch (error) {
          console.error('Failed to cancel booking:', error);
        }
      }
    };

    const formatTime = (timeString) => {
      if (!timeString) return '';
      const date = new Date(timeString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };

    const getCoursesForSlot = (dayIndex, timeIndex) => {
      return courses.value.filter(course => {
        const courseDate = new Date(course.time);
        const courseDay = courseDate.getDay() === 0 ? 6 : courseDate.getDay() - 1;
        const courseHour = courseDate.getHours().toString().padStart(2, '0');
        const courseMinute = courseDate.getMinutes().toString().padStart(2, '0');
        const courseTime = `${courseHour}:${courseMinute}`;
        
        return courseDay === dayIndex && courseTime === timeSlots[timeIndex];
      });
    };

    const addCourseToSchedule = (dayIndex, timeIndex) => {
      selectedTimeSlot = { dayIndex, timeIndex };
      showCreateForm = true;
    };

    // 分页控制函数
    const goToPage = (page) => {
    // 分页控制函数
    const goToPage = (page) => {
      if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page;
      }
    };
    
    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
      }
    };
    
    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
      }
    };
    
    const changePageSize = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
    };
      const date = new Date();
      const currentDay = date.getDay() === 0 ? 6 : date.getDay() - 1;
      const daysToAdd = dayIndex - currentDay;
      date.setDate(date.getDate() + daysToAdd);
      
      const [hours, minutes] = timeSlots[timeIndex].split(':');
      date.setHours(parseInt(hours), parseInt(minutes), 0, 0);
      
      courseForm.value.time = date.toISOString().slice(0, 16);
      showCreateForm.value = true;
    };

    onMounted(() => {
      fetchCourses();
    });

    return {
      courses,
      paginatedCourses,
      showCreateForm,
      editingCourse,
      courseForm,
      showSchedule,
      showBookings,
      bookings,
      weekDays,
      timeSlots,
      currentPage,
      pageSize,
      totalCourses,
      totalPages,
      saveCourse,
      editCourse,
      deleteCourse,
      closeForm,
      viewBookings,
      closeBookings,
      cancelBooking,
      formatTime,
      getCoursesForSlot,
      addCourseToSchedule,
      goToPage,
      nextPage,
      prevPage,
      changePageSize
    };
  }
};
</script>

<style scoped>
.course-list {
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

.view-toggle {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.btn-secondary.active {
  background-color: #495057;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-info:hover {
  background-color: #138496;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.course-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.course-status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.course-status.active {
  background-color: #d4edda;
  color: #155724;
}

.course-status.inactive {
  background-color: #f8d7da;
  color: #721c24;
}

.course-info p {
  margin: 4px 0;
  font-size: 14px;
}

.course-description {
  margin: 12px 0;
  font-size: 14px;
  color: #666;
}

.course-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.schedule-grid {
  display: grid;
  grid-template-columns: 80px repeat(7, 1fr);
  gap: 1px;
  background-color: #ddd;
  border: 1px solid #ddd;
}

.time-header, .day-header {
  background-color: #f8f9fa;
  padding: 8px;
  text-align: center;
  font-weight: bold;
}

.time-slot {
  background-color: #f8f9fa;
  padding: 8px;
  text-align: center;
  font-size: 14px;
}

.schedule-cell {
  background-color: white;
  min-height: 60px;
  padding: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.schedule-cell:hover {
  background-color: #f0f0f0;
}

.schedule-course {
  background-color: #007bff;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 2px;
  cursor: pointer;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: bold;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.booking-list {
  max-height: 400px;
  overflow-y: auto;
}

.booking-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #eee;
}

.booking-info p {
  margin: 4px 0;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #666;
}
</style>

.pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-size-selector select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.pagination-info {
  color: #666;
  font-size: 14px;
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-numbers .btn {
  min-width: 32px;
  padding: 4px 8px;
}

.ellipsis {
  padding: 0 8px;
  color: #666;
}

.course-grid {
  position: relative;
  height: 600px;
}