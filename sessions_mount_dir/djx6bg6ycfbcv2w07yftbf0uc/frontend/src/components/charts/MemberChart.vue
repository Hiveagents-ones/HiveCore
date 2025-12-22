<template>
  <div class="member-chart">
    <div class="chart-header">
      <h3>会员增长趋势</h3>
      <div class="chart-controls">
        <el-select v-model="timeRange" @change="handleTimeRangeChange" size="small">
          <el-option label="最近7天" value="7d" />
          <el-option label="最近30天" value="30d" />
          <el-option label="最近90天" value="90d" />
        </el-select>
        <el-switch
          v-model="showPrediction"
          active-text="显示预测"
          @change="handlePredictionToggle"
        />
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
    <div class="chart-footer">
      <div class="stat-item">
        <span class="label">当前会员数：</span>
        <span class="value">{{ currentMembers }}</span>
      </div>
      <div class="stat-item">
        <span class="label">增长率：</span>
        <span class="value" :class="growthRateClass">{{ growthRate }}%</span>
      </div>
      <div v-if="showPrediction" class="stat-item">
        <span class="label">预测30天后：</span>
        <span class="value">{{ predictedMembers }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getMemberAnalytics } from '@/api/analytics'

const chartRef = ref(null)
let chartInstance = null

const timeRange = ref('30d')
const showPrediction = ref(false)
const chartData = ref({
  dates: [],
  actual: [],
  prediction: []
})
const currentMembers = ref(0)
const growthRate = ref(0)
const predictedMembers = ref(0)

const growthRateClass = computed(() => {
  return growthRate.value >= 0 ? 'positive' : 'negative'
})

const initChart = () => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
}

const updateChart = () => {
  if (!chartInstance) return

  const series = [
    {
      name: '实际会员数',
      type: 'line',
      data: chartData.value.actual,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: '#409EFF'
      },
      itemStyle: {
        color: '#409EFF'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      }
    }
  ]

  if (showPrediction.value && chartData.value.prediction.length > 0) {
    series.push({
      name: '预测会员数',
      type: 'line',
      data: chartData.value.prediction,
      smooth: true,
      symbol: 'diamond',
      symbolSize: 6,
      lineStyle: {
        width: 2,
        type: 'dashed',
        color: '#67C23A'
      },
      itemStyle: {
        color: '#67C23A'
      }
    })
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: (params) => {
        let result = params[0].axisValue + '<br/>'
        params.forEach(param => {
          result += `${param.marker} ${param.seriesName}: ${param.value}<br/>`
        })
        return result
      }
    },
    legend: {
      data: ['实际会员数', '预测会员数'],
      top: 10
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
      data: chartData.value.dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series
  }

  chartInstance.setOption(option)
}

const fetchData = async () => {
  try {
    const response = await getMemberAnalytics({
      time_range: timeRange.value,
      include_prediction: showPrediction.value
    })
    
    chartData.value = {
      dates: response.data.dates,
      actual: response.data.actual,
      prediction: response.data.prediction || []
    }
    
    currentMembers.value = response.data.current_members
    growthRate.value = response.data.growth_rate
    predictedMembers.value = response.data.predicted_members || 0
    
    updateChart()
  } catch (error) {
    ElMessage.error('获取会员数据失败')
    console.error('Error fetching member analytics:', error)
  }
}

const handleTimeRangeChange = () => {
  fetchData()
}

const handlePredictionToggle = () => {
  fetchData()
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch([timeRange, showPrediction], () => {
  fetchData()
})

onMounted(() => {
  initChart()
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.member-chart {
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
  align-items: center;
  gap: 15px;
}

.chart-container {
  height: 400px;
  margin-bottom: 20px;
}

.chart-footer {
  display: flex;
  justify-content: space-around;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
}

.stat-item {
  text-align: center;
}

.stat-item .label {
  font-size: 14px;
  color: #909399;
  display: block;
  margin-bottom: 5px;
}

.stat-item .value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-item .value.positive {
  color: #67C23A;
}

.stat-item .value.negative {
  color: #F56C6C;
}
</style>