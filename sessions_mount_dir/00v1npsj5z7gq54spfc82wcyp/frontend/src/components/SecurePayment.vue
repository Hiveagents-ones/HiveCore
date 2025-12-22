<template>
  <div class="secure-payment-container">
    <el-card class="payment-card">
      <template #header>
        <div class="card-header">
          <span>安全支付</span>
          <el-tag type="success" v-if="pciCompliant">PCI DSS 合规</el-tag>
          <el-tag type="danger" v-else>PCI DSS 检查中</el-tag>
        </div>
      </template>

      <el-form ref="paymentForm" :model="paymentForm" :rules="paymentRules" label-width="120px">
        <el-form-item label="会员ID" prop="memberId">
          <el-input v-model="paymentForm.memberId" placeholder="请输入会员ID" />
        </el-form-item>
        
        <el-form-item label="支付金额" prop="amount">
          <el-input-number v-model="paymentForm.amount" :min="0" :precision="2" />
        </el-form-item>
        
        <el-form-item label="支付类型" prop="paymentType">
          <el-select v-model="paymentForm.paymentType" placeholder="请选择支付类型">
            <el-option label="会员费" value="membership" />
            <el-option label="课程费" value="course" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="信用卡号" prop="cardNumber">
          <el-input 
            v-model="paymentForm.cardNumber" 
            placeholder="请输入信用卡号" 
            maxlength="16" 
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="有效期" prop="expiryDate">
          <el-date-picker
            v-model="paymentForm.expiryDate"
            type="month"
            placeholder="选择月份"
            value-format="MM/YY"
          />
        </el-form-item>
        
        <el-form-item label="CVV" prop="cvv">
          <el-input v-model="paymentForm.cvv" placeholder="CVV" maxlength="3" show-word-limit />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="submitPayment"
            :loading="isSubmitting"
            :disabled="!pciCompliant"
          >
            确认支付
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-dialog v-model="showReceipt" title="支付凭证" width="30%">
      <div class="receipt-content">
        <p><strong>交易ID:</strong> {{ receipt.transactionId }}</p>
        <p><strong>会员ID:</strong> {{ receipt.memberId }}</p>
        <p><strong>金额:</strong> ¥{{ receipt.amount.toFixed(2) }}</p>
        <p><strong>日期:</strong> {{ receipt.paymentDate }}</p>
        <p><strong>状态:</strong> <el-tag type="success">支付成功</el-tag></p>
      </div>
      <template #footer>
        <el-button type="primary" @click="showReceipt = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import axios from '../api/axios';

export default {
  name: 'SecurePayment',
  
  setup() {
    const paymentForm = ref({
      memberId: '',
      amount: 0,
      paymentType: '',
      cardNumber: '',
      expiryDate: '',
      cvv: ''
    });
    
    const paymentRules = {
      memberId: [{ required: true, message: '请输入会员ID', trigger: 'blur' }],
      amount: [{ required: true, message: '请输入支付金额', trigger: 'blur' }],
      paymentType: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
      cardNumber: [
        { required: true, message: '请输入信用卡号', trigger: 'blur' },
        { pattern: /^[0-9]{16}$/, message: '信用卡号必须为16位数字', trigger: 'blur' }
      ],
      expiryDate: [{ required: true, message: '请选择有效期', trigger: 'change' }],
      cvv: [
        { required: true, message: '请输入CVV', trigger: 'blur' },
        { pattern: /^[0-9]{3}$/, message: 'CVV必须为3位数字', trigger: 'blur' }
      ]
    };
    
    const pciCompliant = ref(false);
    const isSubmitting = ref(false);
    const showReceipt = ref(false);
    const receipt = ref({
      transactionId: '',
      memberId: '',
      amount: 0,
      paymentDate: ''
    });
    
    const checkPCICompliance = async () => {
      try {
        const response = await axios.get('/api/v1/payments/compliance');
        pciCompliant.value = response.data.compliant;
        if (!pciCompliant.value) {
          ElMessage.warning('系统正在进行PCI DSS安全检查，请稍后再试');
        }
      } catch (error) {
        console.error('PCI合规检查失败:', error);
        ElMessage.error('无法验证支付安全性');
      }
    };
    
    const submitPayment = async () => {
      try {
        isSubmitting.value = true;
        const response = await axios.post('/api/v1/payments', {
          member_id: paymentForm.value.memberId,
          amount: paymentForm.value.amount,
          payment_type: paymentForm.value.paymentType
        });
        
        receipt.value = {
          transactionId: response.data.transaction_id,
          memberId: paymentForm.value.memberId,
          amount: paymentForm.value.amount,
          paymentDate: new Date().toLocaleString()
        };
        
        showReceipt.value = true;
        resetForm();
        ElMessage.success('支付成功');
      } catch (error) {
        console.error('支付失败:', error);
        ElMessage.error(error.response?.data?.detail || '支付失败');
      } finally {
        isSubmitting.value = false;
      }
    };
    
    const resetForm = () => {
      paymentForm.value = {
        memberId: '',
        amount: 0,
        paymentType: '',
        cardNumber: '',
        expiryDate: '',
        cvv: ''
      };
    };
    
    onMounted(() => {
      checkPCICompliance();
    });
    
    return {
      paymentForm,
      paymentRules,
      pciCompliant,
      isSubmitting,
      showReceipt,
      receipt,
      submitPayment,
      resetForm
    };
  }
};
</script>

<style scoped>
.secure-payment-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.payment-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.receipt-content p {
  margin: 10px 0;
  line-height: 1.6;
}
</style>