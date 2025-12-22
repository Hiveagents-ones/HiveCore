<template>
  <div class="payment-management">
    <h1>收费管理</h1>
    
    <div class="action-bar">
      <el-button type="primary" @click="showCreateDialog = true">新增收费</el-button>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="会员ID">
          <el-input v-model="searchForm.member_id" placeholder="会员ID" clearable />
        </el-form-item>
        
        <el-form-item label="支付方式">
          <el-select v-model="searchForm.payment_method" placeholder="支付方式" clearable>
            <el-option label="全部" value="" />
            <el-option label="微信支付" value="WeChat" />
            <el-option label="支付宝" value="Alipay" />
            <el-option label="现金" value="Cash" />
            <el-option label="银行卡" value="Bank Card" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <el-table :data="payments" style="width: 100%; margin-top: 20px" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="member_id" label="会员ID" width="100" />
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="payment_method" label="支付方式" width="150" />
      <el-table-column prop="payment_date" label="支付日期" width="180" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="totalPayments"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="fetchPayments"
      @size-change="fetchPayments"
      style="margin-top: 20px"
    />
    
    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="showCreateDialog" :title="isEditing ? '编辑收费记录' : '新增收费记录'" width="30%">
      <el-form :model="paymentForm" label-width="100px">
        <el-form-item label="会员ID" required>
          <el-input v-model.number="paymentForm.member_id" type="number" />
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input v-model.number="paymentForm.amount" type="number" />
        </el-form-item>
        <el-form-item label="支付方式" required>
        <el-form-item label="交易ID" required>
          <el-input v-model="paymentForm.transaction_id" />
        </el-form-item>
        <el-form-item label="安全码" required>
          <el-input v-model="paymentForm.security_code" type="password" show-password />
        </el-form-item>
          <el-select v-model="paymentForm.payment_method" placeholder="请选择支付方式">
            <el-option label="微信支付" value="WeChat" />
            <el-option label="支付宝" value="Alipay" />
            <el-option label="现金" value="Cash" />
            <el-option label="银行卡" value="Bank Card" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitPayment">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
  ElMessageBox,
  getPaymentStats,
import { 
  getPayments, 
  createPayment, 
  updatePayment, 
  deletePayment,
  getPaymentsByMemberId
} from '@/api/payments';

// 数据状态
const payments = ref([]);
const totalPayments = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const searchQuery = ref('');
const searchForm = ref({
  member_id: '',
  payment_method: '',
  dateRange: []
});

// 表单相关
const showCreateDialog = ref(false);
const isEditing = ref(false);
const currentPaymentId = ref(null);
const paymentForm = ref({
  member_id: '',
  amount: '',
  payment_method: '',
  transaction_id: '',
  security_code: ''
});

// 获取支付记录
const fetchPayments = async () => {
  // 构建查询参数
  const params = {};
  if (searchForm.value.member_id) params.member_id = searchForm.value.member_id;
  if (searchForm.value.payment_method) params.payment_method = searchForm.value.payment_method;
  if (searchForm.value.dateRange && searchForm.value.dateRange.length === 2) {
    params.start_date = searchForm.value.dateRange[0];
    params.end_date = searchForm.value.dateRange[1];
  }
  try {
    const stats = await getPaymentStats();
    console.log('Payment statistics:', stats);
  } catch (error) {
    console.error('Failed to fetch payment stats:', error);
  }
  try {
    let response;
    response = await getPayments(params);
    payments.value = response;
    totalPayments.value = payments.value.length;
  } catch (error) {
    console.error('获取支付记录失败:', error);
    ElMessage.error('获取支付记录失败');
  }
};

// 提交支付记录
const submitPayment = async () => {
  try {
    if (isEditing.value) {
      await updatePayment(currentPaymentId.value, paymentForm.value);
      ElMessage.success('更新成功');
    } else {
      await createPayment({
        ...paymentForm.value,
        payment_date: new Date().toISOString()
      });
      ElMessage.success('创建成功');
    }
    showCreateDialog.value = false;
    fetchPayments();
    resetForm();
  } catch (error) {
    console.error('提交失败:', error);
    ElMessage.error('提交失败');
  }
};

// 编辑支付记录
const handleEdit = (payment) => {
  isEditing.value = true;
  currentPaymentId.value = payment.id;
  paymentForm.value = {
    member_id: payment.member_id,
    amount: payment.amount,
    payment_method: payment.payment_method
  };
  showCreateDialog.value = true;
};

// 删除支付记录
const handleDelete = async (paymentId) => {
  try {
    await ElMessageBox.confirm('请确认删除操作原因:', '审计日志', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入删除原因...',
      inputValidator: (value) => {
        if (!value || value.length < 10) {
          return '删除原因必须至少10个字符';
        }
        return true;
      }
    });
    await deletePayment(paymentId);
    ElMessage.success('删除成功');
    fetchPayments();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error);
      ElMessage.error('删除失败');
    }
  }
  try {
    await ElMessageBox.confirm('确定要删除这条支付记录吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    await deletePayment(paymentId);
    ElMessage.success('删除成功');
    fetchPayments();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error);
      ElMessage.error('删除失败');
    }
  }
};

// 重置表单
const resetForm = () => {
// 重置搜索条件
const resetSearch = () => {
  searchForm.value = {
    member_id: '',
    payment_method: '',
    dateRange: []
  };
  fetchPayments();
};

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1;
  fetchPayments();
};
  paymentForm.value = {
    member_id: '',
    amount: '',
    payment_method: '',
    transaction_id: '',
    security_code: ''
  };
  isEditing.value = false;
  currentPaymentId.value = null;
};

// 初始化
onMounted(() => {
  fetchPayments();
});
</script>

<style scoped>
.payment-management {
  padding: 20px;
}
.action-bar {
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-left: 20px;
}

.search-form .el-form-item {
  margin-right: 15px;
  margin-bottom: 0;
}
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
</style>