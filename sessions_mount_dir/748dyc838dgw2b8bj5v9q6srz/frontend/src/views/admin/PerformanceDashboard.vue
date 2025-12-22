<template>
  <div class="performance-dashboard">
    <div class="dashboard-header">
      <h1>性能监控仪表板</h1>
      <div class="time-filter">
        <select v-model="selectedTimeRange" @change="fetchMetrics">
          <option value="1h">过去1小时</option>
          <option value="24h">过去24小时</option>
          <option value="7d">过去7天</option>
          <option value="30d">过去30天</option>
        </select>
      </div>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <h3>响应时间</h3>
        <div class="metric-value">{{ metrics.avgResponseTime }}ms</div>
        <div class="metric-trend" :class="metrics.responseTimeTrend">
          {{ formatTrend(metrics.responseTimeTrend) }}
        </div>
      </div>

      <div class="metric-card">
        <h3>请求成功率</h3>
        <div class="metric-value">{{ metrics.successRate }}%</div>
        <div class="metric-trend" :class="metrics.successRateTrend">
          {{ formatTrend(metrics.successRateTrend) }}
        </div>
      </div>

      <div class="metric-card">
        <h3>每秒请求数</h3>
        <div class="metric-value">{{ metrics.requestsPerSecond }}</div>
        <div class="metric-trend" :class="metrics.rpsTrend">
          {{ formatTrend(metrics.rpsTrend) }}
        </div>
      </div>

      <div class="metric-card">
        <h3>错误数</h3>
        <div class="metric-value">{{ metrics.errorCount }}</div>
        <div class="metric-trend" :class="metrics.errorTrend">
          {{ formatTrend(metrics.errorTrend) }}
        </div>
      </div>
    </div>

    <div class="charts-section">
      <div class="chart-container">
        <h3>响应时间趋势</h3>
        <canvas ref="responseTimeChart"></canvas>
      </div>

      <div class="chart-container">
        <h3>请求分布</h3>
        <canvas ref="requestDistributionChart"></canvas>
      </div>
    </div>

    <div class="operations-table">
      <h3>操作性能详情</h3>
      <table>
        <thead>
          <tr>
            <th>操作名称</th>
            <th>平均响应时间</th>
            <th>最大响应时间</th>
            <th>最小响应时间</th>
            <th>调用次数</th>
            <th>成功率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="op in operations" :key="op.name">
            <td>{{ op.name }}</td>
            <td>{{ op.avgTime }}ms</td>
            <td>{{ op.maxTime }}ms</td>
            <td>{{ op.minTime }}ms</td>
            <td>{{ op.count }}</td>
            <td>{{ op.successRate }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="alerts-section">
      <h3>性能告警</h3>
      <div class="alerts-list">
        <div v-for="alert in alerts" :key="alert.id" class="alert" :class="alert.severity">
          <div class="alert-header">
            <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
            <span class="alert-severity">{{ alert.severity }}</span>
          </div>
          <div class="alert-message">{{ alert.message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { Chart } from 'chart.js/auto'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default {
  name: 'PerformanceDashboard',
  setup() {
    const selectedTimeRange = ref('24h')
    const metrics = ref({
      avgResponseTime: 0,
      responseTimeTrend: 'stable',
      successRate: 0,
      successRateTrend: 'stable',
      requestsPerSecond: 0,
      rpsTrend: 'stable',
      errorCount: 0,
      errorTrend: 'stable'
    })
    const operations = ref([])
    const alerts = ref([])
    const responseTimeChart = ref(null)
    const requestDistributionChart = ref(null)
    let chartInstances = {}
    let refreshInterval = null

    const fetchMetrics = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/admin/performance/metrics`, {
          params: { timeRange: selectedTimeRange.value }
        })
        metrics.value = response.data.metrics
        operations.value = response.data.operations
        alerts.value = response.data.alerts
        
        updateCharts(response.data.chartData)
      } catch (error) {
        console.error('Failed to fetch performance metrics:', error)
      }
    }

    const updateCharts = (chartData) => {
      // Update response time chart
      if (chartInstances.responseTime) {
        chartInstances.responseTime.destroy()
      }
      
      chartInstances.responseTime = new Chart(responseTimeChart.value, {
        type: 'line',
        data: {
          labels: chartData.responseTime.labels,
          datasets: [{
            label: '响应时间 (ms)',
            data: chartData.responseTime.data,
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false
        }
      })

      // Update request distribution chart
      if (chartInstances.requestDistribution) {
        chartInstances.requestDistribution.destroy()
      }
      
      chartInstances.requestDistribution = new Chart(requestDistributionChart.value, {
        type: 'doughnut',
        data: {
          labels: chartData.requestDistribution.labels,
          datasets: [{
            data: chartData.requestDistribution.data,
            backgroundColor: [
              'rgb(255, 99, 132)',
              'rgb(54, 162, 235)',
              'rgb(255, 205, 86)',
              'rgb(75, 192, 192)'
            ]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false
        }
      })
    }

    const formatTrend = (trend) => {
      const trends = {
        up: '↑ 上升',
        down: '↓ 下降',
        stable: '→ 稳定'
      }
      return trends[trend] || trends.stable
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleString('zh-CN')
    }

    onMounted(() => {
      fetchMetrics()
      refreshInterval = setInterval(fetchMetrics, 30000) // Refresh every 30 seconds
    })

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
      Object.values(chartInstances).forEach(chart => chart.destroy())
    })

    return {
      selectedTimeRange,
      metrics,
      operations,
      alerts,
      responseTimeChart,
      requestDistributionChart,
      fetchMetrics,
      formatTrend,
      formatTime
    }
  }
}
</script>

<style scoped>
.performance-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.dashboard-header h1 {
  color: #2c3e50;
  margin: 0;
}

.time-filter select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.metric-card h3 {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 14px;
  text-transform: uppercase;
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 5px;
}

.metric-trend {
  font-size: 14px;
}

.metric-trend.up {
  color: #e74c3c;
}

.metric-trend.down {
  color: #27ae60;
}

.metric-trend.stable {
  color: #95a5a6;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chart-container h3 {
  margin: 0 0 20px 0;
  color: #2c3e50;
}

.chart-container canvas {
  max-height: 300px;
}

.operations-table {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 30px;
}

.operations-table h3 {
  margin: 0 0 20px 0;
  color: #2c3e50;
}

.operations-table table {
  width: 100%;
  border-collapse: collapse;
}

.operations-table th,
.operations-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.operations-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #666;
}

.alerts-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.alerts-section h3 {
  margin: 0 0 20px 0;
  color: #2c3e50;
}

.alert {
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 4px;
  border-left: 4px solid;
}

.alert.critical {
  background: #fee;
  border-color: #e74c3c;
}

.alert.warning {
  background: #fff3cd;
  border-color: #f39c12;
}

.alert.info {
  background: #d1ecf1;
  border-color: #17a2b8;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.alert-time {
  font-size: 12px;
  color: #666;
}

.alert-severity {
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.alert-message {
  color: #2c3e50;
}
</style>