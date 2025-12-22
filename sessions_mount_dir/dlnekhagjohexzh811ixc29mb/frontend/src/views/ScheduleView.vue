<template>
  <div class="schedule-view">
    <h1>教练排班日历</h1>
    
    <div class="controls">
      <el-button type="primary" @click="showCalendarView">日历视图</el-button>
      <el-select v-model="selectedCoach" placeholder="选择教练" @change="fetchSchedule">
        <el-option
          v-for="coach in coaches"
          :key="coach.id"
          :label="coach.name"
          :value="coach.id"
        />
      </el-select>
      
      <el-date-picker
        v-model="selectedWeek"
        type="week"
        format="第 ww 周"
        placeholder="选择周"
        @change="fetchSchedule"
      />
    </div>
    
    <div v-if="selectedCoach" class="schedule-container">
      <el-table :data="scheduleData" border style="width: 100%">
        <el-table-column prop="dayOfWeek" label="星期" width="120">
          <template #default="{ row }">
            {{ getDayName(row.dayOfWeek) }}
          </template>
        </el-table-column>
        <el-table-column prop="startHour" label="开始时间" width="120" />
        <el-table-column prop="endHour" label="结束时间" width="120" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="editSchedule(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteSchedule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-button class="add-btn" type="primary" @click="showAddDialog">添加排班</el-button>
    </div>
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle">
      <el-form :model="form">
        <el-form-item label="星期">
          <el-select v-model="form.dayOfWeek" placeholder="请选择星期">
            <el-option
              v-for="(day, index) in daysOfWeek"
              :key="index"
              :label="day"
              :value="index"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="form.startHour"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="form.endHour"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getCoaches, getCoachSchedule, addCoachSchedule, updateCoachSchedule, deleteCoachSchedule } from '../api/schedules';

export default {
  name: 'ScheduleView',
  setup() {
    const coaches = ref([]);
    const selectedCoach = ref('');
    const selectedWeek = ref(new Date());
    const scheduleData = ref([]);
    const dialogVisible = ref(false);
    const isEditMode = ref(false);
    const currentScheduleId = ref(null);
    
    const daysOfWeek = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    
    const form = ref({
      dayOfWeek: 0,
      startHour: '09:00',
      endHour: '17:00'
    });
    
    const dialogTitle = computed(() => {
      return isEditMode.value ? '编辑排班' : '添加排班';
    });
    
    const fetchCoaches = async () => {
      try {
        const response = await getCoaches();
        coaches.value = response.data;
      } catch (error) {
        ElMessage.error('获取教练列表失败');
      }
    };
    
    const fetchSchedule = async () => {
      if (!selectedCoach.value) return;
      
      try {
        const response = await getCoachSchedule(selectedCoach.value, {
          week: selectedWeek.value
        });
        scheduleData.value = response.data;
      } catch (error) {
        ElMessage.error('获取排班信息失败');
      }
    };
    
    const showAddDialog = () => {
      isEditMode.value = false;
      form.value = {
        dayOfWeek: 0,
        startHour: '09:00',
        endHour: '17:00'
      };
      dialogVisible.value = true;
    };
    
    const editSchedule = (row) => {
      isEditMode.value = true;
      currentScheduleId.value = row.id;
      form.value = {
        dayOfWeek: row.dayOfWeek,
        startHour: row.startHour,
        endHour: row.endHour
      };
      dialogVisible.value = true;
    };
    
    const deleteSchedule = async (row) => {
      try {
        await ElMessageBox.confirm('确定要删除这条排班记录吗?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        });
        
        await deleteCoachSchedule(selectedCoach.value, row.id);
        ElMessage.success('删除成功');
        fetchSchedule();
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败');
        }
      }
    };
    
    const submitForm = async () => {
      try {
        const scheduleData = {
          dayOfWeek: form.value.dayOfWeek,
          startHour: form.value.startHour,
          endHour: form.value.endHour
        };
        
        if (isEditMode.value) {
          await updateCoachSchedule(selectedCoach.value, currentScheduleId.value, scheduleData);
          ElMessage.success('更新成功');
        } else {
          await addCoachSchedule(selectedCoach.value, scheduleData);
          ElMessage.success('添加成功');
        }
        
        dialogVisible.value = false;
        fetchSchedule();
      } catch (error) {
        ElMessage.error(isEditMode.value ? '更新失败' : '添加失败');
      }
    };
    
    const getDayName = (dayOfWeek) => {
    const showCalendarView = () => {
      ElMessage.info('即将切换到日历视图');
    };
      return daysOfWeek[dayOfWeek];
    };
    
    onMounted(() => {
      fetchCoaches();
    });
    
    return {
      showCalendarView,
      coaches,
      selectedCoach,
      selectedWeek,
      scheduleData,
      dialogVisible,
      dialogTitle,
      form,
      daysOfWeek,
      fetchSchedule,
      showAddDialog,
      editSchedule,
      deleteSchedule,
      submitForm,
      getDayName
    };
  }
};
</script>

<style scoped>
.schedule-view {
  padding: 20px;
}

.controls {
  margin: 20px 0;
  display: flex;
  gap: 20px;
  align-items: center;
}

.schedule-container {
  margin-top: 20px;
}

.add-btn {
  margin-top: 20px;
}
</style>