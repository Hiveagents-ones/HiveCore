<template>
  <div class="course-ranking-chart">
    <div class="chart-header">
      <h3>热门课程排行</h3>
      <div class="chart-controls">
        <el-select v-model="timeRange" @change="handleTimeRangeChange" size="small">
          <el-option label="最近7天" value="7d" />
          <el-option label="最近30天" value="30d" />
          <el-option label="最近90天" value="90d" />
        </el-select>
        <el-select v-model="sortBy" @change="handleSortChange" size="small">
          <el-option label="预约量" value="bookings" />
          <el-option label="收入" value="revenue" />
          <el-option label="评分" value="rating" />
        </el-select>
      </div>
    </div>
    
    <div ref="chartRef" class="chart-container" v-loading="loading"></div>
    
    <div class="chart-legend">
      <div class="legend-item">
        <span class="legend-color" style="background-color: #409EFF"></span>
        <span>预约量</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background-color: #67C23A"></span>
        <span>收入</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background-color: #E6A23C"></span>
        <span>评分</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { ElSelect, ElOption } from 'element-plus'
import { getCourseRanking } from '@/api/analytics'

const props = defineProps({
  shopId: {
    type: [String, Number],
    required: true
  }
})

const chartRef = ref(null)
const chartInstance = ref(null)
const loading = ref(false)
const timeRange = ref('30d')
const sortBy = ref('bookings')
const rankingData = ref([])

const initChart = () => {
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value)
    updateChart()
  }
}

const updateChart = () => {
  if (!chartInstance.value || !rankingData.value.length) return

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        const data = params[0]
        const course = rankingData.value[data.dataIndex]
        return `
          <div style="padding: 8px">
            <div style="font-weight: bold; margin-bottom: 4px">${course.name}</div>
            <div>预约量: ${course.bookings}次</div>
            <div>收入: ¥${course.revenue}</div>
            <div>评分: ${course.rating}分</div>
          </div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value) => {
          if (sortBy.value === 'revenue') {
            return `¥${value}`
          }
          if (sortBy.value === 'rating') {
            return `${value}分`
          }
          return value
        }
      }
    },
    yAxis: {
      type: 'category',
      data: rankingData.value.map(item => item.name),
      axisLabel: {
        interval: 0,
        width: 100,
        overflow: 'truncate'
      }
    },
    series: [
      {
        name: '课程排行',
        type: 'bar',
        data: rankingData.value.map(item => {
          let value = item[sortBy.value]
          if (sortBy.value === 'revenue') {
            value = parseFloat(value)
          }
          return {
            value,
            itemStyle: {
              color: sortBy.value === 'bookings' ? '#409EFF' : 
                     sortBy.value === 'revenue' ? '#67C23A' : '#E6A23C'
            }
          }
        }),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          formatter: (params) => {
            let value = params.value
            if (sortBy.value === 'revenue') {
              return `¥${value}`
            }
            if (sortBy.value === 'rating') {
              return `${value}分`
            }
            return value
          }
        }
      }
    ]
  }

  chartInstance.value.setOption(option)
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      shop_id: props.shopId,
      time_range: timeRange.value,
      sort_by: sortBy.value
    }
    const response = await getCourseRanking(params)
    rankingData.value = response.data || []
    updateChart()
  } catch (error) {
    console.error('Failed to fetch course ranking data:', error)
  } finally {
    loading.value = false
  }
}

const handleTimeRangeChange = () => {
  fetchData()
}

const handleSortChange = () => {
  fetchData()
}

const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

watch(() => props.shopId, () => {
  if (props.shopId) {
    fetchData()
  }
}, { immediate: true })

onMounted(() => {
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
.course-ranking-chart {
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
  font-weight: 600;
  color: #303133;
}

.chart-controls {
  display: flex;
  gap: 12px;
}

.chart-container {
  width: 100%;
  height: 400px;
  margin-bottom: 20px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>