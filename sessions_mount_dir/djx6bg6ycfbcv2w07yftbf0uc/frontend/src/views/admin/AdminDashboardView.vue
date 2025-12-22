<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <h1>平台数据统计</h1>
      <p class="header-desc">实时监控平台核心数据，洞察业务增长趋势</p>
    </div>

    <!-- 全局筛选器 -->
    <GlobalFilter
      :loading="loading"
      @filter="handleFilter"
      @reset="handleReset"
    />

    <!-- KPI 卡片区域 -->
    <el-row :gutter="20" class="kpi-section">
      <el-col :xs="24" :sm="12" :md="6" v-for="kpi in kpiData" :key="kpi.key">
        <KpiCard
          :title="kpi.title"
          :value="kpi.value"
          :icon="kpi.icon"
          :trend="kpi.trend"
          :footer="kpi.footer"
          :format="kpi.format"
        />
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-section">
      <el-col :span="24">
        <el-card>
          <ActivityTrendChart :time-range="timeRange" height="400px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格区域 -->
    <el-row :gutter="20" class="table-section">
      <el-col :span="24">
        <DetailDataTable
          title="热门课程排行"
          :data="tableData"
          :columns="tableColumns"
          :loading="tableLoading"
          :total="tableTotal"
          :current-page="currentPage"
          :page-size="pageSize"
          @update:currentPage="handlePageChange"
          @update:pageSize="handlePageSizeChange"
          @sort-change="handleSortChange"
          @export="handleExport"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getPlatformCoreStats,
  getUserActivityAnalysis,
  getMerchantActivityAnalysis,
  getCourseSalesStats,
  getRevenueTrends,
  getUserRegistrationTrends,
  getMerchantOnboardingTrends,
  getCoursePublishingTrends,
  getTopCourses
} from '@/services/analytics'
import KpiCard from '@/components/KpiCard.vue'
import GlobalFilter from '@/components/GlobalFilter.vue'
import ActivityTrendChart from '@/components/ActivityTrendChart.vue'
import DetailDataTable from '@/components/DetailDataTable.vue'

// 响应式数据
const loading = ref(false)
const timeRange = ref('7d')
const filterParams = reactive({
  startDate: '',
  endDate: ''
})

// KPI 数据
const kpiData = ref([
  {
    key: 'users',
    title: '用户总数',
    value: 0,
    icon: 'User',
    trend: 0,
    footer: '累计注册用户',
    format: 'number'
  },
  {
    key: 'merchants',
    title: '商家总数',
    value: 0,
    icon: 'Shop',
    trend: 0,
    footer: '入驻商家数量',
    format: 'number'
  },
  {
    key: 'courses',
    title: '课程总数',
    value: 0,
    icon: 'Reading',
    trend: 0,
    footer: '已发布课程',
    format: 'number'
  },
  {
    key: 'revenue',
    title: '平台总收入',
    value: 0,
    icon: 'Money',
    trend: 0,
    footer: '累计交易金额',
    format: 'currency'
  }
])

// 表格数据
const tableLoading = ref(false)
const tableData = ref([])
const tableTotal = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const tableColumns = [
  { prop: 'rank', label: '排名', width: 80, sortable: true },
  { prop: 'courseName', label: '课程名称', width: 200 },
  { prop: 'merchantName', label: '商家', width: 150 },
  { prop: 'sales', label: '销量', width: 100, sortable: true },
  { prop: 'revenue', label: '收入', width: 120, sortable: true, formatter: formatCurrency },
  { prop: 'rating', label: '评分', width: 100, sortable: true },
  { prop: 'students', label: '学生数', width: 100, sortable: true }
]

// 方法
const formatCurrency = (row, column, cellValue) => {
  return `¥${cellValue.toLocaleString()}`
}

const fetchCoreStats = async () => {
  try {
    const response = await getPlatformCoreStats()
    const data = response.data
    
    kpiData.value = kpiData.value.map(kpi => {
      const key = kpi.key
      return {
        ...kpi,
        value: data[`${key}Total`] || 0,
        trend: data[`${key}Trend`] || 0
      }
    })
  } catch (error) {
    ElMessage.error('获取核心统计数据失败')
  }
}

const fetchTopCourses = async () => {
  tableLoading.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
      ...filterParams
    }
    const response = await getTopCourses(params)
    tableData.value = response.data.items || []
    tableTotal.value = response.data.total || 0
  } catch (error) {
    ElMessage.error('获取热门课程数据失败')
  } finally {
    tableLoading.value = false
  }
}

const handleFilter = (params) => {
  Object.assign(filterParams, params)
  currentPage.value = 1
  fetchAllData()
}

const handleReset = () => {
  Object.keys(filterParams).forEach(key => {
    filterParams[key] = ''
  })
  currentPage.value = 1
  fetchAllData()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchTopCourses()
}

const handlePageSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTopCourses()
}

const handleSortChange = ({ prop, order }) => {
  // 处理排序逻辑
  fetchTopCourses()
}

const handleExport = async () => {
  try {
    const params = {
      ...filterParams,
      export: true
    }
    await getTopCourses(params)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const fetchAllData = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchCoreStats(),
      fetchTopCourses()
    ])
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  fetchAllData()
})
</script>

<style scoped>
.admin-dashboard {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  margin-bottom: 20px;
}

.dashboard-header h1 {
  font-size: 24px;
  color: #303133;
  margin: 0 0 8px 0;
}

.header-desc {
  color: #909399;
  margin: 0;
}

.kpi-section {
  margin-bottom: 20px;
}

.chart-section {
  margin-bottom: 20px;
}

.table-section {
  margin-bottom: 20px;
}
</style>