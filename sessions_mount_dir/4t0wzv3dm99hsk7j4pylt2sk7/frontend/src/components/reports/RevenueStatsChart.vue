<template>
  <div class="revenue-stats-chart">
    <div class="chart-header">
      <h3>收入统计</h3>
      <span class="total-revenue">总收入: ¥{{ totalRevenue.toFixed(2) }}</span>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getRevenueStats } from '@/api/reports'

export default {
  name: 'RevenueStatsChart',
  props: {
    timeRange: {
      type: Number,
      required: true
    },
    dimension: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const chartRef = ref(null)
    const chartInstance = ref(null)
    const totalRevenue = ref(0)
    
    const initChart = () => {
      if (chartRef.value) {
        chartInstance.value = echarts.init(chartRef.value)
      }
    }
    
    const loadData = async () => {
      try {
        const response = await getRevenueStats({
          days: props.timeRange,
          dimension: props.dimension
        })
        
        totalRevenue.value = response.total_revenue
        
        const option = {
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'cross'
            }
          },
          legend: {
            data: ['收入趋势']
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            data: response.dates
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: '¥{value}'
            }
          },
          series: [
            {
              name: '收入趋势',
              type: 'line',
              smooth: true,
              lineStyle: {
                color: '#F56C6C',
                width: 3
              },
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(245, 108, 108, 0.5)' },
                  { offset: 1, color: 'rgba(245, 108, 108, 0.1)' }
                ])
              },
              data: response.revenues
            }
          ]
        }
        
        chartInstance.value.setOption(option)
      } catch (error) {
        console.error('加载收入统计数据失败:', error)
      }
    }
    
    const refreshChart = () => {
      loadData()
    }
    
    watch([() => props.timeRange, () => props.dimension], () => {
      loadData()
    })
    
    onMounted(() => {
      initChart()
      loadData()
      
      window.addEventListener('resize', () => {
        chartInstance.value?.resize()
      })
    })
    
    return {
      chartRef,
      totalRevenue,
      refreshChart
    }
  }
}
</script>

<style scoped>
.revenue-stats-chart {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.total-revenue {
  font-size: 14px;
  color: #F56C6C;
  font-weight: bold;
}

.chart-container {
  flex: 1;
  min-height: 0;
}
</style>