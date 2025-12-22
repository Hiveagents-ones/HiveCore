<template>
  <div class="activity-trend-chart">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useAnalyticsStore } from '../services/analytics'

const props = defineProps({
  timeRange: {
    type: String,
    default: '7d'
  },
  height: {
    type: String,
    default: '400px'
  }
})

const chartRef = ref(null)
let chartInstance = null
const analyticsStore = useAnalyticsStore()

const initChart = () => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
}

const updateChart = () => {
  if (!chartInstance) return

  const option = {
    title: {
      text: '平台活跃度趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['日活跃用户', '周活跃用户', '月活跃用户'],
      top: 30
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
      data: analyticsStore.activityTrendData.dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '日活跃用户',
        type: 'line',
        stack: 'Total',
        smooth: true,
        data: analyticsStore.activityTrendData.dau,
        itemStyle: {
          color: '#5470c6'
        }
      },
      {
        name: '周活跃用户',
        type: 'line',
        stack: 'Total',
        smooth: true,
        data: analyticsStore.activityTrendData.wau,
        itemStyle: {
          color: '#91cc75'
        }
      },
      {
        name: '月活跃用户',
        type: 'line',
        stack: 'Total',
        smooth: true,
        data: analyticsStore.activityTrendData.mau,
        itemStyle: {
          color: '#fac858'
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch(() => props.timeRange, async () => {
  await analyticsStore.fetchActivityTrendData(props.timeRange)
  updateChart()
})

watch(() => analyticsStore.activityTrendData, () => {
  updateChart()
}, { deep: true })

onMounted(async () => {
  await analyticsStore.fetchActivityTrendData(props.timeRange)
  initChart()
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
.activity-trend-chart {
  width: 100%;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-container {
  width: 100%;
  height: v-bind(height);
}
</style>