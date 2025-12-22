<template>
  <div class="member-trend-chart">
    <div class="chart-header">
      <h3>会员增长趋势</h3>
      <span class="total-count">总会员: {{ totalMembers }}</span>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getMemberTrend } from '@/api/reports'

export default {
  name: 'MemberTrendChart',
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
    const totalMembers = ref(0)
    
    const initChart = () => {
      if (chartRef.value) {
        chartInstance.value = echarts.init(chartRef.value)
      }
    }
    
    const loadData = async () => {
      try {
        const response = await getMemberTrend({
          days: props.timeRange,
          dimension: props.dimension
        })
        
        totalMembers.value = response.total_members
        
        const option = {
          tooltip: {
            trigger: 'axis'
          },
          legend: {
            data: ['新增会员']
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
            data: response.dates
          },
          yAxis: {
            type: 'value'
          },
          series: [
            {
              name: '新增会员',
              type: 'line',
              stack: 'Total',
              smooth: true,
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
                  { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
                ])
              },
              lineStyle: {
                color: '#409EFF'
              },
              data: response.new_members
            }
          ]
        }
        
        chartInstance.value.setOption(option)
      } catch (error) {
        console.error('加载会员趋势数据失败:', error)
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
      totalMembers,
      refreshChart
    }
  }
}
</script>

<style scoped>
.member-trend-chart {
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

.total-count {
  font-size: 14px;
  color: #666;
}

.chart-container {
  flex: 1;
  min-height: 0;
}
</style>