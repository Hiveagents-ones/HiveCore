<template>
  <div class="course-detail-container">
    <el-page-header @back="goBack" content="课程详情" />
    
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>
    
    <div v-else-if="course" class="course-content">
      <el-card class="course-card">
        <div slot="header" class="course-header">
          <h2>{{ course.name }}</h2>
          <el-tag :type="getStatusTagType(course)">
            {{ getStatusText(course) }}
          </el-tag>
        </div>
        
        <div class="course-info">
          <div class="info-section">
            <h3>课程信息</h3>
            <p><strong>时间:</strong> {{ formatTime(course.start_time) }} - {{ formatTime(course.end_time) }}</p>
            <p><strong>教练:</strong> {{ course.coach_name }}</p>
            <p><strong>已预约:</strong> {{ course.booked_count }}/{{ course.capacity }}</p>
            <p><strong>时长:</strong> {{ getDuration(course) }}分钟</p>
          </div>
          
          <div class="description-section">
            <h3>课程描述</h3>
            <p>{{ course.description }}</p>
          </div>
        </div>
        
        <div class="course-actions">
          <el-button 
            type="primary" 
            :disabled="!canBook(course)"
            @click="handleBooking"
            :loading="bookingLoading"
          >
            预约课程
          </el-button>
          
          <el-button 
            v-if="isBooked"
            type="danger" 
            @click="handleCancelBooking"
          >
            取消预约
          </el-button>
        </div>
      </el-card>
      
      <div class="participants-section" v-if="participants.length > 0">
        <h3>已预约会员</h3>
        <el-table :data="participants" style="width: 100%">
          <el-table-column prop="member_name" label="会员姓名" />
          <el-table-column prop="booking_time" label="预约时间" :formatter="formatBookingTime" />
        </el-table>
      </div>
    </div>
    
    <div v-else class="no-course">
      <el-empty description="未找到课程信息" />
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useStore } from 'vuex';
import { getMemberBookings } from '../api/courses';
import { 
  getCourseDetail, 
  bookCourse, 
  cancelBooking,
  getCourseParticipants 
} from '../api/courses';

export default {
  name: 'CourseDetailView',
  setup() {
    const route = useRoute();
    const router = useRouter();
const store = useStore();
    
    const courseId = ref(route.params.id);
    const course = ref(null);
    const participants = ref([]);
    const loading = ref(true);
    const isBooked = ref(false);
    const bookingLoading = ref(false);
    
    const fetchCourseDetail = async () => {
      try {
        loading.value = true;
        const response = await getCourseDetail(courseId.value);
        course.value = response.data;
        await checkBookingStatus();
        await fetchParticipants();
      } catch (error) {
        ElMessage.error('获取课程详情失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    const fetchParticipants = async () => {
      try {
        const response = await getCourseParticipants(courseId.value);
        participants.value = response.data;
      } catch (error) {
        console.error('获取预约会员列表失败:', error);
      }
    };
    
    const checkBookingStatus = async () => {
      const memberId = store.state.user?.id;
      if (!memberId) {
        isBooked.value = false;
        return;
      }
      isBooked.value = participants.value.some(p => p.member_id === memberId);
    };
    
    const formatTime = (timeStr) => {
      return new Date(timeStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };
    
    const formatBookingTime = (row) => {
      return new Date(row.booking_time).toLocaleString();
    };
    
    const getDuration = (course) => {
      const start = new Date(course.start_time);
      const end = new Date(course.end_time);
      return Math.round((end - start) / (1000 * 60));
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
        course.booked_count < course.capacity &&
        !isBooked.value
      );
    };
    
    const handleBooking = async () => {
      if (!memberId) {
        ElMessage.warning('请先登录后再预约');
        return;
      }

      // 检查是否有时间冲突
      try {
        const bookings = await getMemberBookings(memberId);
        const hasConflict = bookings.some(booking => {
          const bookingStart = new Date(booking.start_time);
          const bookingEnd = new Date(booking.end_time);
          const courseStart = new Date(course.value.start_time);
          const courseEnd = new Date(course.value.end_time);
          
          return (courseStart >= bookingStart && courseStart < bookingEnd) || 
                 (courseEnd > bookingStart && courseEnd <= bookingEnd) ||
                 (courseStart <= bookingStart && courseEnd >= bookingEnd);
        });

        if (hasConflict) {
          ElMessage.warning('您已有其他课程安排在此时间段，请先取消后再预约');
          return;
        }
      } catch (error) {
        console.error('检查预约冲突失败:', error);
      }
      try {
        // TODO: 需要获取当前会员ID
        const memberId = 1; // 临时写死，实际应从登录状态获取
        await bookCourse(courseId.value, memberId);
        ElMessage.success('预约成功');
        await fetchCourseDetail();
      } catch (error) {
        ElMessage.error('预约失败: ' + error.message);
      }
    };
    
    const handleCancelBooking = async () => {
      if (!isBooked.value) {
        ElMessage.warning('您尚未预约该课程');
        return;
      }
      const memberId = store.state.user?.id;
      if (!memberId) {
        ElMessage.warning('请先登录后再操作');
        return;
      }

      try {
        bookingLoading.value = true;
        await cancelBooking(courseId.value, memberId);
        ElMessage.success('已取消预约');
        await fetchCourseDetail();
      } catch (error) {
        if (error.response?.data?.message) {
          ElMessage.error(`取消预约失败: ${error.response.data.message}`);
        } else {
          ElMessage.error('取消预约失败: ' + error.message);
        }
      } finally {
        bookingLoading.value = false;
      }
    };
    
    const goBack = () => {
      router.go(-1);
    };
    
    onMounted(() => {
      fetchCourseDetail();
    });
    
    return {
      course,
      participants,
      loading,
      isBooked,
      formatTime,
      formatBookingTime,
      getDuration,
      getStatusText,
      getStatusTagType,
      canBook,
      handleBooking,
      handleCancelBooking,
      goBack
    };
  }
};
</script>

<style scoped>
.course-detail-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.loading-container {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.course-card {
  margin-top: 20px;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.course-info {
  display: flex;
  gap: 40px;
}

.info-section, .description-section {
  flex: 1;
}

.course-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.participants-section {
  margin-top: 30px;
}
</style>