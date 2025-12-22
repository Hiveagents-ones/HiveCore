<template>
  <el-dialog
    v-model="visible"
    title="生成报表"
    width="50%"
    :before-close="handleClose"
  >
    <el-form
      ref="reportForm"
      :model="reportParams"
      label-width="120px"
      :rules="rules"
    >
      <el-form-item label="报表类型" prop="report_type">
        <el-select
          v-model="reportParams.report_type"
          placeholder="请选择报表类型"
          style="width: 100%"
        >
          <el-option
            label="会员费收入报表"
            value="membership_income"
          />
          <el-option
            label="课程费收入报表"
            value="course_income"
          />
          <el-option
            label="综合收入报表"
            value="total_income"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="定时生成" prop="schedule_time">
        <el-switch v-model="isScheduled" />
        <el-date-picker
          v-model="reportParams.schedule_time"
          type="datetime"
          placeholder="选择定时时间"
          :disabled="!isScheduled"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="width: 100%; margin-top: 10px"
        />
      </el-form-item>

      <el-form-item v-if="progress > 0" label="生成进度">
        <el-progress :percentage="progress" :status="progress === 100 ? 'success' : ''" />
      </el-form-item>

      <el-form-item label="日期范围" prop="date_range">
        <el-date-picker
          v-model="reportParams.date_range"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="报表格式" prop="format">
        <el-radio-group v-model="reportParams.format">
          <el-radio label="pdf">PDF</el-radio>
          <el-radio label="excel">Excel</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="loading">
          生成
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, defineEmits, defineProps } from 'vue';
import { ElMessage } from 'element-plus';
import { generateReport } from '@/api/reports';
import { checkReportStatus } from '@/api/reports';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:visible']);

const reportParams = ref({
  report_type: '',
  date_range: [],
  format: 'pdf',
  schedule_time: '',
});

const reportForm = ref(null);
const loading = ref(false);
const isScheduled = ref(false);
const scheduleTime = ref('');
const progress = ref(0);
const taskId = ref(null);
const progressInterval = ref(null);

const rules = {
  report_type: [
    { required: true, message: '请选择报表类型', trigger: 'change' },
  ],
  schedule_time: [
    { validator: (rule, value, callback) => {
      if (isScheduled.value && !value) {
        callback(new Error('请选择定时时间'));
      } else {
        callback();
      }
    }, trigger: 'change' }
  ],
  date_range: [
    { required: true, message: '请选择日期范围', trigger: 'change' },
  ],
};

const handleClose = () => {
  emit('update:visible', false);
  reportForm.value.resetFields();
};

const handleGenerate = async () => {
  try {
    await reportForm.value.validate();
    loading.value = true;

    const params = {
      report_type: reportParams.value.report_type,
      start_date: reportParams.value.date_range[0],
      end_date: reportParams.value.date_range[1],
      format: reportParams.value.format,
    };

    const response = await generateReport(params);
    
    if (response.data) {
      const link = document.createElement('a');
      link.href = response.data.download_url;
      link.download = response.data.filename;
      link.click();
      
      ElMessage.success('报表生成成功，开始下载');
      handleClose();
    }
  } catch (error) {
    console.error('生成报表失败:', error);
    ElMessage.error('生成报表失败: ' + (error.message || '未知错误'));
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const handleGenerate = async () => {
  try {
    await reportForm.value.validate();
    loading.value = true;

    const params = {
      report_type: reportParams.value.report_type,
      start_date: reportParams.value.date_range[0],
      end_date: reportParams.value.date_range[1],
      format: reportParams.value.format,
      schedule_time: isScheduled.value ? reportParams.value.schedule_time : null
    };

    const response = await generateReport(params);

    if (isScheduled.value) {
      taskId.value = response.data.task_id;
      progressInterval.value = setInterval(checkProgress, 2000);
      ElMessage.success('报表已加入定时任务队列');
    } else {
      if (response.data) {
        const link = document.createElement('a');
        link.href = response.data.download_url;
        link.download = response.data.filename;
        link.click();
        ElMessage.success('报表生成成功，开始下载');
        handleClose();
      }
    }
  } catch (error) {
    console.error('生成报表失败:', error);
    ElMessage.error('生成报表失败: ' + (error.message || '未知错误'));
    clearInterval(progressInterval.value);
  } finally {
    if (!isScheduled.value) {
      loading.value = false;
    }
  }
};

const checkProgress = async () => {
  try {
    const response = await checkReportStatus(taskId.value);
    progress.value = response.data.progress;
    
    if (progress.value === 100) {
      clearInterval(progressInterval.value);
      loading.value = false;
      
      const link = document.createElement('a');
      link.href = response.data.download_url;
      link.download = response.data.filename;
      link.click();
      
      ElMessage.success('定时报表生成完成，开始下载');
      handleClose();
    }
  } catch (error) {
    console.error('获取进度失败:', error);
    clearInterval(progressInterval.value);
    loading.value = false;
  }
};