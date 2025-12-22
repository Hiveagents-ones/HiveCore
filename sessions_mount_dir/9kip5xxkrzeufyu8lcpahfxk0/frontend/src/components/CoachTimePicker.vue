<template>
  <div class="coach-time-picker">
    <div class="header">
      <h3>教练工作时间选择</h3>
      <p class="subtitle">请选择教练可工作的时间段</p>
      <v-btn color="primary" @click="saveSchedule">保存排班</v-btn>
    </div>
    
    <div class="date-selector">
      <v-date-picker
        v-model="selectedDate"
        :min="minDate"
        :max="maxDate"
        :allowed-dates="isWeekday"
        @input="fetchCoachSchedule"
        locale="zh-cn"
        :first-day-of-week="1"
      ></v-date-picker>
    </div>
    
    <div class="time-slots">
      <div v-for="(slot, index) in timeSlots" :key="index" class="time-slot">
        <v-checkbox
          v-model="selectedSlots"
          :value="slot.value"
          :label="slot.label"
          :disabled="isSlotDisabled(slot.value)"
          :class="slot.color"
          :color="existingSchedule.value.includes(slot.value) ? 'success' : 'primary'"
        ></v-checkbox>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useStore } from 'vuex';
import { getCoachSchedule, updateCoachSchedule } from '../api/coaches';

export default {
  name: 'CoachTimePicker',
  props: {
    coachId: {
      type: Number,
      required: true
    }
  },
  setup(props) {
    const store = useStore();
    const selectedDate = ref(new Date());
    const minDate = ref(new Date());
    const maxDate = ref(new Date());
    maxDate.value.setMonth(maxDate.value.getMonth() + 3);
    // 限制只能选择工作日（周一到周五）
    const isWeekday = (date) => {
      // 获取当前用户时区
      const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const day = date.getDay();
      return day !== 0 && day !== 6;
    };
    
    const isDateDisabled = (date) => !isWeekday(date);
    
    const timeSlots = ref([
      { label: '08:00 - 10:00', value: '08:00-10:00', color: 'morning' },
      { label: '10:00 - 12:00', value: '10:00-12:00', color: 'morning' },
      { label: '12:00 - 14:00', value: '12:00-14:00', color: 'afternoon' },
      { label: '14:00 - 16:00', value: '14:00-16:00', color: 'afternoon' },
      { label: '16:00 - 18:00', value: '16:00-18:00', color: 'evening' },
      { label: '18:00 - 20:00', value: '18:00-20:00', color: 'evening' },
      { label: '20:00 - 22:00', value: '20:00-22:00', color: 'night' }
    ]);
    
    const selectedSlots = ref([]);
    const existingSchedule = ref([]);
    
    const fetchCoachSchedule = async () => {
      try {
              // 根据用户时区格式化日期
      const dateStr = new Date(selectedDate.value.getTime() - (selectedDate.value.getTimezoneOffset() * 60000))
        .toISOString()
        .split('T')[0];
        const response = await getCoachSchedule(props.coachId, dateStr);
        existingSchedule.value = response.data.slots || [];
        selectedSlots.value = [...existingSchedule.value];
      } catch (error) {
        store.dispatch('showError', '获取排班信息失败');
      }
    };
    
    const saveSchedule = async () => {
      if (selectedSlots.value.length === 0) {
        store.dispatch('showError', '请至少选择一个时间段');
        return;
      }
      try {
        const dateStr = selectedDate.value.toISOString().split('T')[0];
        await updateCoachSchedule(props.coachId, {
          date: dateStr,
          slots: selectedSlots.value
        });
        store.dispatch('showSuccess', '排班信息保存成功');
        fetchCoachSchedule();
      // 获取节假日数据
      store.dispatch('fetchHolidays');
      } catch (error) {
        store.dispatch('showError', '保存排班信息失败');
      }
    };
    
    const isSlotDisabled = (slotValue) => {
      // 检查是否是节假日
      const holidays = store.state.holidays;
      const dateKey = selectedDate.value.toISOString().split('T')[0];
      if (holidays.includes(dateKey)) {
        return true;
      }
      // 禁用过去的时间段
      const now = new Date();
      const [startHour] = slotValue.split('-')[0].split(':');
      const slotDate = new Date(selectedDate.value);
      slotDate.setHours(Number(startHour));
      
      if (selectedDate.value.toDateString() === now.toDateString()) {
        return slotDate < now;
      }
      return false;
    };
    
    onMounted(() => {
      fetchCoachSchedule();
    });
    
    return {
      selectedDate,
      minDate,
      maxDate,
      timeSlots,
      selectedSlots,
      existingSchedule,
      fetchCoachSchedule,
      saveSchedule,
      isSlotDisabled
    };
  }
};
</script>

<style scoped>
.coach-time-picker {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.date-selector {
  margin-bottom: 20px;
}

.time-slots {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.time-slot {
  &.morning { background-color: rgba(255, 245, 157, 0.3); }
  &.afternoon { background-color: rgba(255, 204, 128, 0.3); }
  &.evening { background-color: rgba(179, 229, 252, 0.3); }
  &.night { background-color: rgba(206, 147, 216, 0.3); }

.subtitle {
  color: #666;
  font-size: 0.9rem;
  margin-top: 5px;
}
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 4px;
}
</style>