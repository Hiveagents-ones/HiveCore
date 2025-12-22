<template>
  <div class="coach-schedule-container">
    <h1>{{ $t('coachSchedule.title') }}</h1>
    
    <div class="action-buttons">
      <button @click="handlePrevWeek" class="btn">{{ $t('coachSchedule.prevWeek') }}</button>
      <span class="current-week">{{ currentWeekRange }}</span>
      <button @click="handleNextWeek" class="btn">{{ $t('coachSchedule.nextWeek') }}</button>
      <button @click="showAddDialog = true" class="btn btn-primary">{{ $t('coachSchedule.addSchedule') }}</button>
    </div>
    
    <div class="calendar-container">
      <table class="schedule-table">
        <thead>
          <tr>
            <th>时间</th>
            <th v-for="day in weekDays" :key="day.date">{{ day.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="timeSlot in timeSlots" :key="timeSlot">
            <td class="time-slot">{{ timeSlot }}</td>
            <td 
              v-for="day in weekDays" 
              :key="`${day.date}-${timeSlot}`"
              @click="handleCellClick(day.date, timeSlot)"
              :class="{ 'available': isAvailable(day.date, timeSlot), 'booked': isBooked(day.date, timeSlot) }"
            >
              {{ getScheduleInfo(day.date, timeSlot) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 添加排班对话框 -->
    <div v-if="showAddDialog" class="dialog-overlay">
      <div class="dialog-content">
        <h2>{{ $t('coachSchedule.addNewSchedule') }}</h2>
        <div class="form-group">
          <div v-if="conflictError" class="error-message">{{ conflictError }}</div>
          <label>日期</label>
          <input type="date" v-model="newSchedule.date" required>
        </div>
        <div class="form-group">
          <label>开始时间</label>
          <input type="time" v-model="newSchedule.startTime" required>
        </div>
        <div class="form-group">
          <label>结束时间</label>
          <input type="time" v-model="newSchedule.endTime" required>
        </div>
        <div class="dialog-actions">
          <button @click="showAddDialog = false" class="btn">取消</button>
          <button @click="handleAddSchedule" class="btn btn-primary">保存</button>
          <button @click="exportSchedule" class="btn btn-export">导出排班表</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { getCoachSchedules, createCoachSchedule, updateCoachSchedule, deleteCoachSchedule } from '../api/coaches';
import { checkScheduleConflict } from '../api/coaches';

// 当前周
const currentWeekStart = ref(new Date());

// 排班数据
const schedules = ref([]);

// 添加排班对话框状态
const showAddDialog = ref(false);
const conflictError = ref('');
const exportLoading = ref(false);
const chunkSize = 100; // 分块处理大小
const newSchedule = ref({
  date: '',
  startTime: '',
  endTime: ''
});

// 时间槽
const timeSlots = [
  '08:00', '09:00', '10:00', '11:00',
  '12:00', '13:00', '14:00', '15:00',
  '16:00', '17:00', '18:00', '19:00',
  '20:00'
];

// 计算当前周的范围
const currentWeekRange = computed(() => {
  const start = new Date(currentWeekStart.value);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  
  return `${formatDate(start)} 至 ${formatDate(end)}`;
});

// 计算一周的日期
const weekDays = computed(() => {
  const days = [];
  const start = new Date(currentWeekStart.value);
  
  for (let i = 0; i < 7; i++) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    
    days.push({
      date: date.toISOString().split('T')[0],
      label: `${formatWeekday(date)} ${date.getDate()}日`
    });
  }
  
  return days;
});

// 格式化日期
const formatDate = (date) => {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
};

// 格式化星期
const formatWeekday = (date) => {
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  return `周${weekdays[date.getDay()]}`;
};

// 检查时间段是否可用
const isAvailable = (date, timeSlot) => {
  const chunks = [];
  
  // 分块处理数据
  for (let i = 0; i < schedules.value.length; i += chunkSize) {
    const chunk = schedules.value.slice(i, i + chunkSize);
    chunks.push(chunk);
  }
  
  // 检查每个分块
  for (const chunk of chunks) {
    if (chunk.some(schedule => 
      schedule.date === date && 
    schedule.startTime <= timeSlot && 
    schedule.endTime > timeSlot &&
    schedule.available
  );
};

// 检查时间段是否已预约
const isBooked = (date, timeSlot) => {
  return schedules.value.some(schedule => 
    schedule.date === date && 
    schedule.start_time <= timeSlot && 
    schedule.end_time > timeSlot &&
    !schedule.available
  );
};

// 获取排班信息
const getScheduleInfo = (date, timeSlot) => {
  const chunks = [];
  
  // 分块处理数据
  for (let i = 0; i < schedules.value.length; i += chunkSize) {
    const chunk = schedules.value.slice(i, i + chunkSize);
    chunks.push(chunk);
  }
  
  // 检查每个分块
  for (const chunk of chunks) {
    const schedule = chunk.find(s => 
      s.date === date && 
    s.startTime <= timeSlot && 
    s.endTime > timeSlot
  );
  
  return schedule ? (schedule.available ? '可预约' : '已预约') : '';
};

// 处理单元格点击
const handleCellClick = (date, timeSlot) => {
  const schedule = schedules.value.find(s => 
    s.date === date && 
    s.startTime <= timeSlot && 
    s.endTime > timeSlot
  );
  
  if (schedule) {
    if (confirm(schedule.available ? '确定要标记为已预约吗？' : '确定要标记为可预约吗？')) {
      updateScheduleStatus(schedule.id, !schedule.available);
    }
  }
};

// 上一周
const handlePrevWeek = () => {
  const newDate = new Date(currentWeekStart.value);
  newDate.setDate(newDate.getDate() - 7);
  currentWeekStart.value = newDate;
  fetchSchedules();
};

// 下一周
const handleNextWeek = () => {
  const newDate = new Date(currentWeekStart.value);
  newDate.setDate(newDate.getDate() + 7);
  currentWeekStart.value = newDate;
  fetchSchedules();
};

// 添加排班
const handleAddSchedule = async () => {
  conflictError.value = '';
  try {
    const conflict = await checkScheduleConflict({
      date: newSchedule.value.date,
      startTime: newSchedule.value.startTime,
      endTime: newSchedule.value.endTime
    });

    if (conflict.hasConflict) {
      conflictError.value = conflict.message;
      return;
    }
  try {
    await createCoachSchedule({
      date: newSchedule.value.date,
      startTime: newSchedule.value.startTime,
      endTime: newSchedule.value.endTime,
      available: true
    });
    
    showAddDialog.value = false;
    resetNewSchedule();
    fetchSchedules();
  } catch (error) {
    console.error('添加排班失败:', error);
    alert('添加排班失败，请重试');
  }
};

// 更新排班状态
const updateScheduleStatus = async (scheduleId, available) => {
// 导出排班表
const exportSchedule = () => {
  exportLoading.value = true;
  
  // 使用虚拟滚动优化大数据量导出
  const chunkSize = 1000;
  const chunks = [];
  
  // 分块处理数据
  for (let i = 0; i < schedules.value.length; i += chunkSize) {
    const chunk = schedules.value.slice(i, i + chunkSize);
    chunks.push(chunk);
  }
  
  // 生成CSV头部
  let csvContent = '日期,开始时间,结束时间,状态\n';
  
  // 分块生成CSV内容
  chunks.forEach(chunk => {
    chunk.forEach(schedule => {
      csvContent += `${schedule.date},${schedule.startTime},${schedule.endTime},${schedule.available ? '可预约' : '已预约'}\n`;
    });
  });
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `排班表_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  exportLoading.value = false;
};
  try {
    await updateCoachSchedule(scheduleId, { available });
    fetchSchedules();
  } catch (error) {
    console.error('更新排班状态失败:', error);
    alert('更新排班状态失败，请重试');
  }
};

// 重置新排班表单
const resetNewSchedule = () => {
  newSchedule.value = {
    date: '',
    startTime: '',
    endTime: ''
  };
};

// 获取排班数据
const fetchSchedules = async () => {
  try {
    const startDate = new Date(currentWeekStart.value);
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + 6);
    
    const response = await getCoachSchedules({
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0]
    });
    
    schedules.value = response.data || [];
  } catch (error) {
    console.error('获取排班数据失败:', error);
  }
};

// 初始化
onMounted(() => {
  // 设置当前周为本周一
  const today = new Date();
  const dayOfWeek = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  currentWeekStart.value = monday;
  
  // 获取排班数据
  fetchSchedules();
});
</script>

<style scoped>
.coach-schedule-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
}

.btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #fff;
  cursor: pointer;
  transition: all 0.3s;
}

.btn:hover {
  background-color: #f5f5f5;
}

.btn-primary {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

.btn-primary:hover {
  background-color: #40a9ff;
}

.btn-export {
  background-color: #52c41a;
  color: white;
  border-color: #52c41a;
}

.btn-export:hover {
  background-color: #73d13d;
}

.error-message {
  color: #f5222d;
  margin-top: 5px;
  font-size: 14px;
}
  background-color: #40a9ff;
}

.current-week {
  font-weight: bold;
  margin: 0 10px;
}

.calendar-container {
  overflow-x: auto;
}

.schedule-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.schedule-table th, .schedule-table td {
  border: 1px solid #ddd;
  padding: 10px;
  text-align: center;
}

.schedule-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.time-slot {
  background-color: #f5f5f5;
  font-weight: bold;
}

.available {
  background-color: #e6f7ff;
  cursor: pointer;
}

.booked {
  background-color: #fff1f0;
  cursor: pointer;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.dialog-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  max-width: 90%;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const handleAddSchedule = async () => {
  conflictError.value = '';
  
  // 验证必填字段
  if (!newSchedule.value.date || !newSchedule.value.startTime || !newSchedule.value.endTime) {
    conflictError.value = this.$t('coachSchedule.requiredFields');
    return;
  }
  
  // 验证时间顺序
  if (newSchedule.value.startTime >= newSchedule.value.endTime) {
    conflictError.value = this.$t('coachSchedule.invalidTimeRange');
    return;
  }
  
  try {
    const conflict = await checkScheduleConflict({
      date: newSchedule.value.date,
      start_time: newSchedule.value.startTime,
      end_time: newSchedule.value.endTime
    });

# [AUTO-APPENDED] Failed to replace, adding new code:
const exportSchedule = () => {
  // 生成CSV内容
  let csvContent = '日期,开始时间,结束时间\n';
  
  schedules.value.forEach(schedule => {
    csvContent += `${schedule.date},${schedule.startTime},${schedule.endTime}\n`;
  });
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${this.$t('coachSchedule.scheduleExport')}_${new Date().toISOString().slice(0, 10)}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const handleAddSchedule = async () => {
  conflictError.value = '';
  
  // 验证必填字段
  if (!newSchedule.value.date || !newSchedule.value.startTime || !newSchedule.value.endTime) {
    conflictError.value = '请填写所有必填字段';
    return;
  }

  // 验证时间顺序
  if (newSchedule.value.startTime >= newSchedule.value.endTime) {
    conflictError.value = '结束时间必须晚于开始时间';
    return;
  }

  try {
    const conflict = await checkScheduleConflict({
      date: newSchedule.value.date,
      start_time: newSchedule.value.startTime,
      end_time: newSchedule.value.endTime
    });

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const handleAddSchedule = async () => {
  conflictError.value = '';

  // 验证必填字段
  if (!newSchedule.value.date || !newSchedule.value.startTime || !newSchedule.value.endTime) {
    conflictError.value = this.$t('coachSchedule.requiredFields');
    return;
  }

  // 验证时间顺序
  if (newSchedule.value.startTime >= newSchedule.value.endTime) {
    conflictError.value = this.$t('coachSchedule.invalidTimeRange');
    return;
  }

  try {
    const conflict = await checkScheduleConflict({
      date: newSchedule.value.date,
      start_time: newSchedule.value.startTime,
      end_time: newSchedule.value.endTime
    });

# [AUTO-APPENDED] Failed to insert:

// 导出排班表
const exportSchedule = () => {
  exportLoading.value = true;
  
  // 生成CSV内容
  let csvContent = `${this.$t('coachSchedule.date')},${this.$t('coachSchedule.startTime')},${this.$t('coachSchedule.endTime')}\n`;

  schedules.value.forEach(schedule => {
    csvContent += `${schedule.date},${schedule.startTime},${schedule.endTime}\n`;
  });

  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${this.$t('coachSchedule.scheduleExport')}_${new Date().toISOString().slice(0, 10)}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  exportLoading.value = false;
};