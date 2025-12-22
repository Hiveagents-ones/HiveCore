<template>
  <div class="payment-list-view">
    <div class="header">
      <h1>支付记录</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        新增支付记录
      </el-button>
    </div>

    <div class="filter-container">
      <el-form :inline="true" :model="filterParams" class="filter-form">
        <el-form-item label="会员ID">
          <el-input
            v-model="filterParams.memberId"
            placeholder="请输入会员ID"
            clearable
          />
        </el-form-item>
        <el-form-item label="支付类型">
          <el-select
            v-model="filterParams.type"
            placeholder="请选择支付类型"
            clearable
          >
            <el-option label="会员费" value="membership" />
            <el-option label="课程费" value="course" />
            <el-option label="私教费" value="personal_training" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchPayments">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-table :data="payments" border style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="支付ID" width="180" />
      <el-table-column prop="memberId" label="会员ID" width="120" />
      <el-table-column prop="type" label="类型" width="120">
        <template #default="scope">
          {{ 
              scope.row.type === 'membership' ? '会员费' : 
              scope.row.type === 'course' ? '课程费' : 
              '私教费'
            }}
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="120" />
      <el-table-column prop="paymentMethod" label="支付方式" width="120">
          <template #default="scope">
            {{ 
              scope.row.paymentMethod === 'alipay' ? '支付宝' : 
              scope.row.paymentMethod === 'wechat' ? '微信支付' : 
              scope.row.paymentMethod === 'cash' ? '现金' : 
              scope.row.paymentMethod === 'card' ? '银行卡' : 
              scope.row.paymentMethod
            }}
          </template>
        </el-table-column>
      <el-table-column prop="createdAt" label="支付时间" width="180" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(scope.row.id)"
            >删除</el-button
          >
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pagination"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="handlePageChange"
      layout="total, prev, pager, next, jumper"
    />

    <!-- 创建支付对话框 -->
    <el-dialog v-model="showCreateDialog" title="新增支付记录" width="50%">
      <el-form :model="newPayment" label-width="120px" :rules="rules" ref="createForm">
        <el-form-item label="会员ID" prop="memberId">
          <el-input v-model="newPayment.memberId" />
        </el-form-item>
        <el-form-item label="支付类型" prop="type">
          <el-select v-model="newPayment.type" placeholder="请选择支付类型">
            <el-option label="会员费" value="membership" />
            <el-option label="课程费" value="course" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="newPayment.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="支付方式" prop="paymentMethod">
          <el-input v-model="newPayment.paymentMethod" />
        </el-form-item>
        <el-form-item label="关联ID" prop="referenceId">
          <el-input v-model="newPayment.referenceId" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="newPayment.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="handleCreate">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑支付对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑支付记录" width="50%">
      <el-form :model="currentPayment" label-width="120px" :rules="rules" ref="editForm">
        <el-form-item label="会员ID" prop="memberId">
          <el-input v-model="currentPayment.memberId" disabled />
        </el-form-item>
        <el-form-item label="支付类型" prop="type">
          <el-select v-model="currentPayment.type" placeholder="请选择支付类型" disabled>
            <el-option label="会员费" value="membership" />
            <el-option label="课程费" value="course" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="currentPayment.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="支付方式" prop="paymentMethod">
          <el-input v-model="currentPayment.paymentMethod" />
        </el-form-item>
        <el-form-item label="关联ID" prop="referenceId">
          <el-input v-model="currentPayment.referenceId" disabled />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="currentPayment.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpdate">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import paymentApi from '@/api/payments';

// 数据状态
const payments = ref([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);
const total = ref(0);
const dateRange = ref([]);

// 对话框状态
const showCreateDialog = ref(false);
const showEditDialog = ref(false);

// 表单数据
const filterParams = reactive({
  memberId: '',
  type: '',
  startDate: '',
  endDate: ''
});

const newPayment = reactive({
  memberId: '',
  type: '',
  amount: 0,
  paymentMethod: '',
  referenceId: '',
  description: ''
});

const currentPayment = reactive({
  id: '',
  memberId: '',
  type: '',
  amount: 0,
  paymentMethod: '',
  referenceId: '',
  description: ''
});

// 表单验证规则
const rules = {
  referenceId: [{ required: true, message: '请输入关联ID', trigger: 'blur' }],
  memberId: [{ required: true, message: '请输入会员ID', trigger: 'blur' }],
  type: [{ required: true, message: '请选择支付类型', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  paymentMethod: [{ required: true, message: '请输入支付方式', trigger: 'blur' }]
  referenceId: [{ required: true, message: '请输入关联ID', trigger: 'blur' }],
};

// 获取支付记录
const fetchPayments = async () => {
  loading.value = true;
  try {
    const params = {
      ...filterParams,
      page: currentPage.value,
      limit: pageSize.value
    };
    const data = await paymentApi.getPayments(params);
    payments.value = data.items;
    total.value = data.total;
  } catch (error) {
    ElMessage.error('获取支付记录失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// 处理日期范围变化
const handleDateChange = (dates) => {
  if (dates && dates.length === 2) {
    filterParams.startDate = dates[0];
    filterParams.endDate = dates[1];
  } else {
    filterParams.startDate = '';
    filterParams.endDate = '';
  }
};

// 重置筛选条件
const resetFilters = () => {
  filterParams.memberId = '';
  filterParams.type = '';
  filterParams.startDate = '';
  filterParams.endDate = '';
  dateRange.value = [];
  currentPage.value = 1;
  fetchPayments();
};

// 分页变化
const handlePageChange = (page) => {
  currentPage.value = page;
  fetchPayments();
};

// 编辑支付记录
const handleEdit = (payment) => {
  Object.assign(currentPayment, payment);
  showEditDialog.value = true;
};

// 更新支付记录
const handleUpdate = async () => {
  try {
    await paymentApi.updatePayment(currentPayment.id, {
      amount: currentPayment.amount,
      paymentMethod: currentPayment.paymentMethod,
      description: currentPayment.description
    });
    ElMessage.success('更新成功');
    showEditDialog.value = false;
    fetchPayments();
  } catch (error) {
    ElMessage.error('更新失败');
    console.error(error);
  }
};

// 删除支付记录
const handleDelete = (id) => {
  ElMessageBox.confirm('确定要删除这条支付记录吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      try {
        await paymentApi.deletePayment(id);
        ElMessage.success('删除成功');
        fetchPayments();
      } catch (error) {
        ElMessage.error('删除失败');
        console.error(error);
      }
    })
    .catch(() => {});
};

// 创建支付记录
const handleCreate = async () => {
  try {
    await paymentApi.createPayment(newPayment);
    ElMessage.success('创建成功');
    showCreateDialog.value = false;
    resetFilters();
    fetchPayments();
  } catch (error) {
    ElMessage.error('创建失败');
    console.error(error);
  }
};

// 初始化加载
onMounted(() => {
  fetchPayments();
});
</script>

<style scoped>
.payment-list-view {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.filter-container {
  margin-bottom: 20px;
}
.pagination {
  margin-top: 20px;
  text-align: right;
}
</style>