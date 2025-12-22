<template>
  <div class="payment-monitoring-container">
    <el-card class="dashboard-card">
      <template #header>
        <div class="card-header">
          <span>支付监控仪表盘</span>
          <div class="header-actions">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="fetchPaymentData"
            />
            <el-button type="primary" @click="exportReport">导出报表</el-button>
          <el-button type="success" @click="showCalculator">费用计算器</el-button>
          <el-select v-model="selectedPaymentType" placeholder="支付类型" style="width: 120px" @change="fetchPaymentData">
            <el-option
              v-for="item in paymentTypes"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          </div>
        </div>
      </template>

      <div class="metrics-row">
    <el-row :gutter="20" class="observability-row">
      <el-col :span="6">
        <metric-card 
          title="支付成功率" 
          :value="observabilityData.successRate + '%'" 
          icon="SuccessFilled"
          color="#67C23A"
        />
      </el-col>
      <el-col :span="6">
        <metric-card 
          title="平均响应时间" 
          :value="observabilityData.avgResponseTime + 'ms'" 
          icon="Clock"
          color="#409EFF"
        />
      </el-col>
      <el-col :span="6">
        <metric-card 
          title="错误次数" 
          :value="observabilityData.errorCount" 
          icon="Warning"
          color="#F56C6C"
        />
      </el-col>
      <el-col :span="6">
        <metric-card 
          title="高峰时段" 
          :value="observabilityData.peakHour" 
          icon="TrendCharts"
          color="#E6A23C"
        />
      </el-col>
    </el-row>
        <el-row :gutter="20">
          <el-col :span="6">
            <metric-card 
              title="总收入" 
              :value="metrics.totalIncome" 
              icon="Money"
              color="#67C23A"
            />
          </el-col>
          <el-col :span="6">
            <metric-card 
              title="会员费" 
              :value="metrics.membershipIncome" 
              icon="User"
              color="#409EFF"
            />
          </el-col>
          <el-col :span="6">
            <metric-card 
              title="课程费" 
              :value="metrics.courseIncome" 
              icon="Reading"
              color="#E6A23C"
            />
          </el-col>
          <el-col :span="6">
            <metric-card 
              title="支付次数" 
              :value="metrics.paymentCount" 
              icon="Document"
              color="#F56C6C"
            />
          </el-col>
        </el-row>
      </div>

      <div class="chart-row">
        <el-row :gutter="20">
          <el-col :span="12">
            <line-chart 
              title="每日收入趋势" 
              :data="incomeTrendData" 
              :loading="chartLoading"
            />
          </el-col>
          <el-col :span="12">
            <pie-chart 
              title="收入构成" 
              :data="incomeCompositionData" 
              :loading="chartLoading"
            />
          </el-col>
        </el-row>
      </div>

      <div class="payment-table">
        <el-table 
          :data="paymentRecords" 
          v-loading="tableLoading"
          style="width: 100%"
          border
        >
          <el-table-column prop="id" label="支付ID" width="100" />
          <el-table-column prop="memberName" label="会员" />
          <el-table-column prop="amount" label="金额(元)" width="120">
          <template #default="scope">
            {{ scope.row.amount.toFixed(2) }}
          </template>
        </el-table-column>
          <el-table-column prop="paymentType" label="类型" width="120" />
          <el-table-column prop="paymentDate" label="支付时间" width="180" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button 
                size="small" 
                @click="showDetail(scope.row)"
              >详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          class="pagination"
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalRecords"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchPaymentData"
          @current-change="fetchPaymentData"
        />
      </div>
    </el-card>

    <payment-detail-dialog 
      v-model="detailDialogVisible" 
      :payment-id="selectedPaymentId"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import MetricCard from '../components/MetricCard.vue'
import LineChart from '../components/LineChart.vue'
import PieChart from '../components/PieChart.vue'
import PaymentDetailDialog from '../components/PaymentDetailDialog.vue'
import { getPayments, getPaymentMetrics, exportPaymentsReport } from '../api/payment'
import { getPaymentObservability } from '../api/observability'
import PaymentCalculator from '../components/PaymentCalculator.vue'
const paymentTypes = [
  { label: '全部', value: '' },
  { label: '会员费', value: 'membership' },
  { label: '课程费', value: 'course' },
  { label: '其他', value: 'other' }
]

const dateRange = ref([
const selectedPaymentType = ref('')
  new Date(new Date().setDate(new Date().getDate() - 30)),
  new Date()
])

const metrics = ref({
  totalIncome: 0,
  membershipIncome: 0,
  courseIncome: 0,
  paymentCount: 0
})

const incomeTrendData = ref([])
const incomeCompositionData = ref([])
const paymentRecords = ref([])

const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = ref(0)

const chartLoading = ref(false)
const tableLoading = ref(false)
const detailDialogVisible = ref(false)
const selectedPaymentId = ref(null)
const calculatorVisible = ref(false)
const observabilityData = ref({
  successRate: 0,
  avgResponseTime: 0,
  errorCount: 0,
  peakHour: ''
})
const showCalculator = () => {
  calculatorVisible.value = true
}

const fetchObservabilityData = async () => {
  try {
    const response = await getPaymentObservability()
    observabilityData.value = response.data
  } catch (error) {
    ElMessage.error('获取可观测性数据失败: ' + error.message)
  }
}
  calculatorVisible.value = true
}

const fetchPaymentData = async () => {
  try {
    chartLoading.value = true
    tableLoading.value = true
    
    const [startDate, endDate] = dateRange.value
    const params = {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
      paymentType: selectedPaymentType.value,
      page: currentPage.value,
      pageSize: pageSize.value
    }
    
    // 获取指标数据
    const metricsResponse = await getPaymentMetrics(params)
    metrics.value = metricsResponse.data
    
    // 获取图表数据
    incomeTrendData.value = metricsResponse.data.dailyTrend
    incomeCompositionData.value = [
      { name: '会员费', value: metricsResponse.data.membershipIncome },
      { name: '课程费', value: metricsResponse.data.courseIncome },
      { name: '其他', value: metricsResponse.data.otherIncome }
    ]
    
    // 获取支付记录
    const recordsResponse = await getPayments(params)
    paymentRecords.value = recordsResponse.data.items
    totalRecords.value = recordsResponse.data.total
  } catch (error) {
    ElMessage.error('获取支付数据失败: ' + error.message)
  } finally {
    chartLoading.value = false
    tableLoading.value = false
  }
}

const exportReport = async () => {
  try {
    const [startDate, endDate] = dateRange.value
    const params = {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    }
    
    await exportPaymentsReport(params)
    ElMessage.success('报表导出成功，请查看下载文件夹')
  } catch (error) {
    ElMessage.error('导出报表失败: ' + error.message)
  }
}

const showDetail = (payment) => {
  selectedPaymentId.value = payment.id
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchPaymentData()
  fetchObservabilityData()
  fetchPaymentData()
})
</script>

<style scoped>
.payment-monitoring-container {
  padding: 20px;
}

.dashboard-card {
  min-height: calc(100vh - 100px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.metrics-row {
  margin-bottom: 20px;
}

.observability-row {
  margin-bottom: 20px;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}
  margin-bottom: 20px;
}

.chart-row {
  margin-bottom: 20px;
}

.payment-table {
  margin-top: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

    <payment-calculator 
      v-model="calculatorVisible"
    />