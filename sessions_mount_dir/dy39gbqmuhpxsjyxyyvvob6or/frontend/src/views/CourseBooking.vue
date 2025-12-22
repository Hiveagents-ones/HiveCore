<template>
  <div class="course-booking">
    <h1>{{ t('courseBooking.title') }}</h1>
    
      <div class="confirmation" v-if="currentStep === 3">
        <h3>{{ t('courseBooking.confirmationTitle') }}</h3>
        <div class="confirmation-details">
          <p><strong>{{ t('courseBooking.courseName') }}:</strong> {{ course.name }}</p>
          <p><strong>{{ t('courseBooking.courseTime') }}:</strong> {{ formatDateTime(course.start_time) }} - {{ formatDateTime(course.end_time) }}</p>
          <p><strong>{{ t('courseBooking.memberId') }}:</strong> {{ bookingData.member_id }}</p>
          <p><strong>{{ t('courseBooking.notes') }}:</strong> {{ bookingData.notes || t('courseBooking.noNotes') }}</p>
        </div>
        <button 
          type="button" 
          class="submit-btn"
          @click="handleSubmit"
        >
          {{ t('courseBooking.confirmBooking') }}
        </button>
        <button 
          type="button" 
          class="prev-btn"
          @click="currentStep--"
        >
          {{ t('courseBooking.backToEdit') }}
        </button>
      </div>
    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    
    <div v-else>
      <div class="steps">
        <div class="step" :class="{ active: currentStep === 1 }">1. {{ t('courseBooking.step1') }}</div>
        <div class="step" :class="{ active: currentStep === 2 }">2. {{ t('courseBooking.step2') }}</div>
        <div class="step" :class="{ active: currentStep === 3 }">3. {{ t('courseBooking.step3') }}</div>
      </div>

      <div class="course-details" v-if="course && currentStep === 1">
        <h2>{{ course.name }}</h2>
        <p>{{ course.description }}</p>
        <p>{{ t('courseBooking.time') }}: {{ formatDateTime(course.start_time) }} - {{ formatDateTime(course.end_time) }}</p>
      </div>
      
      <div class="booking-form" v-if="currentStep === 2">
        <h3>{{ t('courseBooking.bookingInfo') }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="memberId">{{ t('courseBooking.memberId') }}</label>
            <input 
              type="number" 
              id="memberId" 
              v-model="bookingData.member_id" 
              required
            />
          </div>
          
          <div class="form-group">
            <label for="notes">{{ t('courseBooking.notes') }}</label>
            <textarea 
              id="notes" 
              v-model="bookingData.notes" 
              :placeholder="t('courseBooking.notesPlaceholder')"
            ></textarea>
          </div>
          
          <button type="submit" class="submit-btn">
            {{ isEditing ? t('courseBooking.updateBooking') : t('courseBooking.submitBooking') }}
          </button>
          
          <button 
            v-if="isEditing" 
            type="button" 
            class="cancel-btn"
            @click="handleCancelBooking"
          >
            {{ t('courseBooking.cancelBooking') }}
          </button>
        </form>
      </div>
    </div>
    
    <div v-if="message" class="message" :class="{ success: isSuccess, error: !isSuccess }">
    <div v-if="conflictDetected" class="conflict-warning">
      <p>{{ t('courseBooking.conflictWarning') }}</p>
      <button @click="fetchCourse">{{ t('courseBooking.refreshData') }}</button>
    </div>
    <div v-if="conflictDetected" class="conflict-warning">
      <p>{{ t('courseBooking.conflictWarning') }}</p>
      <button @click="fetchCourse">{{ t('courseBooking.refreshData') }}</button>
    </div>
      {{ message }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { 
  getCourseById, 
  createCourseBooking, 
  updateCourseBooking, 
  cancelCourseBooking 
} from '../api/courses';

export default {
  name: 'CourseBooking',
  setup() {
    const route = useRoute();
    const router = useRouter();
    
    const courseId = route.params.id;
    const isEditing = route.query.edit === 'true';
    
    const course = ref(null);
    const loading = ref(true);
    const message = ref('');
    const isSuccess = ref(false);
const { t } = useI18n();
    const currentStep = ref(1);
const lastUpdated = ref(null);
    const conflictDetected = ref(false);
    
    const bookingData = ref({
      member_id: '',
      notes: ''
    });
    
    const formatDateTime = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleString();
    };
    
    const fetchCourse = async () => {
      try {
        const data = await getCourseById(courseId);
        course.value = data;
        
        if (isEditing) {
          bookingData.value.member_id = data.member_id || '';
          bookingData.value.notes = data.notes || '';
        }
      } catch (error) {
        console.error('Failed to fetch course:', error);
        message.value = t('errors.fetchCourseFailed');
        isSuccess.value = false;
      } finally {
        loading.value = false;
      }
    };
    
    const handleSubmit = async () => {
      try {
        if (isEditing) {
          await updateCourseBooking(courseId, bookingData.value);
          message.value = t('messages.bookingUpdated');
        } else {
          await createCourseBooking({
            ...bookingData.value,
            course_id: courseId
          });
          message.value = t('messages.bookingCreated');
        }
        isSuccess.value = true;
        
        // 3秒后返回课程列表
        setTimeout(() => {
          router.push('/courses');
        }, 3000);
      } catch (error) {
        console.error('Booking failed:', error);
        message.value = isEditing ? t('errors.bookingUpdateFailed') : t('errors.bookingCreateFailed');
        isSuccess.value = false;
      }
    };
    
    const handleCancelBooking = async () => {
      try {
        await cancelCourseBooking(courseId);
        message.value = t('messages.bookingCancelled');
        isSuccess.value = true;
        
        // 3秒后返回课程列表
        setTimeout(() => {
          router.push('/courses');
        }, 3000);
      } catch (error) {
        console.error('Cancel booking failed:', error);
        message.value = t('errors.bookingCancelFailed');
        isSuccess.value = false;
      }
    };
    
    onMounted(() => {
      fetchCourse();
    });
    
    return {
      course,
      loading,
      bookingData,
      message,
      isSuccess,
      isEditing,
      formatDateTime,
      handleSubmit,
      handleCancelBooking
    };
  }
};
</script>

<style scoped>
.course-booking {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.loading {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.course-details {
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.booking-form {
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

input, textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

textarea {
  min-height: 100px;
}

button {
  padding: 10px 20px;
  margin-right: 10px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
}

.submit-btn {
  background-color: #4CAF50;
  color: white;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
}

.message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 4px;
  text-align: center;
}

.success {
  background-color: #dff0d8;
  color: #3c763d;
}

.error {
  background-color: #f2dede;
  color: #a94442;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
          <button 
            type="button" 
            class="prev-btn"
            @click="currentStep--"
          >
            上一步
          </button>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
        console.error('Fetch course failed:', error);
        if (error.response && error.response.status === 409) {
          conflictDetected.value = true;
        } else {
          message.value = t('errors.courseFetchFailed');
          isSuccess.value = false;
        }