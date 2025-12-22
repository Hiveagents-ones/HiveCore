<template>
  <div class="course-schedule-container">
    <h1 class="page-title">课程预约</h1>
    
    <div class="schedule-form">
      <div class="form-group">
        <label for="schedule-date">选择时间</label>
        <el-date-picker
          v-model="selectedDateTime"
          type="datetime-local"
          id="schedule-date"
          :min-date="minDate"
          @change="checkConflict"
          placeholder="选择日期和时间"
          class="date-picker"
        />
      </div>

      <div class="form-group">
        <label for="party-size">预约人数</label>
        <el-input
          v-model.number="partySize"
          type="number"
          id="party-size"
          min="1"
          max="50"
          placeholder="1-50人"
          @change="validatePartySize"
          class="party-size-input"
        />
        <div v-if="sizeError" class="error-message">{{ sizeError }}</div>
      </div>

      <div v-if="conflictError" class="error-message">{{ conflictError }}</div>

      <el-button
        type="primary"
        @click="submitBooking"
        :disabled="isSubmitting || conflictError || sizeError"
        class="submit-btn"
      >
        {{ isSubmitting ? '提交中...' : '确认预约' }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import axios from 'axios';

const selectedDateTime = ref(null);
const partySize = ref(1);
const sizeError = ref('');
const conflictError = ref('');
const isSubmitting = ref(false);

const minDate = computed(() => {
  const now = new Date();
  now.setHours(now.getHours() + 1);
  return now.toISOString().slice(0, 16);
});

const validatePartySize = () => {
  if (partySize.value < 1) {
    sizeError.value = '人数至少为1';
  } else if (partySize.value > 50) {
    sizeError.value = '人数不能超过50';
  } else {
    sizeError.value = '';
  }
};

const checkConflict = async () => {
  if (!selectedDateTime.value) return;

  try {
    isSubmitting.value = true;
    conflictError.value = '';
    
    const response = await axios.get('/api/bookings/check', {
      params: {
        datetime: selectedDateTime.value,
        partySize: partySize.value
      }
    });

    if (response.data.conflict) {
      conflictError.value = '该时间段已有预约，请选择其他时间';
    }
  } catch (error) {
    conflictError.value = '检查冲突时出错，请重试';
    console.error('Conflict check error:', error);
  } finally {
    isSubmitting.value = false;
  }
};

const submitBooking = async () => {
  if (sizeError.value || conflictError.value) return;

  isSubmitting.value = true;
  try {
    const response = await axios.post('/api/bookings', {
      datetime: selectedDateTime.value,
      partySize: partySize.value
    });

    if (response.data.success) {
      ElMessage.success('预约成功！');
      // 重置表单
      selectedDateTime.value = null;
      partySize.value = 1;
    }
  } catch (error) {
    ElMessage.error('预约失败，请重试');
    console.error('Booking error:', error);
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  // 默认选择1小时后的时间
  const now = new Date();
  now.setHours(now.getHours() + 1);
  selectedDateTime.value = now.toISOString().slice(0, 16);
});
</script>

<style scoped>
.course-schedule-container {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.page-title {
  text-align: center;
  margin-bottom: 2rem;
  color: #333;
}

.schedule-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.date-picker {
  width: 100%;
}

.party-size-input {
  width: 100%;
}

.error-message {
  color: #e53935;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.submit-btn {
  width: 100%;
  padding: 0.75rem;
  font-weight: 600;
}
</style>