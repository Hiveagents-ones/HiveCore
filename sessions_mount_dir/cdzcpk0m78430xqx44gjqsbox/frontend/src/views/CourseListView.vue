<template>
  <div class="course-list-view">
    <div class="filters">
      <div class="filter-group">
        <label for="date-filter">日期:</label>
        <input 
          id="date-filter" 
          type="date" 
          v-model="dateFilter" 
          @change="fetchCourses"
        />
      </div>
      
      <div class="filter-group">
        <label for="coach-filter">教练:</label>
        <select 
          id="coach-filter" 
          v-model="coachFilter" 
          @change="fetchCourses"
        >
          <option value="">全部</option>
          <option 
            v-for="coach in coaches" 
            :key="coach.id" 
            :value="coach.id"
          >
            {{ coach.name }}
          </option>
        </select>
      </div>
    </div>
    
    <div class="course-table">
      <div class="table-header">
        <div class="header-cell">课程名称</div>
        <div class="header-cell">时间</div>
        <div class="header-cell">教练</div>
        <div class="header-cell">预约人数</div>
        <div class="header-cell">操作</div>
      </div>
      
      <div 
        class="table-row" 
        v-for="course in filteredCourses" 
        :key="course.id"
      >
        <div class="table-cell">{{ course.name }}</div>
        <div class="table-cell">
          {{ formatTime(course.schedule) }}
          ({{ course.duration }}分钟)
        </div>
        <div class="table-cell">{{ getCoachName(course.coach_id) }}</div>
        <div class="table-cell">{{ course.booking_count || 0 }}/{{ course.max_participants || 20 }}</div>
        <div class="table-cell">
          <button 
            v-if="!isBooked(course.id)" 
            @click="bookCourse(course.id)"
            :disabled="course.booking_count >= (course.max_participants || 20)"
          >
            预约
          </button>
          <button 
            v-else 
            @click="cancelBooking(course.id)"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useCourseStore } from '@/stores/courseStore';
import { 
  getCourses, 
  bookCourse, 
  cancelBooking, 
  getBookingCount 
} from '@/api/courses';

export default {
  name: 'CourseListView',
  setup() {
    const courses = ref([]);
    const coaches = ref([]);
    const memberId = ref(1); // 假设当前会员ID为1
    const dateFilter = ref('');
    const coachFilter = ref('');
    const bookings = ref([]);

    const fetchCourses = async () => {
      try {
        const data = await getCourses();
        courses.value = data;
        
        // 提取教练列表
        const uniqueCoaches = {};
        data.forEach(course => {
          if (course.coach_id && !uniqueCoaches[course.coach_id]) {
            uniqueCoaches[course.coach_id] = {
              id: course.coach_id,
              name: course.coach_name
            };
          }
        });
        coaches.value = Object.values(uniqueCoaches);
        
        // 获取每个课程的预约人数
        for (const course of courses.value) {
          course.booking_count = await getBookingCount(course.id);
        }
        
        // 获取当前会员的预约记录
        // 这里简化处理，实际应该从API获取
        bookings.value = []; // 重置
      } catch (error) {
        console.error('加载课程失败:', error);
      }
    };

    const formatTime = (datetime) => {
      if (!datetime) return '';
      const date = new Date(datetime);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    };

    const getCoachName = (coachId) => {
      const coach = coaches.value.find(c => c.id === coachId);
      return coach ? coach.name : '未知教练';
    };

    const isBooked = (courseId) => {
      return bookings.value.some(b => b.course_id === courseId);
    };

    const book = async (courseId) => {
      try {
        const course = courses.value.find(c => c.id === courseId);
        if (course) {
          course.isProcessing = true;
          course.processingType = 'booking';
        }
        await courseStore.bookCourse({ courseId, memberId: memberId.value });
        bookings.value.push({ course_id: courseId });
        await fetchCourses(); // 刷新数据
      } catch (error) {
        console.error('预约失败:', error);
        if (error.message.includes('正在被其他操作处理中')) {
          alert(error.message);
        }
      } finally {
        const course = courses.value.find(c => c.id === courseId);
        if (course) {
          course.isProcessing = false;
          course.processingType = null;
        }
      }
    };

    const cancel = async (courseId) => {
      try {
        const course = courses.value.find(c => c.id === courseId);
        if (course) {
          course.isProcessing = true;
          course.processingType = 'canceling';
        }
        const booking = bookings.value.find(b => b.course_id === courseId);
        if (booking) {
          await courseStore.cancelBooking(booking.id);
          bookings.value = bookings.value.filter(b => b.course_id !== courseId);
          await fetchCourses(); // 刷新数据
        }
      } catch (error) {
        console.error('取消预约失败:', error);
        if (error.message.includes('正在被其他操作处理中')) {
          alert(error.message);
        }
      } finally {
        const course = courses.value.find(c => c.id === courseId);
        if (course) {
          course.isProcessing = false;
          course.processingType = null;
        }
      }
    };

    const filteredCourses = computed(() => {
      let result = courses.value;
      
      if (dateFilter.value) {
        const filterDate = new Date(dateFilter.value).toDateString();
        result = result.filter(course => {
          const courseDate = new Date(course.schedule).toDateString();
          return courseDate === filterDate;
        });
      }
      
      if (coachFilter.value) {
        result = result.filter(course => course.coach_id === coachFilter.value);
      }
      
      return result;
    });

    onMounted(() => {
      fetchCourses();
    });

    return {
      courses,
      coaches,
      dateFilter,
      coachFilter,
      filteredCourses,
      bookings,
      fetchCourses,
      formatTime,
      getCoachName,
      isBooked,
      bookCourse: book,
      cancelBooking: cancel
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

.filters {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-table {
  display: flex;
  flex-direction: column;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.table-header, .table-row {
  display: grid;
  grid-template-columns: 2fr 2fr 1fr 1fr 1fr;
  gap: 10px;
  padding: 12px 15px;
}

.table-header {
  background-color: #f0f0f0;
  font-weight: bold;
}

.table-row {
  border-top: 1px solid #ddd;
}

.table-row:nth-child(even) {
  background-color: #f9f9f9;
}

.table-cell {
  display: flex;
  align-items: center;
}

button {
  padding: 6px 12px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

button[disabled] {
  opacity: 0.6;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
            <span v-if="course.isProcessing && course.processingType === 'booking'">处理中...</span>
            <span v-else>预约</span>

# [AUTO-APPENDED] Failed to insert:
            <span v-if="course.isProcessing && course.processingType === 'canceling'">处理中...</span>
            <span v-else>取消</span>

# [AUTO-APPENDED] Failed to insert:

button .processing {
  opacity: 0.7;
}