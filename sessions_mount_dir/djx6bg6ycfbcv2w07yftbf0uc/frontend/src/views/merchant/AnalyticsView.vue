<template>
  <div class="analytics-view">
    <div class="page-header">
      <h1>数据统计</h1>
      <div class="date-filter">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleDateChange"
          :shortcuts="dateShortcuts"
        />
      </div>
    </div>

    <div class="summary-cards" v-loading="summaryLoading">
      <el-row :gutter="20">
        <el-col :span="6" v-for="card in summaryCards" :key="card.key">
          <el-card class="summary-card" :body-style="{ padding: '20px' }">
            <div class="card-content">
              <div class="card-icon" :style="{ backgroundColor: card.color }">
                <el-icon><component :is="card.icon" /></el-icon>
              </div>
              <div class="card-info">
                <div class="card-title">{{ card.title }}</div>
                <div class="card-value">{{ card.value }}</div>
                <div class="card-trend" :class="card.trend > 0 ? 'up' : 'down'">
                  <el-icon><ArrowUp v-if="card.trend > 0" /><ArrowDown v-else /></el-icon>
                  {{ Math.abs(card.trend) }}%
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="charts-container">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>课程预约量</span>
                <el-button-group>
                  <el-button
                    size="small"
                    :type="bookingPeriod === 'week' ? 'primary' : ''"
                    @click="changeBookingPeriod('week')"
                  >
                    周
                  </el-button>
                  <el-button
                    size="small"
                    :type="bookingPeriod === 'month' ? 'primary' : ''"
                    @click="changeBookingPeriod('month')"
                  >
                    月
                  </el-button>
                </el-button-group>
              </div>
            </template>
            <BookingChart :data="bookingData" :loading="bookingLoading" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>会员增长趋势</span>
              </div>
            </template>
            <MemberChart :data="memberData" :loading="memberLoading" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>热门课程排行</span>
              </div>
            </template>
            <CourseRankingChart :data="courseRankingData" :loading="courseRankingLoading" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="card-header">
                <span>收入统计</span>
              </div>
            </template>
            <RevenueChart :data="revenueData" :loading="revenueLoading" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Calendar, User, TrendCharts, Money, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import analyticsService from '@/services/analytics'
import BookingChart from '@/components/charts/BookingChart.vue'
import MemberChart from '@/components/charts/MemberChart.vue'
import CourseRankingChart from '@/components/charts/CourseRankingChart.vue'
import RevenueChart from '@/components/charts/RevenueChart.vue'

const dateRange = ref([])
const bookingPeriod = ref('week')

const summaryLoading = ref(false)
const bookingLoading = ref(false)
const memberLoading = ref(false)
const courseRankingLoading = ref(false)
const revenueLoading = ref(false)

const summaryData = ref({})
const bookingData = ref([])
const memberData = ref([])
const courseRankingData = ref([])
const revenueData = ref([])

const dateShortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    },
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    },
  },
  {
    text: '最近90天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    },
  },
]

const summaryCards = computed(() => [
  {
    key: 'totalBookings',
    title: '总预约量',
    value: summaryData.value.totalBookings || 0,
    trend: summaryData.value.bookingTrend || 0,
    icon: 'Calendar',
    color: '#409EFF',
  },
  {
    key: 'totalMembers',
    title: '总会员数',
    value: summaryData.value.totalMembers || 0,
    trend: summaryData.value.memberTrend || 0,
    icon: 'User',
    color: '#67C23A',
  },
  {
    key: 'totalRevenue',
    title: '总收入',
    value: `¥${summaryData.value.totalRevenue || 0}`,
    trend: summaryData.value.revenueTrend || 0,
    icon: 'Money',
    color: '#E6A23C',
  },
  {
    key: 'avgBooking',
    title: '平均预约',
    value: summaryData.value.avgBooking || 0,
    trend: summaryData.value.avgBookingTrend || 0,
    icon: 'TrendCharts',
    color: '#F56C6C',
  },
])

const handleDateChange = async (dates) => {
  if (dates && dates.length === 2) {
    await fetchAllData()
  }
}

const changeBookingPeriod = async (period) => {
  bookingPeriod.value = period
  await fetchBookingData()
}

const fetchSummaryData = async () => {
  try {
    summaryLoading.value = true
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    const data = await analyticsService.getDashboardSummary(params)
    summaryData.value = data
  } catch (error) {
    ElMessage.error(error.message || '获取概览数据失败')
  } finally {
    summaryLoading.value = false
  }
}

const fetchBookingData = async () => {
  try {
    bookingLoading.value = true
    const params = { period: bookingPeriod.value }
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    const data = await analyticsService.getBookingStats(params)
    bookingData.value = data
  } catch (error) {
    ElMessage.error(error.message || '获取预约数据失败')
  } finally {
    bookingLoading.value = false
  }
}

const fetchMemberData = async () => {
  try {
    memberLoading.value = true
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    const data = await analyticsService.getMemberGrowth(params)
    memberData.value = data
  } catch (error) {
    ElMessage.error(error.message || '获取会员数据失败')
  } finally {
    memberLoading.value = false
  }
}

const fetchCourseRankingData = async () => {
  try {
    courseRankingLoading.value = true
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    const data = await analyticsService.getCourseRanking(params)
    courseRankingData.value = data
  } catch (error) {
    ElMessage.error(error.message || '获取课程排行数据失败')
  } finally {
    courseRankingLoading.value = false
  }
}

const fetchRevenueData = async () => {
  try {
    revenueLoading.value = true
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0].toISOString()
      params.endDate = dateRange.value[1].toISOString()
    }
    const data = await analyticsService.getRevenueStats(params)
    revenueData.value = data
  } catch (error) {
    ElMessage.error(error.message || '获取收入数据失败')
  } finally {
    revenueLoading.value = false
  }
}

const fetchAllData = async () => {
  await Promise.all([
    fetchSummaryData(),
    fetchBookingData(),
    fetchMemberData(),
    fetchCourseRankingData(),
    fetchRevenueData(),
  ])
}

onMounted(async () => {
  const end = new Date()
  const start = new Date()
  start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
  dateRange.value = [start, end]
  await fetchAllData()
})
</script>

<style scoped>
.analytics-view {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.summary-cards {
  margin-bottom: 20px;
}

.summary-card {
  height: 120px;
}

.card-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  color: white;
  font-size: 24px;
}

.card-info {
  flex: 1;
}

.card-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.card-trend {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-trend.up {
  color: #67c23a;
}

.card-trend.down {
  color: #f56c6c;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-card {
  height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}
</style>