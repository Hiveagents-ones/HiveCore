<template>
  <div class="coach-schedule-container">
    <div class="header">
      <h1>教练排班管理</h1>
      <div class="actions">
        <el-button type="primary" @click="fetchCoaches">刷新列表</el-button>
        <el-button type="success" @click="showAddCoachDialog = true">添加教练</el-button>
      </div>
    </div>

    <div class="content" :class="{ 'mobile-view': isMobile }">
      <div class="coach-list">
        <el-table :data="coaches" style="width: 100%" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="name" label="姓名" width="120" />
          <el-table-column prop="phone" label="电话" width="150" />
          <el-table-column prop="specialty" label="专长" />
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button size="small" @click="editCoach(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteCoach(scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="schedule-editor" v-if="selectedCoach">
        <h2>{{ selectedCoach.name }}的排班表</h2>
        <el-calendar :style="{ width: isMobile ? '100%' : 'auto' }">
          <template #dateCell="{ date, data }">
            <div class="calendar-day">
              <div class="day-number">{{ data.day.split('-').slice(2).join('-') }}</div>
              <div class="schedule-info" v-if="getScheduleForDate(date)">
                <el-tag type="success" size="small">
                  {{ getScheduleForDate(date).courseName }}
                </el-tag>
              </div>
              <el-button 
                v-if="isFutureDate(date)"
                size="mini" 
                type="text" 
                @click.stop="openScheduleDialog(date)"
              >
                安排
              </el-button>
            </div>
          </template>
        </el-calendar>
      </div>
    </div>

    <!-- 添加/编辑教练对话框 -->
    <el-dialog v-model="showAddCoachDialog" :title="editingCoach ? '编辑教练' : '添加教练'" width="30%">
      <el-form :model="coachForm" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="coachForm.name" />
        </el-form-item>
        <el-form-item label="电话" required>
          <el-input v-model="coachForm.phone" />
        </el-form-item>
        <el-form-item label="专长">
          <el-input v-model="coachForm.specialty" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddCoachDialog = false">取消</el-button>
        <el-button type="primary" @click="submitCoachForm">确认</el-button>
      </template>
    </el-dialog>

    <!-- 排班对话框 -->
    <el-dialog v-model="showScheduleDialog" title="安排课程" width="30%">
      <el-form :model="scheduleForm" label-width="80px">
        <el-form-item label="日期">
          <el-date-picker 
            v-model="scheduleForm.date" 
            type="date" 
            disabled 
            format="YYYY-MM-DD" 
          />
        </el-form-item>
        <el-form-item label="课程">
          <el-select v-model="scheduleForm.courseId" placeholder="请选择课程">
            <el-option 
              v-for="course in availableCourses" 
              :key="course.id" 
              :label="course.name" 
              :value="course.id" 
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showScheduleDialog = false">取消</el-button>
        <el-button type="primary" @click="submitSchedule">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { 
  getCoaches, 
  createCoach, 
  updateCoach, 
  deleteCoach, 
  getCoachSchedules, 
  updateCoachSchedules 
} from '../api/coach';
import { ElMessage, ElMessageBox } from 'element-plus';

