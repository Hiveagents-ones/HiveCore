<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">课程预约</h1>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="4">
        <v-card class="pa-4">
          <v-date-picker
            v-model="dateRange"
            range
            :min="new Date().toISOString().substr(0, 10)"
            @update:modelValue="fetchCourses"
          
          ></v-date-picker>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>课程列表</v-card-title>
          <v-card-subtitle>
            <v-chip-group v-model="selectedType" mandatory>
              <v-chip v-for="type in courseTypes" :key="type.value" :value="type.value">
                {{ type.text }}
              </v-chip>
            </v-chip-group>
          </v-card-subtitle>
          <v-card-text>
            <v-progress-linear
              v-if="loading"
              indeterminate
              color="primary"
            ></v-progress-linear>

            <v-alert
              v-if="error"
              type="error"
              class="mb-4"
            >
              {{ error }}
            </v-alert>

            <v-list v-if="paginatedCourses.length > 0">
              <v-list-item
                v-for="course in paginatedCourses"
                :key="course.id"
                class="mb-4"
              >
                <template #prepend>
                  <v-avatar color="primary" class="mr-4">
                    <v-icon>mdi-dumbbell</v-icon>
                  </v-avatar>
                </template>

                <v-list-item-title>{{ course.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ formatDateTime(course.start_time) }} - {{ formatDateTime(course.end_time) }}
                </v-list-item-subtitle>
                <v-list-item-subtitle>教练: {{ course.coach_name }}</v-list-item-subtitle>

                <template #append>
                  <v-btn
                    v-if="!course.is_booked && authStore.isMember"
                    color="primary"
                    @click="bookCourse(course.id)"
                    :disabled="loading"
                  >
                    预约
                  </v-btn>
                  <v-btn
                    v-else-if="authStore.isMember"
                    color="error"
                    @click="cancelBooking(course.id)"
                    :disabled="loading"
                  >
                    取消预约
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>

            <v-alert
              v-else-if="!loading"
              type="info"
            >
              暂无课程数据
            </v-alert>
          <v-card-actions v-if="totalItems > itemsPerPage">
            <v-pagination
              v-model="currentPage"
              :length="Math.ceil(totalItems / itemsPerPage)"
              @update:modelValue="fetchCourses"
              :total-visible="5"
            ></v-pagination>
          </v-card-actions>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { computed } from 'vue';
import { watch } from 'vue';
import { useAuthStore } from '../stores/auth';
import { getCourses, bookCourse, cancelBooking } from '../api/courses';
import { useSnackbar } from '../composables/useSnackbar';
import { useRouter } from 'vue-router';
import { getCourseTypes } from '../api/courses';

const { showSnackbar } = useSnackbar();
const router = useRouter();
const courseTypes = ref([
  { text: '全部课程', value: 'all' }
]);
const selectedType = ref('all');
const authStore = useAuthStore();
const fetchCourseTypes = async () => {
  try {
    const types = await getCourseTypes();
    courseTypes.value = [
      { text: '全部课程', value: 'all' },
      ...types.map(type => ({
        text: type.name,
        value: type.id
      }))
    ];
  } catch (err) {
    console.error('获取课程类型失败:', err);
  }
};

const courses = ref([]);
const loading = ref(false);
const error = ref(null);
const dateRange = ref([
const currentPage = ref(1);
const itemsPerPage = ref(5);
const totalItems = ref(0);
  new Date().toISOString().substr(0, 10),
  new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().substr(0, 10)
]);

const formatDateTime = (dateTime) => {
const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return courses.value.slice(start, end);
});
  return new Date(dateTime).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const fetchCourses = async () => {
  try {
    loading.value = true;
    error.value = null;
    
    const [startDate, endDate] = dateRange.value;
    const params = {
      startDate,
      endDate,
      type: selectedType.value === 'all' ? undefined : selectedType.value
    };
    
    courses.value = await getCourses(params);
  } catch (err) {
    error.value = '获取课程列表失败，请稍后重试';
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const handleBooking = async (action, courseId) => {
  try {
    loading.value = true;
    
    if (action === 'book') {
      await bookCourse(courseId);
      showSnackbar('预约成功', 'success');
    } else {
      await cancelBooking(courseId);
      showSnackbar('取消预约成功', 'success');
    }
    
    await fetchCourses();
  } catch (err) {
    showSnackbar(`操作失败: ${err.response?.data?.message || err.message}`, 'error');
  } finally {
    loading.value = false;
  }
};

const bookCourse = (courseId) => handleBooking('book', courseId);
const cancelBooking = (courseId) => handleBooking('cancel', courseId);

watch(selectedType, fetchCourses);
watch(dateRange, fetchCourses);

onMounted(() => {
  fetchCourseTypes();
  if (!authStore.isAuthenticated) {
    router.push('/login');
    return;
  }
  
  if (authStore.isMember) {
    fetchCourses();
  } else {
    showSnackbar('只有会员可以预约课程', 'warning');
  }
});
</script>

<style scoped>
.v-list-item {
  border: 1px solid #eee;
  border-radius: 8px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const fetchCourses = async () => {
  try {
    loading.value = true;
    error.value = null;

    const [startDate, endDate] = dateRange.value;
    const params = {
      startDate,
      endDate,
      type: selectedType.value === 'all' ? undefined : selectedType.value,
      page: currentPage.value,
      limit: itemsPerPage.value
    };

    const response = await getCourses(params);
    courses.value = response.data;
    totalItems.value = response.total;
  } catch (err) {
    error.value = '获取课程列表失败，请稍后重试';
    console.error(err);
  } finally {
    loading.value = false;
  }
};