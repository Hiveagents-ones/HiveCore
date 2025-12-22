<template>
  <div class="booking-form">
    <el-form
      ref="bookingFormRef"
      :model="bookingForm"
      :rules="rules"
      label-width="100px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="预约时间" prop="bookingTime">
        <el-date-picker
          v-model="bookingForm.bookingTime"
          type="datetime"
          placeholder="选择预约时间"
          :disabled-date="disabledDate"
          :disabled-hours="disabledHours"
          :disabled-minutes="disabledMinutes"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DD HH:mm:ss"
        />
      </el-form-item>

      <el-form-item label="备注" prop="notes">
        <el-input
          v-model="bookingForm.notes"
          type="textarea"
          :rows="3"
          placeholder="请输入备注信息（选填）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ loading ? '预约中...' : '确认预约' }}
        </el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 错误提示 -->
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      show-icon
      class="mt-3"
    />

    <!-- 重试按钮 -->
    <div v-if="showRetry" class="retry-container mt-3">
      <el-button
        type="warning"
        :loading="retrying"
        @click="handleRetry"
      >
        {{ retrying ? '重试中...' : '重试' }}
      </el-button>
      <span class="retry-hint">网络异常，请重试</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { courseApi } from '../services/api';

// Props
const props = defineProps({
  courseId: {
    type: [String, Number],
    required: true,
  },
  courseInfo: {
    type: Object,
    default: () => ({}),
  },
});

// Emits
const emit = defineEmits(['success', 'cancel']);

// 表单引用
const bookingFormRef = ref(null);

// 表单数据
const bookingForm = reactive({
  bookingTime: '',
  notes: '',
});

// 表单验证规则
const rules = {
  bookingTime: [
    { required: true, message: '请选择预约时间', trigger: 'change' },
    { validator: validateBookingTime, trigger: 'change' },
  ],
};

// 状态
const loading = ref(false);
const retrying = ref(false);
const errorMessage = ref('');
const showRetry = ref(false);
const retryCount = ref(0);
const maxRetries = 3;

// 验证预约时间
function validateBookingTime(rule, value, callback) {
  if (!value) {
    callback(new Error('请选择预约时间'));
    return;
  }

  const selectedTime = new Date(value);
  const now = new Date();
  const minTime = new Date(now.getTime() + 2 * 60 * 60 * 1000); // 至少提前2小时

  if (selectedTime < minTime) {
    callback(new Error('预约时间至少需要提前2小时'));
    return;
  }

  // 检查是否在课程营业时间内
  if (props.courseInfo.businessHours) {
    const { start, end } = props.courseInfo.businessHours;
    const hour = selectedTime.getHours();
    if (hour < start || hour > end) {
      callback(new Error(`预约时间需要在营业时间 ${start}:00 - ${end}:00 之间`));
      return;
    }
  }

  callback();
}

// 禁用过去的日期
function disabledDate(time) {
  const now = new Date();
  const minDate = new Date(now.getTime() + 2 * 60 * 60 * 1000);
  return time.getTime() < minDate.getTime();
}

// 禁用的小时
function disabledHours() {
  if (!props.courseInfo.businessHours) {
    return [];
  }
  const hours = [];
  const { start, end } = props.courseInfo.businessHours;
  for (let i = 0; i < 24; i++) {
    if (i < start || i > end) {
      hours.push(i);
    }
  }
  return hours;
}

// 禁用的分钟
function disabledMinutes(hour) {
  if (!props.courseInfo.businessHours) {
    return [];
  }
  const minutes = [];
  const { start, end } = props.courseInfo.businessHours;
  
  // 营业开始和结束时间的前后30分钟不可选
  if (hour === start) {
    for (let i = 0; i < 30; i++) {
      minutes.push(i);
    }
  }
  if (hour === end) {
    for (let i = 31; i < 60; i++) {
      minutes.push(i);
    }
  }
  
  return minutes;
}

// 提交表单
async function handleSubmit() {
  try {
    // 清除错误信息
    errorMessage.value = '';
    showRetry.value = false;

    // 表单验证
    const valid = await bookingFormRef.value.validate();
    if (!valid) {
      return;
    }

    loading.value = true;
    retryCount.value = 0;

    // 调用预约API
    await bookCourse();
  } catch (error) {
    console.error('预约失败:', error);
    handleError(error);
  } finally {
    loading.value = false;
  }
}

// 执行预约
async function bookCourse() {
  const bookingData = {
    booking_time: bookingForm.bookingTime,
    notes: bookingForm.notes,
  };

  const response = await courseApi.bookCourse(props.courseId, bookingData);
  
  // 预约成功
  ElMessage.success('预约成功！');
  emit('success', response);
  handleReset();
}

// 处理错误
function handleError(error) {
  if (error.response) {
    // 服务器返回的错误
    const { status, data } = error.response;
    
    if (status === 422) {
      // 表单验证错误
      const errors = data.detail;
      if (Array.isArray(errors)) {
        const fieldErrors = {};
        errors.forEach(err => {
          if (err.loc && err.loc.length > 1) {
            const field = err.loc[1];
            fieldErrors[field] = err.msg;
          }
        });
        
        // 设置表单字段错误
        bookingFormRef.value.setFields(fieldErrors);
        errorMessage.value = '请检查表单填写是否正确';
      } else {
        errorMessage.value = data.message || '预约失败，请重试';
      }
    } else if (status >= 500) {
      // 服务器错误，显示重试按钮
      showRetry.value = true;
      errorMessage.value = '服务器错误，请稍后重试';
    } else {
      errorMessage.value = data.message || '预约失败';
    }
  } else if (error.request) {
    // 网络错误
    showRetry.value = true;
    errorMessage.value = '网络连接失败，请检查网络后重试';
  } else {
    errorMessage.value = '预约失败，请重试';
  }
}

// 重试
async function handleRetry() {
  if (retryCount.value >= maxRetries) {
    ElMessage.warning(`已重试${maxRetries}次，请稍后再试或联系客服`);
    return;
  }

  try {
    retrying.value = true;
    retryCount.value++;
    errorMessage.value = '';
    showRetry.value = false;

    await bookCourse();
  } catch (error) {
    handleError(error);
  } finally {
    retrying.value = false;
  }
}

// 重置表单
function handleReset() {
  bookingFormRef.value?.resetFields();
  errorMessage.value = '';
  showRetry.value = false;
  retryCount.value = 0;
}

// 组件挂载时的初始化
onMounted(() => {
  // 可以在这里添加一些初始化逻辑
  // 例如：获取课程可用时间段等
});
</script>

<style scoped>
.booking-form {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
}

.retry-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.retry-hint {
  color: #909399;
  font-size: 14px;
}

.mt-3 {
  margin-top: 12px;
}
</style>