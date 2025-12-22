<template>
  <div class="course-popularity-chart">
    <div class="chart-header">
      <h3>课程受欢迎度</h3>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getCoursePopularity } from '@/api/reports'

export default {
  name: 'CoursePopularityChart',
  props: {
    timeRange: {
      type: Number,
      required: true
    }
  },
  setup(props) {
    const chartRef = ref(null)
    const chartInstance = ref(null)
    
    const initChart = () => {
      if (chartRef.value) {
        chartInstance.value = echarts.init(chartRef.value)
      }
    }
    
    const loadData = async () => {
      try {
        const response = await getCoursePopularity({
          days: props.timeRange
        })
        
        const option = {
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow'
            }
          },
          legend: {
            data: ['预订次数', '收入']
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            data: response.course_names.slice(0, 10),
            axisLabel: {
              interval: 0,
              rotate: 45
            }
          },
          yAxis: [
            {
              type: 'value',
              name: '预订次数',
              position: 'left'
            },
            {
              type: 'value',
              name: '收入(元)',
              position: 'right'
            }
          ],
          series: [
            {
              name: '预订次数',
              type: 'bar',
              yAxisIndex: 0,
              itemStyle: {
                color: '#67C23A'
              },
              data: response.booking_counts.slice(0, 10)
            },
            {
              name: '收入',
              type: 'line',
              yAxisIndex: 1,
              smooth: true,
              itemStyle: {
                color: '#E6A23C'
              },
              data: response.revenues.slice(0, 10)
            }
          ]
        }
        
        chartInstance.value.setOption(option)
      } catch (error) {
        console.error('加载课程受欢迎度数据失败:', error)
      }
    }
    
    const refreshChart = () => {
      loadData()
    }
    
    watch(() => props.timeRange, () => {
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
      refreshChart
    }
  }
}
</script>

<style scoped>
.course-popularity-chart {
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

.chart-container {
  flex: 1;
  min-height: 0;
}
</style>