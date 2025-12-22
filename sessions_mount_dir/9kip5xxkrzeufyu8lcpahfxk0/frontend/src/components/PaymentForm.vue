<template>
  <div class="payment-form">
    <el-form :model="formData" :rules="rules" ref="paymentForm" label-width="120px">
      <el-form-item label="会员" prop="memberId">
        <el-select
          v-model="formData.memberId"
          filterable
          remote
          reserve-keyword
          placeholder="请输入会员姓名或手机号搜索"
          :remote-method="searchMembers"
          :loading="loadingMembers"
        >
          <el-option
            v-for="member in memberOptions"
            :key="member.id"
            :label="`${member.name} (${member.phone})`"
            :value="member.id"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="支付类型" prop="type">
        <el-select v-model="formData.type" placeholder="请选择支付类型">
          <el-option label="会员费" value="membership" />
          <el-option label="课程费" value="course" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="支付金额" prop="amount">
        <el-input-number v-model="formData.amount" :min="0" :precision="2" />
      </el-form-item>
      
      <el-form-item label="支付方式" prop="paymentMethod">
        <el-select v-model="formData.paymentMethod" placeholder="请选择支付方式">
          <el-option label="现金" value="cash" />
          <el-option label="信用卡" value="credit_card" />
          <el-option label="支付宝" value="alipay" />
          <el-option label="微信支付" value="wechat_pay" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="关联ID" prop="referenceId">
        <el-input v-model="formData.referenceId" placeholder="请输入会员卡ID或课程ID" />
      </el-form-item>
      
      <el-form-item label="描述" prop="description">
        <el-input 
          v-model="formData.description" 
          type="textarea" 
          :rows="2" 
          placeholder="请输入支付描述" 
        />
      </el-form-item>
      
      <el-form-item>
        <el-button type="primary" @click="submitForm">提交</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { usePaymentApi } from '@/api/payments';
import { useMemberApi } from '@/api/members';

export default {
  name: 'PaymentForm',
  
  props: {
    memberId: {
      type: String,
      default: ''
    },
    paymentData: {
      type: Object,
      default: () => ({})
    }
  },
  
  setup(props) {
    const paymentForm = ref(null);
    const memberApi = useMemberApi();
    const memberOptions = ref([]);
    const loadingMembers = ref(false);
    const formData = ref({
      memberId: props.memberId || '',
      type: '',
      amount: 0,
      paymentMethod: '',
      description: '',
      referenceId: ''
    });
    
    // 如果有传入的paymentData，则填充表单
    if (props.paymentData && Object.keys(props.paymentData).length > 0) {
      formData.value = { ...props.paymentData };
    } else if (props.memberId) {
      formData.value.memberId = props.memberId;
    }
    
    const rules = {
      memberId: [
        { required: true, message: '请输入会员ID', trigger: 'blur' }
      ],
      type: [
        { required: true, message: '请选择支付类型', trigger: 'change' }
      ],
      amount: [
        { required: true, message: '请输入支付金额', trigger: 'blur' },
        { type: 'number', min: 0, message: '金额必须大于0', trigger: 'blur' }
      ],
      paymentMethod: [
        { required: true, message: '请选择支付方式', trigger: 'change' }
      ]
    };
    
    const submitForm = async () => {
      try {
        await paymentForm.value.validate();
        
        const response = await usePaymentApi().createPayment(formData.value);
        
        ElMessage.success('支付记录创建成功');
        emit('success', response);
        resetForm();
      } catch (error) {
        console.error('提交支付表单失败:', error);
        ElMessage.error(`提交失败: ${error.message || '未知错误'}`);
      }
    };
    
    const resetForm = () => {
      paymentForm.value.resetFields();
      if (props.memberId) {
        formData.value.memberId = props.memberId;
      }
    };

    const searchMembers = async (query) => {
      if (!query || query.length < 2) {
        memberOptions.value = [];
        return;
      }
      
      try {
        loadingMembers.value = true;
        const members = await memberApi.searchMembers({ q: query });
        memberOptions.value = members;
      } catch (error) {
        console.error('搜索会员失败:', error);
        ElMessage.error('搜索会员失败');
      } finally {
        loadingMembers.value = false;
      }
    };

    
    return {
      memberOptions,
      loadingMembers,
      paymentForm,
      formData,
      rules,
      submitForm,
      resetForm
    };
  }
};
</script>

<style scoped>
.payment-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
</style>