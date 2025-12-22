<template>
  <div class="coach-schedule-view">
    <div class="header">
      <h1>教练排班管理</h1>
      <el-button type="primary" @click="showAddDialog = true">添加排班</el-button>
    </div>

    <div class="filter-section">
      <el-select v-model="selectedCoachId" placeholder="选择教练" @change="fetchSchedules">
        <el-option
          v-for="coach in coaches"
          :key="coach.id"
          :label="coach.name"
          :value="coach.id"
        />
      </el-select>
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择日期"
        @change="fetchAvailableSlots"
      />
    </div>

    <div class="schedule-container">
      <el-table :data="schedules" style="width: 100%" border>
        <el-table-column prop="day_of_week" label="星期" width="120" />
        <el-table-column prop="start_hour" label="开始时间" width="120" />
        <el-table-column prop="end_hour" label="结束时间" width="120" />
        <el-table-column label="操作" width="180">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="available-slots" v-if="availableSlots.length > 0">
        <h3>可用时间段</h3>
        <el-tag
          v-for="slot in availableSlots"
          :key="slot"
          type="info"
          class="slot-tag"
          @click="selectSlot(slot)"
        >
          {{ slot }}
        </el-tag>
      </div>
    </div>

    <!-- 添加/编辑排班对话框 -->
    <el-dialog v-model="showAddDialog" :title="isEditing ? '编辑排班' : '添加排班'">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="星期">
          <el-select v-model="formData.day_of_week" placeholder="请选择星期">
            <el-option
              v-for="day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']"
              :key="day"
              :label="day"
              :value="day"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="formData.start_hour"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="formData.end_hour"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="submitSchedule">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import {
  getCoachSchedules,
  createCoachSchedule,
  updateCoachSchedule,
  deleteCoachSchedule,
  getCoachAvailableSlots,
  getCachedSchedules
} from '@/api/schedules';
import { ElMessage, ElMessageBox } from 'element-plus';

export default {
  name: 'CoachScheduleView',
  setup() {
    const selectedCoachId = ref(null);
    const selectedDate = ref('');
    const schedules = ref([]);
    const availableSlots = ref([]);
    const coaches = ref([
      { id: 1, name: '张教练' },
      { id: 2, name: '李教练' },
      { id: 3, name: '王教练' }
    ]);
    const showAddDialog = ref(false);
    const isEditing = ref(false);
    const currentScheduleId = ref(null);
    const formData = ref({
      day_of_week: '',
      start_hour: '',
      end_hour: ''
    });

    const fetchSchedules = async () => {
      if (!selectedCoachId.value) return;

      try {
        // 先检查缓存
        const cached = getCachedSchedules(selectedCoachId.value);
        if (cached) {
          schedules.value = cached;
        }

        // 从API获取最新数据
        const data = await getCoachSchedules(selectedCoachId.value);
        schedules.value = data;
      } catch (error) {
        ElMessage.error('获取排班数据失败');
        console.error(error);
      }
    };

    const fetchAvailableSlots = async () => {
      if (!selectedCoachId.value || !selectedDate.value) return;

      try {
        const dateStr = selectedDate.value.toISOString().split('T')[0];
        const data = await getCoachAvailableSlots(selectedCoachId.value, dateStr);
        availableSlots.value = data;
      } catch (error) {
        ElMessage.error('获取可用时间段失败');
        console.error(error);
      }
    };

    const handleEdit = (schedule) => {
      isEditing.value = true;
      currentScheduleId.value = schedule.id;
      formData.value = {
        day_of_week: schedule.day_of_week,
        start_hour: schedule.start_hour,
        end_hour: schedule.end_hour
      };
      showAddDialog.value = true;
    };

    const handleDelete = async (schedule) => {
      try {
        await ElMessageBox.confirm('确定要删除这个排班吗?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        });

        await deleteCoachSchedule(selectedCoachId.value, schedule.id);
        ElMessage.success('删除成功');
        fetchSchedules();
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败');
          console.error(error);
        }
      }
    };

    const submitSchedule = async () => {
      try {
        if (isEditing.value) {
          await updateCoachSchedule(
            selectedCoachId.value,
            currentScheduleId.value,
            formData.value
          );
          ElMessage.success('更新成功');
        } else {
          await createCoachSchedule(selectedCoachId.value, formData.value);
          ElMessage.success('添加成功');
        }

        showAddDialog.value = false;
        fetchSchedules();
      } catch (error) {
        ElMessage.error(isEditing.value ? '更新失败' : '添加失败');
        console.error(error);
      }
    };

    const selectSlot = (slot) => {
      const [start, end] = slot.split('-');
      formData.value = {
        day_of_week: '',
        start_hour: start.trim(),
        end_hour: end.trim()
      };
      showAddDialog.value = true;
      isEditing.value = false;
    };

    onMounted(() => {
      // 默认选择第一个教练
      if (coaches.value.length > 0) {
        selectedCoachId.value = coaches.value[0].id;
      }
    });

    return {
      selectedCoachId,
      selectedDate,
      schedules,
      availableSlots,
      coaches,
      showAddDialog,
      isEditing,
      formData,
      fetchSchedules,
      fetchAvailableSlots,
      handleEdit,
      handleDelete,
      submitSchedule,
      selectSlot
    };
  }
};
</script>

<style scoped>
.coach-schedule-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.schedule-container {
  margin-top: 20px;
}

.available-slots {
  margin-top: 30px;
}

.slot-tag {
  margin-right: 10px;
  margin-bottom: 10px;
  cursor: pointer;
}

.slot-tag:hover {
  opacity: 0.8;
}
</style>