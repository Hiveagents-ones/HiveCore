<template>
  <div class="monitoring-dashboard">
    <div class="dashboard-header">
      <h1>系统监控仪表板</h1>
      <div class="time-filter">
        <el-select v-model="timeRange" @change="fetchMetrics">
          <el-option label="最近1小时" value="1h" />
          <el-option label="最近24小时" value="24h" />
          <el-option label="最近7天" value="7d" />
          <el-option label="最近30天" value="30d" />
        </el-select>
      </div>
    </div>

    <div class="metrics-grid">
      <!-- 系统概览卡片 -->
      <div class="metric-card">
        <div class="card-header">
          <h3>系统概览</h3>
          <el-icon><Monitor /></el-icon>
        </div>
        <div class="card-content">
          <div class="metric-item">
            <span class="label">CPU使用率</span>
            <span class="value">{{ systemMetrics.cpu }}%</span>
          </div>
          <div class="metric-item">
            <span class="label">内存使用率</span>
            <span class="value">{{ systemMetrics.memory }}%</span>
          </div>
          <div class="metric-item">
            <span class="label">磁盘使用率</span>
            <span class="value">{{ systemMetrics.disk }}%</span>
          </div>
          <div class="metric-item">
            <span class="label">系统负载</span>
            <span class="value">{{ systemMetrics.load }}</span>
          </div>
        </div>
      </div>

      <!-- 应用指标卡片 -->
      <div class="metric-card">
        <div class="card-header">
          <h3>应用指标</h3>
          <el-icon><DataLine /></el-icon>
        </div>
        <div class="card-content">
          <div class="metric-item">
            <span class="label">在线用户</span>
            <span class="value">{{ appMetrics.activeUsers }}</span>
          </div>
          <div class="metric-item">
            <span class="label">请求速率</span>
            <span class="value">{{ appMetrics.requestRate }}/s</span>
          </div>
          <div class="metric-item">
            <span class="label">响应时间</span>
            <span class="value">{{ appMetrics.responseTime }}ms</span>
          </div>
          <div class="metric-item">
            <span class="label">错误率</span>
            <span class="value">{{ appMetrics.errorRate }}%</span>
          </div>
        </div>
      </div>

      <!-- 支付指标卡片 -->
      <div class="metric-card">
        <div class="card-header">
          <h3>支付指标</h3>
          <el-icon><Money /></el-icon>
        </div>
        <div class="card-content">
          <div class="metric-item">
            <span class="label">今日交易</span>
            <span class="value">¥{{ paymentMetrics.todayAmount }}</span>
          </div>
          <div class="metric-item">
            <span class="label">交易成功率</span>
            <span class="value">{{ paymentMetrics.successRate }}%</span>
          </div>
          <div class="metric-item">
            <span class="label">平均交易额</span>
            <span class="value">¥{{ paymentMetrics.avgAmount }}</span>
          </div>
          <div class="metric-item">
            <span class="label">待处理订单</span>
            <span class="value">{{ paymentMetrics.pendingOrders }}</span>
          </div>
        </div>
      </div>

      <!-- 会员指标卡片 -->
      <div class="metric-card">
        <div class="card-header">
          <h3>会员指标</h3>
          <el-icon><User /></el-icon>
        </div>
        <div class="card-content">
          <div class="metric-item">
            <span class="label">总会员数</span>
            <span class="value">{{ memberMetrics.total }}</span>
          </div>
          <div class="metric-item">
            <span class="label">活跃会员</span>
            <span class="value">{{ memberMetrics.active }}</span>
          </div>
          <div class="metric-item">
            <span class="label">即将到期</span>
            <span class="value">{{ memberMetrics.expiringSoon }}</span>
          </div>
          <div class="metric-item">
            <span class="label">已过期</span>
            <span class="value">{{ memberMetrics.expired }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <div class="chart-container">
        <h3>系统性能趋势</h3>
        <div ref="performanceChart" class="chart"></div>
      </div>
      <div class="chart-container">
        <h3>支付趋势</h3>
        <div ref="paymentChart" class="chart"></div>
      </div>
    </div>

    <!-- 实时日志 -->
    <div class="logs-section">
      <div class="section-header">
        <h3>实时日志</h3>
        <el-button @click="refreshLogs" :loading="logsLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <el-table :data="logs" style="width: 100%" height="300">
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="level" label="级别" width="100">
          <template #default="scope">
            <el-tag :type="getLogLevelType(scope.row.level)">{{ scope.row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="service" label="服务" width="120" />
        <el-table-column prop="message" label="消息" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, DataLine, Money, User, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { paymentAPI } from '@/api/payment'

// 数据状态
const timeRange = ref('24h')
const logsLoading = ref(false)

// 系统指标
const systemMetrics = ref({
  cpu: 0,
  memory: 0,
  disk: 0,
  load: 0
})

// 应用指标
const appMetrics = ref({
  activeUsers: 0,
  requestRate: 0,
  responseTime: 0,
  errorRate: 0
})

// 支付指标
const paymentMetrics = ref({
  todayAmount: 0,
  successRate: 0,
  avgAmount: 0,
  pendingOrders: 0
})

// 会员指标
const memberMetrics = ref({
  total: 0,
  active: 0,
  expiringSoon: 0,
  expired: 0
})

// 日志数据
const logs = ref([])

// 图表引用
const performanceChart = ref(null)
const paymentChart = ref(null)
let performanceChartInstance = null
let paymentChartInstance = null

// 定时器
let metricsTimer = null
let logsTimer = null

// 获取系统指标
const fetchSystemMetrics = async () => {
  try {
    // 模拟数据，实际应该从监控系统获取
    systemMetrics.value = {
      cpu: Math.floor(Math.random() * 30 + 40),
      memory: Math.floor(Math.random() * 20 + 50),
      disk: Math.floor(Math.random() * 10 + 60),
      load: (Math.random() * 2 + 1).toFixed(2)
    }
  } catch (error) {
    console.error('Error fetching system metrics:', error)
  }
}

// 获取应用指标
const fetchAppMetrics = async () => {
  try {
    // 模拟数据
    appMetrics.value = {
      activeUsers: Math.floor(Math.random() * 100 + 200),
      requestRate: Math.floor(Math.random() * 50 + 100),
      responseTime: Math.floor(Math.random() * 50 + 100),
      errorRate: (Math.random() * 2).toFixed(2)
    }
  } catch (error) {
    console.error('Error fetching app metrics:', error)
  }
}

// 获取支付指标
const fetchPaymentMetrics = async () => {
  try {
    const stats = await paymentAPI.getPaymentStats({ timeRange: timeRange.value })
    paymentMetrics.value = {
      todayAmount: stats.todayAmount || 0,
      successRate: stats.successRate || 0,
      avgAmount: stats.avgAmount || 0,
      pendingOrders: stats.pendingOrders || 0
    }
  } catch (error) {
    console.error('Error fetching payment metrics:', error)
    // 使用模拟数据作为备用
    paymentMetrics.value = {
      todayAmount: Math.floor(Math.random() * 10000 + 5000),
      successRate: Math.floor(Math.random() * 5 + 95),
      avgAmount: Math.floor(Math.random() * 500 + 200),
      pendingOrders: Math.floor(Math.random() * 10 + 5)
    }
  }
}

// 获取会员指标
const fetchMemberMetrics = async () => {
  try {
    // 模拟数据
    memberMetrics.value = {
      total: Math.floor(Math.random() * 500 + 1500),
      active: Math.floor(Math.random() * 300 + 800),
      expiringSoon: Math.floor(Math.random() * 50 + 20),
      expired: Math.floor(Math.random() * 30 + 10)
    }
  } catch (error) {
    console.error('Error fetching member metrics:', error)
  }
}

// 获取日志
const fetchLogs = async () => {
  logsLoading.value = true
  try {
    // 模拟日志数据
    const mockLogs = []
    const levels = ['INFO', 'WARN', 'ERROR']
    const services = ['payment', 'auth', 'member', 'reminder']
    const messages = [
      'Payment processed successfully',
      'User authentication failed',
      'Member subscription renewed',
      'Reminder sent successfully',
      'Database connection timeout',
      'Cache cleared successfully'
    ]
    
    for (let i = 0; i < 20; i++) {
      mockLogs.push({
        timestamp: new Date(Date.now() - i * 60000).toLocaleString(),
        level: levels[Math.floor(Math.random() * levels.length)],
        service: services[Math.floor(Math.random() * services.length)],
        message: messages[Math.floor(Math.random() * messages.length)]
      })
    }
    
    logs.value = mockLogs
  } catch (error) {
    console.error('Error fetching logs:', error)
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

// 刷新日志
const refreshLogs = () => {
  fetchLogs()
}

// 获取所有指标
const fetchMetrics = async () => {
  await Promise.all([
    fetchSystemMetrics(),
    fetchAppMetrics(),
    fetchPaymentMetrics(),
    fetchMemberMetrics()
  ])
  updateCharts()
}

// 初始化性能图表
const initPerformanceChart = () => {
  if (!performanceChart.value) return
  
  performanceChartInstance = echarts.init(performanceChart.value)
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['CPU使用率', '内存使用率', '响应时间']
    },
    xAxis: {
      type: 'category',
      data: []
    },
    yAxis: [
      {
        type: 'value',
        name: '使用率(%)',
        max: 100
      },
      {
        type: 'value',
        name: '响应时间(ms)',
        max: 500
      }
    ],
    series: [
      {
        name: 'CPU使用率',
        type: 'line',
        data: []
      },
      {
        name: '内存使用率',
        type: 'line',
        data: []
      },
      {
        name: '响应时间',
        type: 'line',
        yAxisIndex: 1,
        data: []
      }
    ]
  }
  performanceChartInstance.setOption(option)
}

// 初始化支付图表
const initPaymentChart = () => {
  if (!paymentChart.value) return
  
  paymentChartInstance = echarts.init(paymentChart.value)
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['交易金额', '交易数量']
    },
    xAxis: {
      type: 'category',
      data: []
    },
    yAxis: [
      {
        type: 'value',
        name: '金额(¥)'
      },
      {
        type: 'value',
        name: '数量'
      }
    ],
    series: [
      {
        name: '交易金额',
        type: 'bar',
        data: []
      },
      {
        name: '交易数量',
        type: 'line',
        yAxisIndex: 1,
        data: []
      }
    ]
  }
  paymentChartInstance.setOption(option)
}

// 更新图表数据
const updateCharts = () => {
  // 生成时间轴数据
  const times = []
  const cpuData = []
  const memoryData = []
  const responseTimeData = []
  const paymentAmountData = []
  const paymentCountData = []
  
  for (let i = 23; i >= 0; i--) {
    const time = new Date(Date.now() - i * 3600000)
    times.push(time.getHours() + ':00')
    cpuData.push(Math.floor(Math.random() * 30 + 40))
    memoryData.push(Math.floor(Math.random() * 20 + 50))
    responseTimeData.push(Math.floor(Math.random() * 50 + 100))
    paymentAmountData.push(Math.floor(Math.random() * 5000 + 2000))
    paymentCountData.push(Math.floor(Math.random() * 50 + 20))
  }
  
  // 更新性能图表
  if (performanceChartInstance) {
    performanceChartInstance.setOption({
      xAxis: { data: times },
      series: [
        { data: cpuData },
        { data: memoryData },
        { data: responseTimeData }
      ]
    })
  }
  
  // 更新支付图表
  if (paymentChartInstance) {
    paymentChartInstance.setOption({
      xAxis: { data: times },
      series: [
        { data: paymentAmountData },
        { data: paymentCountData }
      ]
    })
  }
}

// 获取日志级别类型
const getLogLevelType = (level) => {
  switch (level) {
    case 'ERROR':
      return 'danger'
    case 'WARN':
      return 'warning'
    default:
      return 'info'
  }
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  if (performanceChartInstance) {
    performanceChartInstance.resize()
  }
  if (paymentChartInstance) {
    paymentChartInstance.resize()
  }
}

// 组件挂载
onMounted(async () => {
  await fetchMetrics()
  await fetchLogs()
  
  // 初始化图表
  initPerformanceChart()
  initPaymentChart()
  updateCharts()
  
  // 设置定时刷新
  metricsTimer = setInterval(fetchMetrics, 30000) // 30秒刷新指标
  logsTimer = setInterval(fetchLogs, 60000) // 60秒刷新日志
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

// 组件卸载
onUnmounted(() => {
  if (metricsTimer) {
    clearInterval(metricsTimer)
  }
  if (logsTimer) {
    clearInterval(logsTimer)
  }
  if (performanceChartInstance) {
    performanceChartInstance.dispose()
  }
  if (paymentChartInstance) {
    paymentChartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.monitoring-dashboard {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.dashboard-header h1 {
  color: #303133;
  font-size: 24px;
  margin: 0;
}

.time-filter {
  width: 150px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

.card-header .el-icon {
  font-size: 24px;
  color: #409eff;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-item .label {
  color: #606266;
  font-size: 14px;
}

.metric-item .value {
  color: #303133;
  font-size: 16px;
  font-weight: bold;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.chart-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.chart-container h3 {
  margin: 0 0 20px 0;
  color: #303133;
  font-size: 18px;
}

.chart {
  height: 300px;
}

.logs-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .charts-section {
    grid-template-columns: 1fr;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 15px;
    align-items: flex-start;
  }
}
</style>