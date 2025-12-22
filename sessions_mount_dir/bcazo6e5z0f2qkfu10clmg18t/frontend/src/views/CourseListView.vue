<template>
  <div class="course-list-view">
    <div class="header">
      <h1>课程预约</h1>
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索课程名称或教练..."
          @input="handleSearch"
        />
        <select v-model="selectedCategory" @change="filterCourses">
          <option value="">全部类别</option>
          <option value="yoga">瑜伽</option>
          <option value="cycling">动感单车</option>
          <option value="strength">力量训练</option>
          <option value="dance">舞蹈</option>
          <option value="swimming">游泳</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchCourses" class="retry-btn">重试</button>
    </div>

    <div v-else class="course-grid">
      <div
        v-for="course in filteredCourses"
        :key="course.id"
        class="course-card"
      >
        <div class="course-image">
          <img :src="course.image || '/default-course.jpg'" :alt="course.name" />
          <span class="category-tag">{{ getCategoryName(course.category) }}</span>
        </div>
        
        <div class="course-info">
          <h3>{{ course.name }}</h3>
          <p class="description">{{ course.description }}</p>
          
          <div class="course-details">
            <div class="detail-item">
              <i class="icon">📅</i>
              <span>{{ formatDate(course.date) }}</span>
            </div>
            <div class="detail-item">
              <i class="icon">⏰</i>
              <span>{{ course.time }}</span>
            </div>
            <div class="detail-item">
              <i class="icon">📍</i>
              <span>{{ course.location }}</span>
            </div>
            <div class="detail-item">
              <i class="icon">👤</i>
              <span>{{ course.instructor }}</span>
            </div>
          </div>
          
          <div class="availability">
            <div class="slots-info">
              <span class="available-slots">剩余名额: {{ course.available_slots }}</span>
              <div class="progress-bar">
                <div
                  class="progress"
                  :style="{ width: getSlotPercentage(course) + '%' }"
                ></div>
              </div>
            </div>
          </div>
          
          <div class="actions">
            <button
              @click="bookCourse(course)"
              class="book-btn"
              :disabled="course.available_slots === 0 || course.is_booked"
              :class="{
                'disabled': course.available_slots === 0,
                'booked': course.is_booked
              }"
            >
              {{ course.is_booked ? '已预约' : (course.available_slots === 0 ? '已满员' : '立即预约') }}
            </button>
            <button @click="viewDetails(course)" class="details-btn">
              查看详情
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="filteredCourses.length === 0 && !loading" class="no-results">
      <p>没有找到匹配的课程</p>
    </div>

    <!-- 预约成功弹窗 -->
    <div v-if="showSuccessModal" class="modal-overlay" @click="closeModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>预约成功</h3>
          <button @click="closeModal" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <p>您已成功预约课程：{{ selectedCourse?.name }}</p>
          <p>请准时参加课程，系统将发送确认通知。</p>
        </div>
        <div class="modal-footer">
          <button @click="closeModal" class="confirm-btn">确定</button>
        </div>
      </div>
    </div>

    <!-- 课程详情弹窗 -->
    <div v-if="showDetailsModal" class="modal-overlay" @click="closeDetailsModal">
      <div class="modal details-modal" @click.stop>
        <div class="modal-header">
          <h3>课程详情</h3>
          <button @click="closeDetailsModal" class="close-btn">&times;</button>
        </div>
        <div class="modal-body" v-if="selectedCourse">
          <div class="course-detail-info">
            <h4>{{ selectedCourse.name }}</h4>
            <p>{{ selectedCourse.description }}</p>
            
            <div class="detail-grid">
              <div class="detail-row">
                <span class="label">类别:</span>
                <span>{{ getCategoryName(selectedCourse.category) }}</span>
              </div>
              <div class="detail-row">
                <span class="label">日期:</span>
                <span>{{ formatDate(selectedCourse.date) }}</span>
              </div>
              <div class="detail-row">
                <span class="label">时间:</span>
                <span>{{ selectedCourse.time }}</span>
              </div>
              <div class="detail-row">
                <span class="label">地点:</span>
                <span>{{ selectedCourse.location }}</span>
              </div>
              <div class="detail-row">
                <span class="label">教练:</span>
                <span>{{ selectedCourse.instructor }}</span>
              </div>
              <div class="detail-row">
                <span class="label">时长:</span>
                <span>{{ selectedCourse.duration }} 分钟</span>
              </div>
              <div class="detail-row">
                <span class="label">难度:</span>
                <span>{{ getDifficultyName(selectedCourse.difficulty) }}</span>
              </div>
              <div class="detail-row">
                <span class="label">剩余名额:</span>
                <span>{{ selectedCourse.available_slots }} / {{ selectedCourse.max_slots }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            @click="bookCourse(selectedCourse)"
            class="book-btn"
            :disabled="selectedCourse?.available_slots === 0 || selectedCourse?.is_booked"
          >
            {{ selectedCourse?.is_booked ? '已预约' : '立即预约' }}
          </button>
          <button @click="closeDetailsModal" class="cancel-btn">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { courseApi } from '../services/api';

// 响应式数据
const courses = ref([]);
const loading = ref(false);
const error = ref('');
const searchQuery = ref('');
const selectedCategory = ref('');
const showSuccessModal = ref(false);
const showDetailsModal = ref(false);
const selectedCourse = ref(null);

// 计算属性
const filteredCourses = computed(() => {
  let filtered = courses.value;
  
  if (selectedCategory.value) {
    filtered = filtered.filter(course => course.category === selectedCategory.value);
  }
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(course => 
      course.name.toLowerCase().includes(query) ||
      course.instructor.toLowerCase().includes(query) ||
      course.description.toLowerCase().includes(query)
    );
  }
  
  return filtered;
});

