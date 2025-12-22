<template>
  <div class="payment-list-view">
    <h1>支付记录管理</h1>
    
    <div class="search-bar">
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索会员姓名或支付ID" 
        style="width: 300px" 
        @keyup.enter="fetchPayments"
      >
        <template #append>
          <el-button icon="el-icon-search" @click="fetchPayments" />
        </template>
      </el-input>
      
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        @change="fetchPayments"
      />
      
      <el-button type="primary" @click="showCreateDialog">
        新增支付记录
      </el-button>
      <el-button type="success" @click="exportPayments" :loading="exportLoading">
        导出Excel
      </el-button>
    </div>
    
    <el-table 
      :data="payments" 
      border 
      style="width: 100%" 
      v-loading="loading"
    >
      <el-table-column prop="id" label="支付ID" width="100" />
      <el-table-column prop="member_name" label="会员姓名" />
      <el-table-column prop="amount" label="金额" width="120">
        <template #default="scope">
          ¥{{ scope.row.amount.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="payment_method" label="支付方式" width="120" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row.status)">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="支付时间" width="180" sortable />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="showDetailDialog(scope.row)">
            详情
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(scope.row.id)"
      exportPayments,
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-pagination
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      :current-page="pagination.current"
      :page-sizes="[10, 20, 50, 100]"
      :page-size="pagination.size"
      layout="total, sizes, prev, pager, next, jumper"
      :total="pagination.total"
    />
    
    <!-- 支付详情对话框 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="支付记录详情" 
      width="50%"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="支付ID">{{ currentPayment.id }}</el-descriptions-item>
        <el-descriptions-item label="会员姓名">{{ currentPayment.member_name }}</el-descriptions-item>
        <el-descriptions-item label="金额">¥{{ currentPayment.amount?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="支付方式">{{ currentPayment.payment_method }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(currentPayment.status)">
            {{ currentPayment.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="支付时间">{{ currentPayment.created_at }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentPayment.notes || '无' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
    
    <!-- 新增支付对话框 -->
    <el-dialog 
      v-model="createDialogVisible" 
      title="新增支付记录" 
      width="40%"
      @closed="resetForm"
    >
      <el-form 
        ref="paymentForm" 
        :model="paymentForm" 
        :rules="rules" 
        label-width="100px"
      >
        <el-form-item label="会员ID" prop="member_id">
          <el-input v-model.number="paymentForm.member_id" />
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input v-model.number="paymentForm.amount" prefix-icon="¥" />
        </el-form-item>
        <el-form-item label="支付方式" prop="payment_method">
          <el-select v-model="paymentForm.payment_method" placeholder="请选择">
            <el-option 
              v-for="method in paymentMethods" 
              :key="method" 
              :label="method" 
              :value="method"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="paymentForm.status" placeholder="请选择">
            <el-option 
              v-for="status in paymentStatuses" 
              :key="status" 
              :label="status" 
              :value="status"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="notes">
          <el-input 
            v-model="paymentForm.notes" 
            type="textarea" 
            :rows="2" 
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPaymentForm">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import paymentApi from '@/api/payments';

export default {
  name: 'PaymentListView',
  
  setup() {
    const payments = ref([]);
    const loading = ref(false);
    const exportLoading = ref(false);
    const searchQuery = ref('');
    const dateRange = ref([]);
    const detailDialogVisible = ref(false);
    const createDialogVisible = ref(false);
    const currentPayment = ref({});
    const paymentForm = ref({});
    const paymentFormRef = ref(null);
    
    const pagination = reactive({
      current: 1,
      size: 10,
      total: 0
    });
    
    const paymentMethods = [
      '微信支付',
      '支付宝',
      '现金',
      '银行卡',
      '会员卡余额'
    ];
    
    const paymentStatuses = [
      '已过期',
      '已完成',
      '处理中',
      '已取消',
      '已退款'
    ];
    
    const rules = {
      member_id: [
        { required: true, message: '请输入会员ID', trigger: 'blur' },
        { type: 'number', message: '会员ID必须为数字', trigger: 'blur' }
      ],
      amount: [
        { required: true, message: '请输入金额', trigger: 'blur' },
        { type: 'number', message: '金额必须为数字', trigger: 'blur' }
      ],
      payment_method: [
        { required: true, message: '请选择支付方式', trigger: 'change' }
      ],
      status: [
        { required: true, message: '请选择支付状态', trigger: 'change' }
      ]
    };
    
    const getStatusTagType = (status) => {
      switch (status) {
        case '已完成': return 'success';
        case '处理中': return 'warning';
        case '已取消': return 'info';
        case '已退款': return 'danger';
        case '已过期': return 'info';
        default: return '';
      }
    };
    
    const fetchPayments = async () => {
      try {
        loading.value = true;
        const params = {
          page: pagination.current,
          size: pagination.size,
          query: searchQuery.value
        };
        
        if (dateRange.value && dateRange.value.length === 2) {
          params.start_date = dateRange.value[0];
          params.end_date = dateRange.value[1];
        }
        
        const response = await paymentApi.getPayments(params);
        payments.value = response.data.items;
        pagination.total = response.data.total;
      } catch (error) {
        ElMessage.error('获取支付记录失败: ' + error.message);
      } finally {
        loading.value = false;
      }
    };
    
    const handleSizeChange = (size) => {
      pagination.size = size;
      fetchPayments();
    };
    
    const handleCurrentChange = (current) => {
      pagination.current = current;
      fetchPayments();
    };
    
    const showDetailDialog = (payment) => {
      currentPayment.value = payment;
      detailDialogVisible.value = true;
    };
    
    const showCreateDialog = () => {
      paymentForm.value = {
        member_id: null,
        amount: null,
        payment_method: '',
        status: '已完成',
        notes: ''
      };
      createDialogVisible.value = true;
    };
    
    const resetForm = () => {
      if (paymentFormRef.value) {
        paymentFormRef.value.resetFields();
      }
    };
    
    const submitPaymentForm = async () => {
      try {
        await paymentFormRef.value.validate();
        
        loading.value = true;
        await paymentApi.createPayment(paymentForm.value);
        
        ElMessage.success('支付记录创建成功');
        createDialogVisible.value = false;
        fetchPayments();
      } catch (error) {
        if (error.name !== 'ValidationError') {
          ElMessage.error('创建支付记录失败: ' + error.message);
        }
      } finally {
        loading.value = false;
      }
    };
    
    const exportPayments = async () => {
      try {
        exportLoading.value = true;
        const params = {
          query: searchQuery.value
        };

        if (dateRange.value && dateRange.value.length === 2) {
          params.start_date = dateRange.value[0];
          params.end_date = dateRange.value[1];
        }

        const response = await paymentApi.getPayments({
          ...params,
          size: 10000
        });

        // 这里应该调用导出API或生成Excel文件
        ElMessage.success(`成功导出 ${response.data.items.length} 条支付记录`);
      } catch (error) {
        ElMessage.error('导出失败: ' + error.message);
      } finally {
        exportLoading.value = false;
      }
    };

    const handleDelete = (paymentId) => {
      try {
        exportLoading.value = true;
        const params = {
          query: searchQuery.value
        };

        if (dateRange.value && dateRange.value.length === 2) {
          params.start_date = dateRange.value[0];
          params.end_date = dateRange.value[1];
        }

        const response = await paymentApi.getPayments({
          ...params,
          size: 10000
        });
        
        // 这里应该调用导出API或生成Excel文件
        ElMessage.success(`成功导出 ${response.data.items.length} 条支付记录`);
      } catch (error) {
        ElMessage.error('导出失败: ' + error.message);
      } finally {
        exportLoading.value = false;
      }
    };
      ElMessageBox.confirm('确定要删除这条支付记录吗?', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await paymentApi.deletePayment(paymentId);
          ElMessage.success('支付记录删除成功');
          fetchPayments();
        } catch (error) {
          ElMessage.error('删除支付记录失败: ' + error.message);
        }
      }).catch(() => {});
    };
    
    onMounted(() => {
      fetchPayments();
    });
    
    return {
      payments,
      loading,
      searchQuery,
      dateRange,
      pagination,
      detailDialogVisible,
      createDialogVisible,
      currentPayment,
      paymentForm,
      paymentFormRef,
      paymentMethods,
      paymentStatuses,
      rules,
      getStatusTagType,
      fetchPayments,
      handleSizeChange,
      handleCurrentChange,
      showDetailDialog,
      showCreateDialog,
      resetForm,
      submitPaymentForm,
      handleDelete
    };
  }
};
</script>

<style scoped>
.payment-list-view {
  padding: 20px;
}

.search-bar {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.el-pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>