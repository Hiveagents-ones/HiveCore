<template>
  <div class="coach-schedule-view">
    <h1>教练排班管理</h1>
    
    <div class="controls">
      <div class="coach-selector">
        <label for="coach-select">选择教练：</label>
        <select id="coach-select" v-model="selectedCoachId" @change="fetchCoachSchedules">
          <option value="">全部教练</option>
          <option v-for="coach in coaches" :key="coach.id" :value="coach.id">
            {{ coach.name }}
          </option>
        </select>
      </div>
      
      <button @click="showAddScheduleModal = true" class="add-schedule-btn">
        添加排班
      </button>
    </div>
    
    <ScheduleConflictAlert v-if="hasConflict" />
    <div v-if="hasConflict" class="conflict-warning">
      ⚠️ 检测到排班冲突，请及时调整
    </div>
    
    <div class="schedule-table">
      <table>
        <thead>
          <tr>
            <th>教练</th>
            <th>开始时间</th>
            <th>结束时间</th>
            <th>课程</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="schedule in filteredSchedules" :key="schedule.id">
            <td>{{ getCoachName(schedule.coach_id) }}</td>
            <td>{{ formatDateTime(schedule.start_time) }}</td>
            <td>{{ formatDateTime(schedule.end_time) }}</td>
            <td>{{ schedule.course_id || '未分配' }}</td>
            <td>
              <button @click="editSchedule(schedule)">编辑</button>
              <button @click="deleteSchedule(schedule.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 添加/编辑排班模态框 -->
    <div v-if="showAddScheduleModal || showEditScheduleModal" class="modal">
      <div class="modal-content">
        <span class="close" @click="closeModal">&times;</span>
        <h2>{{ isEditing ? '编辑排班' : '添加排班' }}</h2>
        
        <form @submit.prevent="submitSchedule">
          <div class="form-group">
            <label>教练：</label>
            <select v-model="currentSchedule.coach_id" required>
              <option v-for="coach in coaches" :key="coach.id" :value="coach.id">
                {{ coach.name }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label>开始时间：</label>
            <input 
              type="datetime-local" 
              v-model="currentSchedule.start_time" 
              required
            />
          </div>
          
          <div class="form-group">
            <label>结束时间：</label>
            <input 
              type="datetime-local" 
              v-model="currentSchedule.end_time" 
              required
            />
          </div>
          
          <div class="form-group">
            <label>课程ID（可选）：</label>
            <input 
              type="text" 
              v-model="currentSchedule.course_id" 
              placeholder="输入课程ID"
            />
          </div>
          
          <button type="submit">提交</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import coachesApi from '../api/coaches';
import ScheduleConflictAlert from '../components/ScheduleConflictAlert.vue';

export default {
  name: 'CoachScheduleView',
  components: {
    ScheduleConflictAlert
  },
  setup() {
    const coaches = ref([]);
    const schedules = ref([]);
    const selectedCoachId = ref('');
    const showAddScheduleModal = ref(false);
    const showEditScheduleModal = ref(false);
    const isEditing = ref(false);
    const hasConflict = ref(false);
    
    const currentSchedule = ref({
      id: null,
      coach_id: '',
      start_time: '',
      end_time: '',
      course_id: ''
    });
    
    const filteredSchedules = computed(() => {
      if (!selectedCoachId.value) return schedules.value;
      return schedules.value.filter(
        schedule => schedule.coach_id === selectedCoachId.value
      );
    });
    
    const fetchCoaches = async () => {
      try {
        const response = await coachesApi.getCoaches();
        coaches.value = response.data;
      } catch (error) {
        console.error('获取教练列表失败:', error);
      }
    };
    
    const fetchSchedules = async () => {
      try {
        const response = await coachesApi.getSchedules();
        schedules.value = response.data;
        checkForConflicts();
      } catch (error) {
        console.error('获取排班列表失败:', error);
      }
    };
    
    const fetchCoachSchedules = async () => {
      if (!selectedCoachId.value) {
        fetchSchedules();
        return;
      }
      
      try {
        const response = await coachesApi.getCoachSchedules(selectedCoachId.value);
        schedules.value = response.data;
        checkForConflicts();
      } catch (error) {
        console.error('获取教练排班失败:', error);
      }
    };
    
    const checkForConflicts = () => {
      // 简化的冲突检测逻辑
      // 实际项目中应该在后端实现更复杂的冲突检测
      const timeSlots = {};
      
      // 检查排班冲突
      schedules.value.forEach(schedule => {
        const key = `${schedule.coach_id}-${schedule.start_time}-${schedule.end_time}`;
        if (timeSlots[key]) {
          hasConflict.value = true;
          return;
        }
        timeSlots[key] = true;
      });
      
      hasConflict.value = false; // 重置，实际项目中应该根据检测结果设置
    };
    
    const addSchedule = async () => {
      try {
        await coachesApi.addSchedule(currentSchedule.value);
        fetchSchedules();
        closeModal();
      } catch (error) {
        console.error('添加排班失败:', error);
      }
    };
    
    const updateSchedule = async () => {
      try {
        await coachesApi.updateSchedule(currentSchedule.value);
        fetchSchedules();
        closeModal();
      } catch (error) {
        console.error('更新排班失败:', error);
      }
    };
    
    const deleteSchedule = async (id) => {
      if (!confirm('确定要删除这个排班吗？')) return;
      
      try {
        await coachesApi.deleteSchedule(id);
        fetchSchedules();
      } catch (error) {
        console.error('删除排班失败:', error);
      }
    };
    
    const editSchedule = (schedule) => {
      currentSchedule.value = { ...schedule };
      isEditing.value = true;
      showEditScheduleModal.value = true;
    };
    
    const submitSchedule = () => {
      // 验证时间有效性
      const startTime = new Date(currentSchedule.value.start_time);
      const endTime = new Date(currentSchedule.value.end_time);
      
      if (startTime >= endTime) {
        alert('结束时间必须晚于开始时间');
        return;
      }
      
      if (isEditing.value) {
        updateSchedule();
      } else {
        addSchedule();
      }
    };
    
    const closeModal = () => {
      showAddScheduleModal.value = false;
      showEditScheduleModal.value = false;
      isEditing.value = false;
      currentSchedule.value = {
        id: null,
        coach_id: '',
        start_time: '',
        end_time: '',
        course_id: ''
      };
    };
    
    const getCoachName = (coachId) => {
      const coach = coaches.value.find(c => c.id === coachId);
      return coach ? coach.name : '未知教练';
    };
    
    const formatDateTime = (dateTime) => {
  if (!dateTime) return '';
  const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  };
  return new Date(dateTime).toLocaleString('zh-CN', options).replace(/\//g, '-');
      if (!dateTime) return '';
      return new Date(dateTime).toLocaleString();
    };
    
    onMounted(() => {
      fetchCoaches();
      fetchSchedules();
    });
    
    return {
      coaches,
      schedules,
      selectedCoachId,
      filteredSchedules,
      showAddScheduleModal,
      showEditScheduleModal,
      isEditing,
      hasConflict,
      currentSchedule,
      fetchCoachSchedules,
      editSchedule,
      deleteSchedule,
      submitSchedule,
      closeModal,
      getCoachName,
      formatDateTime
    };
  }
};
</script>

<style scoped>
.coach-schedule-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.coach-selector select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  margin-left: 10px;
}

.add-schedule-btn {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.add-schedule-btn:hover {
  background-color: #45a049;
}

.schedule-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

th {
  background-color: #f2f2f2;
}

tr:nth-child(even) {
  background-color: #f9f9f9;
}

button {
  padding: 6px 12px;
  margin-right: 5px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  opacity: 0.8;
}

/* 模态框样式 */
.modal {
  position: fixed;
  z-index: 1;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: #fefefe;
  padding: 20px;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  position: relative;
}

.close {
  position: absolute;
  right: 20px;
  top: 10px;
  font-size: 24px;
  font-weight: bold;
  cursor: pointer;
}

.close:hover {
  color: #aaa;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group select, 
.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

form button[type="submit"] {
  background-color: #4CAF50;
  color: white;
  padding: 10px 15px;
  margin-top: 10px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
    <div v-if="hasConflict" class="conflict-details">
      冲突详情：{{ conflictDetails }}
    </div>