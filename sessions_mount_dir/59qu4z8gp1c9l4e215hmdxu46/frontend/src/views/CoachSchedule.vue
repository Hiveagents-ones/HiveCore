<template>
  <div class="coach-schedule-container">
    <h1>教练排班管理</h1>
    <div class="timezone-info">当前时区: {{ timezone }}</div>
    <div class="timezone-selector">
      <el-select v-model="timezone" placeholder="选择时区">
        <el-option
          v-for="tz in timezoneOptions"
          :key="tz.value"
          :label="tz.label"
          :value="tz.value"
        />
      </el-select>
    </div>
    
    <div class="coach-selector">
      <el-select 
        v-model="selectedCoachId" 
        placeholder="请选择教练"
        @change="fetchCoachSchedules"
      >
        <el-option
          v-for="coach in coaches"
          :key="coach.id"
          :label="coach.name"
          :value="coach.id"
        />
      </el-select>
    </div>
    
    <div class="schedule-calendar">
      <el-calendar v-model="currentDate">
        <template #dateCell="{ data }">
          <div class="calendar-day">
            <div class="day-header">{{ data.day.split('-').slice(2).join('-') }}</div>
            <div 
              v-for="schedule in getSchedulesForDate(data.day)" 
              :key="schedule.id"
              class="schedule-item"
            >
              {{ formatTime(schedule.start_time) }} - {{ formatTime(schedule.end_time) }}
              <el-button 
                size="mini" 
                type="danger" 
                @click="deleteSchedule(schedule.id)"
              >
                删除
              </el-button>
            </div>
            <el-button 
              v-if="selectedCoachId" 
              size="mini" 
              type="primary" 
              @click="showAddDialog(data.day)"
            >
              添加排班
            </el-button>
          </div>
        </template>
      </el-calendar>
    </div>
    
    <el-dialog 
      v-model="dialogVisible" 
      title="添加排班"
      width="30%"
    >
      <el-form :model="newSchedule">
        <el-form-item label="开始时间">
          <el-time-picker 
            v-model="newSchedule.start_time" 
            format="HH:mm" 
            value-format="HH:mm"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker 
            v-model="newSchedule.end_time" 
            format="HH:mm" 
            value-format="HH:mm"
          />
          <el-alert
            v-if="conflictMessage"
            :title="conflictMessage"
            type="error"
            show-icon
            :closable="false"
            style="margin-top: 10px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addSchedule">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getCoaches, getCoachSchedules, createCoachSchedule, deleteCoachSchedule, getCoachAvailability } from '@/api/coaches';
import { ElMessage } from 'element-plus';
import { watch } from 'vue';

