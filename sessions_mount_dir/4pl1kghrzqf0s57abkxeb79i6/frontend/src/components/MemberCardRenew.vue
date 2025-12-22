<template>
  <el-dialog
    v-model="dialogVisible"
    title="会员卡续费/升级"
    width="500px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="当前会员卡">
        <el-tag :type="currentCardType?.type || 'info'">
          {{ currentCardType?.name || '无' }}
        </el-tag>
        <span class="ml-2 text-gray-500">
          到期时间: {{ formatDate(memberInfo.expire_date) }}
        </span>
      </el-form-item>

      <el-form-item label="操作类型" prop="operation">
        <el-radio-group v-model="form.operation" @change="handleOperationChange">
          <el-radio label="renew">续费</el-radio>
          <el-radio label="upgrade">升级</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item 
        v-if="form.operation === 'renew'" 
        label="续费时长" 
        prop="duration"
      >
        <el-select v-model="form.duration" placeholder="请选择续费时长">
          <el-option
            v-for="item in durationOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item 
        v-if="form.operation === 'upgrade'" 
        label="升级类型" 
        prop="upgradeType"
      >
        <el-select v-model="form.upgradeType" placeholder="请选择升级类型">
          <el-option
            v-for="item in upgradeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="支付方式" prop="paymentMethod">
        <el-select v-model="form.paymentMethod" placeholder="请选择支付方式">
          <el-option label="现金" value="cash" />
          <el-option label="支付宝" value="alipay" />
          <el-option label="微信" value="wechat" />
          <el-option label="银行卡" value="card" />
        </el-select>
      </el-form-item>

      <el-form-item label="实付金额" prop="amount">
        <el-input-number
          v-model="form.amount"
          :min="0"
          :precision="2"
          :step="0.01"
          placeholder="请输入金额"
        />
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.remark"
          type="textarea"
          :rows="3"
          placeholder="请输入备注信息"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading">
          确认
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { renewMembership, upgradeMembership } from '../api/member';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  memberInfo: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:visible', 'success']);

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
});

const formRef = ref(null);
const loading = ref(false);

const form = reactive({
  operation: 'renew',
  duration: '',
  upgradeType: '',
  paymentMethod: '',
  amount: 0,
  remark: ''
});

const rules = {
  operation: [{ required: true, message: '请选择操作类型', trigger: 'change' }],
  duration: [{ required: true, message: '请选择续费时长', trigger: 'change' }],
  upgradeType: [{ required: true, message: '请选择升级类型', trigger: 'change' }],
  paymentMethod: [{ required: true, message: '请选择支付方式', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }]
};

const currentCardType = computed(() => {
  const cardTypes = {
    monthly: { name: '月卡', type: 'success' },
    quarterly: { name: '季卡', type: 'warning' },
    yearly: { name: '年卡', type: 'danger' }
  };
  return cardTypes[props.memberInfo.card_type] || null;
});

const durationOptions = [
  { label: '1个月', value: 1 },
  { label: '3个月', value: 3 },
  { label: '6个月', value: 6 },
  { label: '12个月', value: 12 }
];

const upgradeOptions = computed(() => {
  const currentType = props.memberInfo.card_type;
  const options = [];
  
  if (currentType === 'monthly') {
    options.push(
      { label: '季卡', value: 'quarterly' },
      { label: '年卡', value: 'yearly' }
    );
  } else if (currentType === 'quarterly') {
    options.push({ label: '年卡', value: 'yearly' });
  }
  
  return options;
});

const handleOperationChange = () => {
  form.duration = '';
  form.upgradeType = '';
  form.amount = 0;
};

const formatDate = (date) => {
  if (!date) return '未设置';
  return new Date(date).toLocaleDateString('zh-CN');
};

const handleClose = () => {
  dialogVisible.value = false;
  resetForm();
};

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  Object.assign(form, {
    operation: 'renew',
    duration: '',
    upgradeType: '',
    paymentMethod: '',
    amount: 0,
    remark: ''
  });
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  
  try {
    await formRef.value.validate();
    loading.value = true;

    const data = {
      payment_method: form.paymentMethod,
      amount: form.amount,
      remark: form.remark
    };

    let result;
    if (form.operation === 'renew') {
      data.duration = form.duration;
      result = await renewMembership(props.memberInfo.id, data);
    } else {
      data.new_card_type = form.upgradeType;
      result = await upgradeMembership(props.memberInfo.id, data);
    }

    ElMessage.success(`${form.operation === 'renew' ? '续费' : '升级'}成功`);
    emit('success', result.data);
    handleClose();
  } catch (error) {
    console.error('操作失败:', error);
    ElMessage.error(error.response?.data?.detail || '操作失败，请重试');
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      resetForm();
    }
  }
);
</script>

<style scoped>
.ml-2 {
  margin-left: 8px;
}

.text-gray-500 {
  color: #6b7280;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>