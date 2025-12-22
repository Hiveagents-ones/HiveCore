<template>
  <div class="leave-request-container">
    <h2>请假申请</h2>
    <form @submit.prevent="submitLeaveRequest">
      <div class="form-group">
        <label for="startDate">开始日期</label>
        <input 
          type="date" 
          id="startDate" 
          v-model="leaveRequest.start_date" 
          required
          :min="minDate"
        />
    </div>
      
      <div class="form-group">
        <label for="endDate">结束日期</label>
        <input 
          type="date" 
          id="endDate" 
          v-model="leaveRequest.end_date" 
          required
          :min="leaveRequest.start_date || minDate"
        />
      </div>
      
      <div class="form-group">
        <label for="reason">请假原因</label>
        <textarea 
          id="reason" 
          v-model="leaveRequest.reason" 
          rows="3" 
          required
        ></textarea>
      </div>
      
      <button type="submit" class="submit-btn">提交申请</button>
    </form>
    
    <div v-if="message" class="message" :class="{ 'success': isSuccess, 'error': !isSuccess }">
      {{ message }}
    </div>
    </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useStore } from 'vuex';
import { submitCoachLeaveRequest } from '../api/coaches';

export default {
  name: 'CoachLeaveRequest',
  
  setup() {
    const store = useStore();
    const leaveRequest = ref({
      coach_id: null,
      start_date: '',
      end_date: '',
      reason: ''
    });
    
    const message = ref('');
    const isSuccess = ref(false);
    
    const minDate = computed(() => {
      const today = new Date();
      return today.toISOString().split('T')[0];
    });
    
    const submitLeaveRequest = async () => {
      try {
        // Get coach_id from store
        leaveRequest.value.coach_id = store.state.user.id;
        
        const response = await submitCoachLeaveRequest(leaveRequest.value);
        
        if (response.success) {
          message.value = '请假申请提交成功！';
          isSuccess.value = true;
          // Reset form
          leaveRequest.value = {
            coach_id: null,
            start_date: '',
            end_date: '',
            reason: ''
          };
        } else {
          message.value = response.message || '提交失败，请重试';
          isSuccess.value = false;
        }
      } catch (error) {
        console.error('Error submitting leave request:', error);
        message.value = '系统错误，请稍后再试';
        isSuccess.value = false;
      }
      
      // Clear message after 5 seconds
      setTimeout(() => {
        message.value = '';
      }, 5000);
    };
    
    return {
      leaveRequest,
      message,
      isSuccess,
      minDate,
      submitLeaveRequest
    };
  }
};
</script>

<style scoped>
.leave-request-container {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input[type="date"],
textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

textarea {
  resize: vertical;
}

.submit-btn {
  width: 100%;
  padding: 10px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.submit-btn:hover {
  background-color: #45a049;
}

.message {
  margin-top: 15px;
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