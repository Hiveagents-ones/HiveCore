<template>
  <div class="reminder-config">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>续费提醒配置</span>
        </div>
      </template>
      
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef" 
        label-width="150px"
      >
        <el-form-item label="到期前提醒天数" prop="leadTime">
          <el-input 
            v-model.number="form.leadTime" 
            type="number" 
            min="1" 
            placeholder="例如：7" 
            :disabled="isSaving"
          />
        </el-form-item>

        <el-form-item label="通知类型" prop="notificationType">
          <el-select 
            v-model="form.notificationType" 
            placeholder="请选择通知类型" 
            :disabled="isSaving"
          >
            <el-option label="短信" value="sms" />
            <el-option label="邮件" value="email" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="submitForm" 
            :loading="isSaving"
            :disabled="isSaving"
          >
            {{ isSaving ? '保存中...' : '保存配置' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';

const form = reactive({
  leadTime: 7,
  notificationType: 'sms'
});

const rules = {
  leadTime: [
    { required: true, message: '请输入提前天数', trigger: 'blur' },
    { validator: (rule, value) => value > 0, message: '提前天数必须大于0', trigger: 'blur' }
  ],
  notificationType: [
    { required: true, message: '请选择通知类型', trigger: 'change' }
  ]
};

const formRef = ref();
const isSaving = ref(false);

const submitForm = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      isSaving.value = true;
      
      // 模拟API调用
      setTimeout(() => {
        isSaving.value = false;
        ElMessage.success('配置已成功保存');
      }, 800);
    }
  });
};
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  font-weight: bold;
}

.reminder-config {
  max-width: 600px;
  margin: 20px auto;
}
</style>