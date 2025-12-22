<template>
  <div class="revenue-chart">
    <div class="chart-header">
      <h3>收入统计</h3>
      <div class="chart-controls">
        <select v-model="timeRange" @change="fetchData">
          <option value="7">最近7天</option>
          <option value="30">最近30天</option>
          <option value="90">最近90天</option>
        </select>
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
    <div class="chart-summary">
      <div class="summary-item">
        <span class="label">总收入</span>
        <span class="value">{{ formatCurrency(totalRevenue) }}</span>
      </div>
      <div class="summary-item">
        <span class="label">日均收入</span>
        <span class="value">{{ formatCurrency(averageRevenue) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useAnalyticsStore } from '@/stores/analytics'

const chartRef = ref(null)
const chartInstance = ref(null)
const timeRange = ref('30')
const analyticsStore = useAnalyticsStore()

const chartData = ref({
  dates: [],
  revenues: []
})

const totalRevenue = ref(0)
const averageRevenue = ref(0)

// 脱敏处理：将金额转换为显示格式
const formatCurrency = (value) => {
  if (value >= 10000) {
    return `¥${(value / 10000).toFixed(1)}万`
  }
  return `¥${value.toFixed(2)}`
}

// 获取数据
const fetchData = async () => {
  try {
    const response = await analyticsStore.getRevenueData(timeRange.value)
    chartData.value = response.data
    
    // 计算统计数据
    totalRevenue.value = chartData.value.revenues.reduce((sum, val) => sum + val, 0)
    averageRevenue.value = totalRevenue.value / chartData.value.revenues.length
    
    updateChart()
  } catch (error) {
    console.error('获取收入数据失败:', error)
  }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance.value = echarts.init(chartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const date = params[0].axisValue
        const value = params[0].value
        return `${date}<br/>收入: ${formatCurrency(value)}`
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
      data: chartData.value.dates,
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
        color: '#666',
        formatter: (value) => {
          return formatCurrency(value)
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      }
    },
    series: [
      {
        name: '收入',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: {
          color: '#4f46e5'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: 'rgba(79, 70, 229, 0.3)'
              },
              {
                offset: 1,
                color: 'rgba(79, 70, 229, 0.05)'
              }
            ]
          }
        },
        data: chartData.value.revenues
      }
    ]
  }
  
  chartInstance.value.setOption(option)
}

// 更新图表
const updateChart = () => {
  if (!chartInstance.value) return
  
  const option = {
    xAxis: {
      data: chartData.value.dates
    },
    series: [
      {
        data: chartData.value.revenues
      }
    ]
  }
  
  chartInstance.value.setOption(option)
}

// 响应式处理
const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

onMounted(() => {
  fetchData()
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.revenue-chart {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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
  font-weight: 600;
  color: #333;
}

.chart-controls select {
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: white;
  color: #666;
  font-size: 14px;
  cursor: pointer;
}

.chart-controls select:focus {
  outline: none;
  border-color: #4f46e5;
}

.chart-container {
  width: 100%;
  height: 300px;
  margin-bottom: 20px;
}

.chart-summary {
  display: flex;
  gap: 40px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item .label {
  font-size: 14px;
  color: #666;
}

.summary-item .value {
  font-size: 20px;
  font-weight: 600;
  color: #333;
}
</style>