// 方法
const fetchCourses = async () => {
  loading.value = true;
  error.value = '';
  try {
    const response = await courseApi.getCourses();
    courses.value = response.data || response;
  } catch (err) {
    error.value = '获取课程列表失败，请稍后重试';
    console.error('Failed to fetch courses:', err);
  } finally {
    loading.value = false;
  }
};

const bookCourse = async (course) => {
  if (course.available_slots === 0 || course.is_booked) return;
  
  try {
    await courseApi.bookCourse(course.id);
    course.is_booked = true;
    course.available_slots -= 1;
    selectedCourse.value = course;
    showSuccessModal.value = true;
  } catch (err) {
    error.value = '预约失败，请重试';
    console.error('Failed to book course:', err);
  }
};

const viewDetails = (course) => {
  selectedCourse.value = course;
  showDetailsModal.value = true;
};

const closeModal = () => {
  showSuccessModal.value = false;
  selectedCourse.value = null;
};

const closeDetailsModal = () => {
  showDetailsModal.value = false;
  selectedCourse.value = null;
};

const handleSearch = () => {
  // 搜索逻辑已在计算属性中处理
};

const filterCourses = () => {
  // 筛选逻辑已在计算属性中处理
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  });
};

const getCategoryName = (category) => {
  const categories = {
    yoga: '瑜伽',
    cycling: '动感单车',
    strength: '力量训练',
    dance: '舞蹈',
    swimming: '游泳'
  };
  return categories[category] || category;
};

const getDifficultyName = (difficulty) => {
  const difficulties = {
    beginner: '初级',
    intermediate: '中级',
    advanced: '高级'
  };
  return difficulties[difficulty] || difficulty;
};

const getSlotPercentage = (course) => {
  if (!course.max_slots) return 0;
  const filled = course.max_slots - course.available_slots;
  return (filled / course.max_slots) * 100;
};

// 生命周期
onMounted(() => {
  fetchCourses();
});
</script>

<style scoped>
.course-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5rem;
  color: #333;
  margin-bottom: 20px;
}

.search-bar {
  display: flex;
  gap: 15px;
  align-items: center;
}

.search-bar input {
  flex: 1;
  padding: 12px 20px;
  border: 2px solid #e0e0e0;
  border-radius: 25px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.search-bar input:focus {
  outline: none;
  border-color: #4CAF50;
}

.search-bar select {
  padding: 12px 20px;
  border: 2px solid #e0e0e0;
  border-radius: 25px;
  font-size: 16px;
  background: white;
  cursor: pointer;
  transition: border-color 0.3s;
}

.search-bar select:focus {
  outline: none;
  border-color: #4CAF50;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  text-align: center;
  padding: 50px;
  color: #f44336;
}

.retry-btn {
  margin-top: 15px;
  padding: 10px 20px;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.3s;
}

.retry-btn:hover {
  background: #d32f2f;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 25px;
}

.course-card {
  background: white;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.course-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
}

.course-image {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.course-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.category-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(76, 175, 80, 0.9);
  color: white;
  padding: 5px 10px;
  border-radius: 15px;
  font-size: 12px;
}

.course-info {
  padding: 20px;
}

.course-info h3 {
  margin: 0 0 10px 0;
  font-size: 1.5rem;
  color: #333;
}

.description {
  color: #666;
  margin-bottom: 15px;
  line-height: 1.5;
}

.course-details {
  margin-bottom: 15px;
}

.detail-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #555;
}

.icon {
  margin-right: 8px;
  font-size: 16px;
}

.availability {
  margin-bottom: 20px;
}

.slots-info {
  margin-bottom: 10px;
}

.available-slots {
  font-size: 14px;
  color: #666;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s;
}

.actions {
  display: flex;
  gap: 10px;
}

.book-btn {
  flex: 1;
  padding: 12px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.book-btn:hover:not(.disabled):not(.booked) {
  background: #45a049;
}

.book-btn.disabled {
  background: #ccc;
  cursor: not-allowed;
}

.book-btn.booked {
  background: #2196F3;
  cursor: default;
}

.details-btn {
  padding: 12px 20px;
  background: transparent;
  color: #4CAF50;
  border: 2px solid #4CAF50;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.details-btn:hover {
  background: #4CAF50;
  color: white;
}

.no-results {
  text-align: center;
  padding: 50px;
  color: #666;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 15px;
  width: 90%;
  max-width: 500px;
  overflow: hidden;
}

.details-modal {
  max-width: 600px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.confirm-btn {
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.3s;
}

.confirm-btn:hover {
  background: #45a049;
}

.cancel-btn {
  padding: 10px 20px;
  background: transparent;
  color: #666;
  border: 2px solid #666;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-btn:hover {
  background: #666;
  color: white;
}

.course-detail-info h4 {
  margin: 0 0 15px 0;
  font-size: 1.3rem;
  color: #333;
}

.detail-grid {
  display: grid;
  gap: 10px;
}

.detail-row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.label {
  font-weight: bold;
  color: #666;
  min-width: 80px;
  margin-right: 15px;
}

@media (max-width: 768px) {
  .course-list-view {
    padding: 10px;
  }
  
  .header h1 {
    font-size: 2rem;
  }
  
  .search-bar {
    flex-direction: column;
  }
  
  .search-bar input,
  .search-bar select {
    width: 100%;
  }
  
  .course-grid {
    grid-template-columns: 1fr;
  }
  
  .modal {
    width: 95%;
  }
}
</style>