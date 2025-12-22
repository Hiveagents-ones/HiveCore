<template>
  <div class="coach-schedule-container">
    <h1>教练排班管理</h1>
    <el-alert
      title="提示"
      type="info"
      description="在此页面可以设置教练的工作时间及课程分配"
      show-icon
      :closable="false"
    />
    
    <div class="schedule-controls">
      <el-button type="primary" @click="showAddDialog = true">添加排班</el-button>
      <el-date-picker
      v-model="selectedDate"
      type="date"
      placeholder="选择日期"
      @change="fetchSchedules"
      :disabled-date="disabledDate"
      style="width: 200px"
      :clearable="false"
    />
    <el-select v-model="statusFilter" placeholder="筛选状态" @change="fetchSchedules" clearable style="width: 150px; margin-left: 10px">
        <el-option label="全部" value="" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="待确认" value="pending" />
        <el-option label="已取消" value="canceled" />
      </el-select>

    </div>
    
    <el-table 
      v-loading="loading"
      :data="schedules" 
      style="width: 100%" 
      border
      stripe
    >
      <el-table-column prop="coach_name" label="教练" width="120" />
      <el-table-column prop="date" label="日期" width="120">
        <template #default="{ row }">
          {{ formatDate(row.date) }}
        </template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始时间" width="120" />
      <el-table-column prop="end_time" label="结束时间" width="120" />
      <el-table-column prop="course_name" label="课程" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row.status)">{{ formatStatus(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 添加/编辑排班对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑排班' : '添加排班'" width="50%">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="教练" required>
          <el-select v-model="formData.coach_id" placeholder="请选择教练">
            <el-option
              v-for="coach in coaches"
              :key="coach.id"
              :label="coach.name"
              :value="coach.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker 
            v-model="formData.date" 
            type="date" 
            placeholder="选择日期"
            :disabled-date="disabledDate"
          />
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-time-picker v-model="formData.start_time" format="HH:mm" />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-time-picker v-model="formData.end_time" format="HH:mm" />
        </el-form-item>
        <el-form-item label="课程">
          <el-input v-model="formData.course_name" placeholder="请输入课程名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import coachesApi from '../api/coaches.js';

export default {
  name: 'CoachSchedule',
  setup() {
    const schedules = ref([]);
    const coaches = ref([]);
    const selectedDate = ref(new Date());
    const loading = ref(false);
    const statusFilter = ref('');
    const showAddDialog = ref(false);
    const editMode = ref(false);
    const currentScheduleId = ref(null);
    
    const formData = ref({
      coach_id: '',
      date: new Date(),
      start_time: '',
      end_time: '',
      course_name: ''
    });
    
    const fetchSchedules = async () => {
      loading.value = true;
      try {
        const params = {}
        if (selectedDate.value) {
          params.date = selectedDate.value.toISOString().split('T')[0]
        }
        if (statusFilter.value) {
          params.status = statusFilter.value
        }
        const response = await coachesApi.getSchedules();
        schedules.value = response.data;
      } catch (error) {
        ElMessage.error('获取排班列表失败');
        console.error(error);
      } finally {
        loading.value = false;
      }
    };
    
    const disabledDate = (time) => {
      return time.getTime() < Date.now() - 8.64e7; // Disable dates before today
    };

    const fetchCoaches = async () => {
      try {
        const response = await coachesApi.getCoaches();
        coaches.value = response.data;
      } catch (error) {
        ElMessage.error('获取教练列表失败');
        console.error(error);
      }
    };
    
    const formatDate = (dateString) => {
      if (!dateString) return '';
      

    const formatStatus = (status) => {
      if (!status) return '';
      const statusMap = {
        'confirmed': '已确认',
        'pending': '待确认',
        'canceled': '已取消'
      };
      return statusMap[status] || status;
    };

    const getStatusTagType = (status) => {
      const typeMap = {
        'confirmed': 'success',
        'pending': 'warning',
        'canceled': 'danger'
      };
      return typeMap[status] || '';
    };
      const date = new Date(dateString);
      return date.toLocaleDateString();
    };
    
    const resetForm = () => {
      formData.value = {
        coach_id: '',
        date: new Date(),
        start_time: '',
        end_time: '',
        course_name: ''
      };
      editMode.value = false;
      currentScheduleId.value = null;
    };
    
    const handleEdit = (row) => {
      editMode.value = true;
      currentScheduleId.value = row.id;
      formData.value = {
        coach_id: row.coach_id,
        date: new Date(row.date),
        start_time: row.start_time,
        end_time: row.end_time,
        course_name: row.course_name
      };
      showAddDialog.value = true;
    };
    
    const handleDelete = (id) => {
      ElMessageBox.confirm('确定要删除这条排班记录吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await coachesApi.deleteSchedule(id);
          ElMessage.success('删除成功');
          fetchSchedules();
        } catch (error) {
          ElMessage.error('删除失败');
          console.error(error);
        }
      }).catch(() => {});
    };
    
    const submitForm = async () => {
      // Validate required fields
      if (!formData.value.coach_id || !formData.value.date || !formData.value.start_time || !formData.value.end_time) {
        ElMessage.error('请填写所有必填字段');
        return;
      }

      // Validate time range
      if (formData.value.start_time >= formData.value.end_time) {
        ElMessage.error('结束时间必须晚于开始时间');
        return;
      }

      try {
        const data = {
          ...formData.value,
          date: formData.value.date.toISOString().split('T')[0]
        };
        
        if (editMode.value) {
          await coachesApi.updateSchedule(currentScheduleId.value, data);
          ElMessage.success('更新成功');
        } else {
          await coachesApi.createSchedule(data);
          ElMessage.success('添加成功');
        }
        
        showAddDialog.value = false;
        fetchSchedules();
        resetForm();
      } catch (error) {
        ElMessage.error(editMode.value ? '更新失败' : '添加失败');
        console.error(error);
      }
    };
    
    onMounted(() => {
      fetchSchedules();
      fetchCoaches();
    });
    
    return {
      disabledDate,
      schedules,
      coaches,
      selectedDate,
      statusFilter,
      loading,
      showAddDialog,
      editMode,
      formData,
      fetchSchedules,
      formatDate,
      formatStatus,
      getStatusTagType,
      handleEdit,
      handleDelete,
      submitForm
    };
  }
};
</script>

<style scoped>
.coach-schedule-container {
  padding: 20px;
}

.schedule-controls {
  margin-bottom: 20px;
  align-items: center;
  display: flex;
  gap: 15px;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
      <el-select v-model="statusFilter" placeholder="筛选状态" @change="fetchSchedules" clearable>
        <el-option label="全部" value="" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="待确认" value="pending" />
        <el-option label="已取消" value="canceled" />
      </el-select>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    const formatDate = (dateString) => {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      return date.toLocaleDateString();
    };