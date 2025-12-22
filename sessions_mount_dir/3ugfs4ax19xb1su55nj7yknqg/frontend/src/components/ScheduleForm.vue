<template>
  <div class="schedule-form">
    <h2>教练排班</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="coach">教练</label>
        <select id="coach" v-model="formData.coach_id" required>
          <option v-for="coach in coaches" :key="coach.id" :value="coach.id">
            {{ coach.name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label for="day">星期</label>
        <select id="day" v-model="formData.day_of_week" required>
          <option value="1">星期一</option>
          <option value="2">星期二</option>
          <option value="3">星期三</option>
          <option value="4">星期四</option>
          <option value="5">星期五</option>
          <option value="6">星期六</option>
          <option value="7">星期日</option>
        </select>
      </div>

      <div class="form-group">
        <label for="start">开始时间</label>
        <input 
          type="time" 
          id="start" 
          v-model="formData.start_hour" 
          required
        />
      </div>

      <div class="form-group">
        <label for="end">结束时间</label>
        <input 
          type="time" 
          id="end" 
          v-model="formData.end_hour" 
          required
        />
      </div>

      <button type="submit" class="submit-btn">提交</button>
    </form>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getCoaches, createSchedule } from '../api/schedules';

export default {
  name: 'ScheduleForm',
  emits: ['schedule-created'],
  setup(props, { emit }) {
    const coaches = ref([]);
    const formData = ref({
      coach_id: '',
      day_of_week: '',
      start_hour: '',
      end_hour: ''
    });

    const fetchCoaches = async () => {
      try {
        const response = await getCoaches();
        coaches.value = response.data;
      } catch (error) {
        console.error('获取教练列表失败:', error);
      }
    };

    const submitForm = async () => {
      try {
        await createSchedule(formData.value);
        emit('schedule-created');
        resetForm();
      } catch (error) {
        console.error('创建排班失败:', error);
      }
    };

    const resetForm = () => {
      formData.value = {
        coach_id: '',
        day_of_week: '',
        start_hour: '',
        end_hour: ''
      };
    };

    onMounted(() => {
      fetchCoaches();
    });

    return {
      coaches,
      formData,
      submitForm
    };
  }
};
</script>

<style scoped>
.schedule-form {
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

select, input[type="time"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
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
  margin-top: 10px;
}

.submit-btn:hover {
  background-color: #45a049;
}
</style>