<template>
  <div class="reservation-form">
    <h1>课程预约</h1>
    
    <div class="form-container">
      <el-form ref="form" :model="formData" :rules="rules" label-width="120px">
        
        <el-form-item label="选择日期" prop="date">
          <el-date-picker
            v-model="formData.date"
            type="date"
            placeholder="选择预约日期"
            :picker-options="datePickerOptions"
            @change="handleDateChange"
          />
        </el-form-item>
        
        <el-form-item label="选择课程" prop="courseId">
          <el-select 
            v-model="formData.courseId" 
            placeholder="请选择课程"
            :loading="loadingCourses"
            @change="handleCourseChange"
          >
            <el-option
              v-for="course in availableCourses"
              :key="course.id"
              :label="`${course.name} (${course.time}) - 教练: ${course.coach_name}`"
              :value="course.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="备注信息" prop="notes">
          <el-input
            v-model="formData.notes"
            type="textarea"
            :rows="2"
            placeholder="请输入特殊需求或备注"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="submitting"
            @click="submitForm"
          >
            提交预约
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <el-dialog
      title="预约成功"
      :visible.sync="successDialogVisible"
      width="30%"
      center
    >
      <span>课程预约成功！</span>
      <span slot="footer" class="dialog-footer">
        <el-button type="primary" @click="successDialogVisible = false">确定</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import reservationsApi from '@/api/reservations';
import { useStore } from 'vuex';

export default {
  name: 'ReservationForm',
  
  setup() {
    const store = useStore();
    const form = ref(null);
    const loadingCourses = ref(false);
    const submitting = ref(false);
    const successDialogVisible = ref(false);
    const availableCourses = ref([]);
    
    const formData = reactive({
      date: '',
      courseId: '',
      notes: '',
      memberId: store.getters.userId
    });
    
    const rules = {
      date: [
        { required: true, message: '请选择预约日期', trigger: 'change' }
      ],
      courseId: [
        { required: true, message: '请选择课程', trigger: 'change' }
      ]
    };
    
    const datePickerOptions = {
      disabledDate(time) {
        return time.getTime() < Date.now() - 8.64e7;
      }
    };
    
    const handleDateChange = async (date) => {
      if (!date) return;
      
      try {
        loadingCourses.value = true;
        const formattedDate = new Date(date).toISOString().split('T')[0];
        const response = await reservationsApi.getAvailableCourses(formattedDate);
        availableCourses.value = response.data;
      } catch (error) {
        ElMessage.error('获取课程列表失败: ' + error.message);
      } finally {
        loadingCourses.value = false;
      }
    };
    
    const handleCourseChange = (courseId) => {
      const selectedCourse = availableCourses.value.find(c => c.id === courseId);
      if (selectedCourse) {
        formData.time = selectedCourse.time;
      }
    };
    
    const submitForm = async () => {
      try {
        const valid = await form.value.validate();
        if (!valid) return;
        
        submitting.value = true;
        
        const reservationData = {
          course_id: formData.courseId,
          member_id: formData.memberId,
          reservation_time: formData.date,
          notes: formData.notes
        };
        
        await reservationsApi.createReservation(reservationData);
        successDialogVisible.value = true;
        resetForm();
      } catch (error) {
        ElMessage.error('预约失败: ' + error.message);
      } finally {
        submitting.value = false;
      }
    };
    
    const resetForm = () => {
      form.value.resetFields();
      availableCourses.value = [];
    };
    
    return {
      form,
      formData,
      rules,
      loadingCourses,
      submitting,
      successDialogVisible,
      availableCourses,
      datePickerOptions,
      handleDateChange,
      handleCourseChange,
      submitForm,
      resetForm
    };
  }
};
</script>

<style scoped>
.reservation-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.form-container {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}
</style>