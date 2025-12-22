<template>
  <el-dialog
    v-model="dialogVisible"
    title="支付确认"
    width="400px"
    :before-close="handleClose"
  >
    <div class="payment-content">
      <div class="payment-info">
        <h3>支付信息</h3>
        <div class="info-item">
          <span class="label">支付类型：</span>
          <span class="value">{{ paymentTypeText }}</span>
        </div>
        <div class="info-item" v-if="paymentData.course_id">
          <span class="label">课程ID：</span>
          <span class="value">{{ paymentData.course_id }}</span>
        </div>
        <div class="info-item">
          <span class="label">支付金额：</span>
          <span class="value amount">¥{{ paymentData.amount.toFixed(2) }}</span>
        </div>
      </div>

      <div class="payment-method">
        <h3>支付方式</h3>
        <el-radio-group v-model="selectedMethod">
          <el-radio label="alipay">
            <div class="method-option">
              <i class="iconfont icon-alipay"></i>
              <span>支付宝</span>
            </div>
          </el-radio>
          <el-radio label="wechat">
            <div class="method-option">
              <i class="iconfont icon-wechat"></i>
              <span>微信支付</span>
            </div>
          </el-radio>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handlePayment" :loading="loading">
          确认支付
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { paymentsApi, PaymentMethod } from '../api/payments';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  paymentData: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:visible', 'payment-success', 'payment-failed']);

const dialogVisible = ref(false);
const loading = ref(false);
const selectedMethod = ref('alipay');

// 监听visible变化
watch(() => props.visible, (newVal) => {
  dialogVisible.value = newVal;
});

// 监听dialogVisible变化
watch(dialogVisible, (newVal) => {
  emit('update:visible', newVal);
});

// 计算支付类型文本
const paymentTypeText = computed(() => {
  const typeMap = {
    [PaymentType.MEMBERSHIP]: '会员费',
    [PaymentType.PRIVATE_COURSE]: '私教课费用',
    [PaymentType.COURSE_BOOKING]: '课程预约费用'
  };
  return typeMap[props.paymentData.type] || '未知类型';
});

// 处理支付
const handlePayment = async () => {
  try {
    loading.value = true;
    
    // 创建支付订单
    const paymentResult = await paymentsApi.createPayment({
      member_id: props.paymentData.member_id,
      amount: props.paymentData.amount,
      type: props.paymentData.type,
      course_id: props.paymentData.course_id
    });

    // 模拟支付过程
    await simulatePayment(selectedMethod.value);

    // 支付成功
    ElMessage.success('支付成功！');
    emit('payment-success', paymentResult);
    handleClose();
  } catch (error) {
    console.error('支付失败:', error);
    ElMessage.error(error.message || '支付失败，请重试');
    emit('payment-failed', error);
  } finally {
    loading.value = false;
  }
};



// 轮询支付状态
const pollPaymentStatus = async (paymentId) => {
  const maxAttempts = 60; // 最多轮询60次（5分钟）
  let attempts = 0;
  
  const poll = async () => {
    try {
      attempts++;
      const result = await paymentsApi.verifyPayment(paymentId);
      
      if (result.status === 'success') {
        ElMessage.success('支付成功！');
        emit('payment-success', result);
        handleClose();
      } else if (result.status === 'failed') {
        ElMessage.error('支付失败，请重试');
        emit('payment-failed', new Error('支付失败'));
      } else if (attempts < maxAttempts) {
        // 继续轮询
        setTimeout(poll, 5000); // 每5秒查询一次
      } else {
        ElMessage.warning('支付超时，请手动刷新查看支付结果');
      }
    } catch (error) {
      console.error('查询支付状态失败:', error);
      if (attempts < maxAttempts) {
        setTimeout(poll, 5000);
      }
    }
  };
  
  poll();
};


// 关闭弹窗
const handleClose = () => {
  if (loading.value) return;
  
  ElMessageBox.confirm('确定要取消支付吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    dialogVisible.value = false;
  }).catch(() => {
    // 用户取消关闭
  });
};
</script>

<style scoped>
.payment-content {
  padding: 20px 0;
}

.payment-info {
  margin-bottom: 30px;
}

.payment-info h3 {
  margin-bottom: 15px;
  color: #303133;
  font-size: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
}

.info-item:last-child {
  border-bottom: none;
}

.label {
  color: #606266;
  font-size: 14px;
}

.value {
  color: #303133;
  font-size: 14px;
}

.amount {
  color: #f56c6c;
  font-weight: bold;
  font-size: 18px;
}

.payment-method h3 {
  margin-bottom: 15px;
  color: #303133;
  font-size: 16px;
}

.method-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.iconfont {
  font-size: 20px;
}

.icon-alipay {
  color: #1677ff;
}

.icon-wechat {
  color: #07c160;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
