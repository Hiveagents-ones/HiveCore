<template>
  <div class="booking-chart">
    <div class="chart-header">
      <h3>预约趋势分析</h3>
      <div class="chart-controls">
        <el-select v-model="timeRange" @change="handleTimeRangeChange" size="small">
          <el-option label="最近7天" value="7d" />
          <el-option label="最近30天" value="30d" />
          <el-option label="最近3个月" value="3m" />
          <el-option label="最近1年" value="1y" />
        </el-select>
        <el-button-group size="small">
          <el-button :type="chartType === 'line' ? 'primary' : ''" @click="chartType = 'line'">折线图</el-button>
          <el-button :type="chartType === 'bar' ? 'primary' : ''" @click="chartType = 'bar'">柱状图</el-button>
        </el-button-group>
      </div>
    </div>
    
    <div ref="chartRef" class="chart-container" v-loading="loading"></div>
    
    <div class="chart-stats">
      <div class="stat-item">
        <span class="stat-label">总预约数</span>
        <span class="stat-value">{{ totalBookings }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">日均预约</span>
        <span class="stat-value">{{ averageBookings }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">增长率</span>
        <span class="stat-value" :class="growthRate >= 0 ? 'positive' : 'negative'">
          {{ growthRate >= 0 ? '+' : '' }}{{ growthRate }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getBookingAnalytics } from '@/api/analytics'

const props = defineProps({
  shopId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['dataUpdate'])

const chartRef = ref(null)
const chartInstance = ref(null)
const loading = ref(false)
const timeRange = ref('30d')
const chartType = ref('line')
const chartData = ref([])
const totalBookings = ref(0)
const averageBookings = ref(0)
const growthRate = ref(0)

const initChart = () => {
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value)
    updateChart()
    
    // 添加响应式处理
    window.addEventListener('resize', handleResize)
  }
}

const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

const updateChart = () => {
  if (!chartInstance.value || !chartData.value.length) return
  
  const dates = chartData.value.map(item => item.date)
  const bookings = chartData.value.map(item => item.bookings)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const data = params[0]
        return `${data.axisValue}<br/>预约数: ${data.value}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      },
      axisLabel: {
        color: '#666'
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      },
      axisLabel: {
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      }
    },
    series: [{
      name: '预约数',
      type: chartType.value,
      smooth: true,
      data: bookings,
      itemStyle: {
        color: '#409EFF'
      },
      areaStyle: chartType.value === 'line' ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      } : null,
      emphasis: {
        focus: 'series'
      }
    }]
  }
  
  chartInstance.value.setOption(option)
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getBookingAnalytics({
      shopId: props.shopId,
      timeRange: timeRange.value
    })
    
    chartData.value = response.data || []
    calculateStats()
    await nextTick()
    updateChart()
    
    emit('dataUpdate', {
      totalBookings: totalBookings.value,
      averageBookings: averageBookings.value,
      growthRate: growthRate.value
    })
  } catch (error) {
    console.error('Failed to fetch booking analytics:', error)
    ElMessage.error('获取预约数据失败')
  } finally {
    loading.value = false
  }
}

const calculateStats = () => {
  if (!chartData.value.length) {
    totalBookings.value = 0
    averageBookings.value = 0
    growthRate.value = 0
    return
  }
  
  totalBookings.value = chartData.value.reduce((sum, item) => sum + item.bookings, 0)
  averageBookings.value = Math.round(totalBookings.value / chartData.value.length)
  
  // 计算增长率（对比上一个周期）
  const halfLength = Math.floor(chartData.value.length / 2)
  const firstHalf = chartData.value.slice(0, halfLength)
  const secondHalf = chartData.value.slice(halfLength)
  
  const firstHalfTotal = firstHalf.reduce((sum, item) => sum + item.bookings, 0)
  const secondHalfTotal = secondHalf.reduce((sum, item) => sum + item.bookings, 0)
  
  if (firstHalfTotal > 0) {
    growthRate.value = Math.round(((secondHalfTotal - firstHalfTotal) / firstHalfTotal) * 100)
  } else {
    growthRate.value = secondHalfTotal > 0 ? 100 : 0
  }
}

const handleTimeRangeChange = () => {
  fetchData()
}

watch(chartType, () => {
  updateChart()
})

watch(() => props.shopId, () => {
  if (props.shopId) {
    fetchData()
  }
})

onMounted(() => {
  initChart()
  if (props.shopId) {
    fetchData()
  }
})

onUnmounted(() => {
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.booking-chart {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.chart-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 400px;
  margin-bottom: 20px;
}

.chart-stats {
  display: flex;
  justify-content: space-around;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-value.positive {
  color: #67c23a;
}

.stat-value.negative {
  color: #f56c6c;
}
</style>