export default {
  name: 'CoachSchedule',
  setup() {
    const coaches = ref([]);
    const selectedCoach = ref(null);
    const schedules = ref([]);
    const showAddCoachDialog = ref(false);
    const showScheduleDialog = ref(false);
    const editingCoach = ref(false);
    const coachForm = ref({
      id: null,
      name: '',
      phone: '',
      specialty: ''
    });
    const scheduleForm = ref({
      date: null,
      courseId: null
    });
    const availableCourses = ref([
      { id: 1, name: '瑜伽课' },
      { id: 2, name: '普拉提' },
      { id: 3, name: '有氧操' },
      { id: 4, name: '私教课' }
    ]);

    const fetchCoaches = async () => {
      try {
        const data = await getCoaches();
        coaches.value = data;
        if (data.length > 0 && !selectedCoach.value) {
          selectCoach(data[0]);
        }
      } catch (error) {
        ElMessage.error('获取教练列表失败');
      }
    };

    const selectCoach = async (coach) => {
      selectedCoach.value = coach;
      try {
        const data = await getCoachSchedules(coach.id);
        schedules.value = data;
      } catch (error) {
        ElMessage.error('获取排班信息失败');
      }
    };

    const editCoach = (coach) => {
      editingCoach.value = true;
      coachForm.value = { ...coach };
      showAddCoachDialog.value = true;
    };

    const submitCoachForm = async () => {
      try {
        if (editingCoach.value) {
          await updateCoach(coachForm.value.id, coachForm.value);
          ElMessage.success('教练信息更新成功');
        } else {
          await createCoach(coachForm.value);
          ElMessage.success('教练添加成功');
        }
        showAddCoachDialog.value = false;
        fetchCoaches();
      } catch (error) {
        ElMessage.error('操作失败');
      }
    };

    const deleteCoach = async (id) => {
      try {
        await ElMessageBox.confirm('确定要删除该教练吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        });
        await deleteCoach(id);
        ElMessage.success('删除成功');
        fetchCoaches();
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败');
        }
      }
    };

    const openScheduleDialog = (date) => {
      scheduleForm.value = {
        date: date,
        courseId: null
      };
      showScheduleDialog.value = true;
    };

    const submitSchedule = async () => {
      try {
        const newSchedule = {
          date: formatDate(scheduleForm.value.date),
          courseId: scheduleForm.value.courseId,
          courseName: availableCourses.value.find(c => c.id === scheduleForm.value.courseId)?.name || ''
        };

        const existingIndex = schedules.value.findIndex(s => 
          s.date === newSchedule.date
        );

        if (existingIndex >= 0) {
          schedules.value[existingIndex] = newSchedule;
        } else {
          schedules.value.push(newSchedule);
        }

        await updateCoachSchedules(selectedCoach.value.id, schedules.value);
        ElMessage.success('排班更新成功');
        showScheduleDialog.value = false;
      } catch (error) {
        ElMessage.error('排班更新失败');
      }
    };

    const getScheduleForDate = (date) => {
      const dateStr = formatDate(date);
      return schedules.value.find(s => s.date === dateStr);
    };

    const isFutureDate = (date) => {
  // 移动端适配 - 调整日历显示
  const isMobile = ref(window.innerWidth < 768);
  
  onMounted(() => {
    window.addEventListener('resize', () => {
      isMobile.value = window.innerWidth < 768;
    });
  });
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return date >= today;
    };

    const formatDate = (date) => {
      const d = new Date(date);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    onMounted(() => {
      fetchCoaches();
    });

    return {
    isMobile,
      coaches,
      selectedCoach,
      selectCoach,
      showAddCoachDialog,
      showScheduleDialog,
      editingCoach,
      coachForm,
      scheduleForm,
      availableCourses,
      fetchCoaches,
      editCoach,
      deleteCoach,
      submitCoachForm,
      openScheduleDialog,
      submitSchedule,
      getScheduleForDate,
      isFutureDate
    };
  }
};
</script>

<style scoped>
@media (max-width: 768px) {
  .content {
    flex-direction: column;
  }
  
  .coach-list {
    margin-bottom: 20px;
  }
  
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .actions {
    width: 100%;
    display: flex;
    gap: 10px;
  }
  
  .actions .el-button {
    flex: 1;
  }
  
  .el-table {
    width: 100%;
    overflow-x: auto;
  }
  
  .el-calendar {
    width: 100%;
  }
  
  .el-dialog {
    width: 90% !important;
  }
}
.coach-schedule-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.content {
  display: flex;
  gap: 20px;
}

.coach-list {
  flex: 1;
}

.schedule-editor {
  flex: 2;
}

.calendar-day {
  height: 100%;
  padding: 5px;
}

.day-number {
  font-weight: bold;
  margin-bottom: 5px;
}

.schedule-info {
  margin: 5px 0;
}
</style>