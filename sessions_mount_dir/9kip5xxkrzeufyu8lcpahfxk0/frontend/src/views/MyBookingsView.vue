<template>
  <div class="my-bookings-container">
    <el-page-header @back="goBack" content="我的预约" />

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else class="bookings-content">
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="即将开始" name="upcoming">
          <booking-list 
            :bookings="upcomingBookings" 
            @cancel="handleCancelBooking"
          />
        </el-tab-pane>
        <el-tab-pane label="历史记录" name="history">
          <booking-list 
            :bookings="pastBookings" 
            @cancel="handleCancelBooking"
          />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ElMessageBox } from 'element-plus';
import { getMyBookings, cancelBooking } from '../api/courses';
import BookingList from '../components/BookingList.vue';

export default {
  name: 'MyBookingsView',
  components: {
    BookingList
  },
  setup() {
    const router = useRouter();
    const activeTab = ref('upcoming');
    const upcomingBookings = ref([]);
    const pastBookings = ref([]);
    const loading = ref(true);

    const goBack = () => {
      router.go(-1);
    };

    const fetchMyBookings = async () => {
      try {
        loading.value = true;
        const response = await getMyBookings();
        const now = new Date();
        
        upcomingBookings.value = response.data.filter(
          booking => new Date(booking.course.start_time) > now
        );
        
        pastBookings.value = response.data.filter(
          booking => new Date(booking.course.start_time) <= now
        );
      } catch (error) {
        ElMessage.error('获取预约列表失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const handleCancelBooking = async (bookingId) => {
      try {
        await ElMessageBox.confirm(
          '确定要取消此预约吗？取消后如需再次预约可能需要重新排队。',
          '取消预约确认',
          {
            confirmButtonText: '确定取消',
            cancelButtonText: '我再想想',
            type: 'warning',
            beforeClose: async (action, instance, done) => {
              if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                try {
                  await cancelBooking(bookingId);
                  ElMessage.success('取消预约成功');
                  await fetchMyBookings();
                  done();
                } catch (error) {
                  ElMessage.error('取消预约失败: ' + error.message);
                  instance.confirmButtonLoading = false;
                }
              } else {
                done();
              }
            }
          }
        );
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('取消预约失败: ' + error.message);
        }
      }
    };

    onMounted(() => {
      fetchMyBookings();
    });

    return {
      activeTab,
      upcomingBookings,
      pastBookings,
      loading,
      goBack,
      handleCancelBooking
    };
  }
};
</script>

<style scoped>
.my-bookings-container {
  padding: 20px;
}

.loading-container {
  padding: 20px;
}

.bookings-content {
  margin-top: 20px;
}
</style>