export default {
  name: 'CoachSchedule',
  setup() {
    const coaches = ref([]);
    const selectedCoachId = ref(null);
    const schedules = ref([]);
    const currentDate = ref(new Date());
    const dialogVisible = ref(false);
    const selectedDate = ref('');
    
    const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai');
watch(timezone, (newVal) => {
  if (selectedCoachId.value) {
    fetchCoachSchedules();
  }
});
    const conflictMessage = ref('');
const timezoneOptions = [
  { value: 'Asia/Shanghai', label: '上海时间 (UTC+8)' },
  { value: 'America/New_York', label: '纽约时间 (UTC-5)' },
  { value: 'Europe/London', label: '伦敦时间 (UTC+0)' },
  { value: 'America/Los_Angeles', label: '洛杉矶时间 (UTC-8)' },
  { value: 'Australia/Sydney', label: '悉尼时间 (UTC+10)' },
  { value: 'Asia/Tokyo', label: '东京时间 (UTC+9)' }
];
    const newSchedule = ref({
      start_time: '',
      end_time: ''
    });

    const fetchCoaches = async () => {
      try {
        const response = await getCoaches();
        coaches.value = response.data;
      } catch (error) {
        ElMessage.error('获取教练列表失败');
      }
    };

    const fetchCoachSchedules = async () => {
  // 每次获取排班时带上当前时区
  const params = {
    timezone: timezone.value
  };
      if (!selectedCoachId.value) return;
      
      try {
        const response = await getCoachSchedules(selectedCoachId.value, params);
        schedules.value = response.data;
      } catch (error) {
        ElMessage.error('获取排班信息失败');
      }
    };

    const getSchedulesForDate = (date) => {
      return schedules.value.filter(schedule => {
        return schedule.date === date;
      });
    };

    const formatTime = (timeStr) => {
      if (!timeStr) return '';
      return timeStr.slice(0, 5);
    };

    const showAddDialog = (date) => {
      selectedDate.value = date;
      newSchedule.value = { start_time: '', end_time: '' };
      dialogVisible.value = true;
    };

    const addSchedule = async () => {
      // 检查时间冲突
      try {
        const availability = await getCoachAvailability(selectedCoachId.value, selectedDate.value);
        const newStart = newSchedule.value.start_time;
        const newEnd = newSchedule.value.end_time;
        
        const hasConflict = availability.data.some(slot => {
          return (newStart >= slot.start_time && newStart < slot.end_time) ||
                 (newEnd > slot.start_time && newEnd <= slot.end_time) ||
                 (newStart <= slot.start_time && newEnd >= slot.end_time);
        });
        
        if (hasConflict) {
          conflictMessage.value = '该时间段与现有排班冲突';
        } else {
          conflictMessage.value = '';
        }
        
        if (hasConflict) {
          ElMessage.warning('该时间段与现有排班冲突');
          return;
        }
      } catch (error) {
        ElMessage.error('检查排班冲突失败');

      }


      if (newSchedule.value.start_time >= newSchedule.value.end_time) {
        ElMessage.warning('结束时间必须晚于开始时间');
        return;
      }
      if (!newSchedule.value.start_time || !newSchedule.value.end_time) {
        ElMessage.warning('请填写完整的时间');
        return;
      }
      
      try {
        const scheduleData = {
          date: selectedDate.value,
          start_time: newSchedule.value.start_time,
          end_time: newSchedule.value.end_time,
          timezone: timezone.value
        };
        
        await createCoachSchedule(selectedCoachId.value, scheduleData);
        ElMessage.success('添加排班成功');
        dialogVisible.value = false;
        fetchCoachSchedules();
      } catch (error) {
        ElMessage.error('添加排班失败');
      }
    };

    const deleteSchedule = async (scheduleId) => {
      if (!confirm('确定要删除这个排班吗？')) {
        return;
      }
      try {
        await deleteCoachSchedule(selectedCoachId.value, scheduleId);
        ElMessage.success('删除排班成功');
        fetchCoachSchedules();
      } catch (error) {
        ElMessage.error('删除排班失败');
      }
    };

    onMounted(() => {
      fetchCoaches();
    });

    return {
      timezone,
      coaches,
      selectedCoachId,
      schedules,
      currentDate,
      dialogVisible,
      newSchedule,
      fetchCoachSchedules,
      getSchedulesForDate,
      formatTime,
      showAddDialog,
      addSchedule,
      deleteSchedule
    };
  }
};
</script>

<style scoped>
.coach-schedule-container {
  padding: 20px;

  max-width: 1200px;
  margin: 0 auto;
}

.timezone-info {
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: inline-block;
  margin: 15px 0;
  color: #666;
  font-size: 14px;
}
}

.coach-selector {

.timezone-selector {
  margin-left: 15px;
  width: 250px;
}
  margin-bottom: 20px;
  width: 300px;
}

.timezone-selector {
  margin-left: 15px;
  width: 250px;
}

.calendar-day {
  height: 100%;
  padding: 5px;
  box-sizing: border-box;
}

.day-header {
  font-weight: bold;
  margin-bottom: 5px;
}

.schedule-item {
  font-size: 12px;
  margin: 3px 0;
  padding: 3px;
  background-color: #f5f7fa;
  border-radius: 3px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>