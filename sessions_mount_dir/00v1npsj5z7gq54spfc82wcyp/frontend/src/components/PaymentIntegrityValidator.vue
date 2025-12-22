<template>
  <div class="payment-integrity-validator">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>支付完整性验证</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="交易ID" prop="transactionId">
          <el-input v-model="form.transactionId" placeholder="请输入交易ID" />
        </el-form-item>
        
        <el-form-item label="验证类型" prop="validationType">
          <el-select v-model="form.validationType" placeholder="请选择验证类型">
            <el-option label="金额验证" value="amount" />
            <el-option label="签名验证" value="signature" />
            <el-option label="完整性验证" value="full" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="validatePayment" :loading="loading">
            验证支付
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-divider />
      
      <div v-if="result" class="result-container">
        <h3>验证结果</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="交易ID">{{ result.transaction_id }}</el-descriptions-item>
          <el-descriptions-item label="验证状态">
            <el-tag :type="result.is_valid ? 'success' : 'danger'">
              {{ result.is_valid ? '验证通过' : '验证失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="验证详情">{{ result.details }}</el-descriptions-item>
          <el-descriptions-item label="时间戳">{{ result.timestamp }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import axios from '../api/axios';

export default {
  name: 'PaymentIntegrityValidator',
  
  setup() {
    const form = ref({
      transactionId: '',
      validationType: 'full'
    });
    
    const formRef = ref(null);
    const loading = ref(false);
    const result = ref(null);
    
    const rules = {
      transactionId: [
        { required: true, message: '请输入交易ID', trigger: 'blur' },
        { min: 10, max: 64, message: '长度在10到64个字符', trigger: 'blur' }
      ],
      validationType: [
        { required: true, message: '请选择验证类型', trigger: 'change' }
      ]
    };
    
    const validatePayment = async () => {
      try {
        const valid = await formRef.value.validate();
        if (!valid) return;
        
        loading.value = true;
        
        const response = await axios.post('/api/v1/payments/validate', {
          transaction_id: form.value.transactionId,
          validation_type: form.value.validationType
        });
        
        result.value = response.data;
        ElMessage.success('验证完成');
      } catch (error) {
        console.error('验证失败:', error);
        ElMessage.error(error.response?.data?.detail || '验证失败');
      } finally {
        loading.value = false;
      }
    };
    
    return {
      form,
      formRef,
      loading,
      result,
      rules,
      validatePayment
    };
  }
};
</script>

<style scoped>
.payment-integrity-validator {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.result-container {
  margin-top: 20px;
}
</style>