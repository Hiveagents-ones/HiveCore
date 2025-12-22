<template>
  <div class="security-observability-container">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="security-card">
          <template #header>
            <div class="card-header">
              <span>支付安全监控</span>
              <el-tag type="info" class="refresh-tag" @click="fetchSecurityData">
                <el-icon><Refresh /></el-icon> 刷新
              </el-tag>
            </div>
          </template>
          
          <div class="security-metrics">
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="metric-item">
                  <div class="metric-title">PCI合规状态</div>
                  <div class="metric-value" :class="{ 'success': securityData.pciCompliant, 'danger': !securityData.pciCompliant }">
                    {{ securityData.pciCompliant ? '合规' : '不合规' }}
                  </div>
                </div>
              </el-col>
              
              <el-col :span="8">
                <div class="metric-item">
                  <div class="metric-title">加密交易</div>
                  <div class="metric-value">{{ securityData.encryptedTransactions }}%</div>
                </div>
              </el-col>
              
              <el-col :span="8">
                <div class="metric-item">
                  <div class="metric-title">异常交易</div>
                  <div class="metric-value" :class="{ 'warning': securityData.suspiciousTransactions > 0 }">
                    {{ securityData.suspiciousTransactions }}
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
          
          <el-divider />
          
          <div class="security-events">
            <div class="section-title">最近安全事件</div>
            <el-timeline>
              <el-timeline-item 
                v-for="event in securityData.recentEvents" 
                :key="event.id"
                :timestamp="event.timestamp"
                :type="event.severity === 'high' ? 'danger' : event.severity === 'medium' ? 'warning' : 'primary'"
                placement="top"
              >
                {{ event.description }}
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card class="observability-card">
          <template #header>
            <div class="card-header">
              <span>支付可观测性</span>
              <el-select v-model="timeRange" class="time-select" @change="fetchObservabilityData">
                <el-option label="最近1小时" value="1h" />
                <el-option label="最近24小时" value="24h" />
                <el-option label="最近7天" value="7d" />
              </el-select>
            </div>
          </template>
          
          <div class="observability-charts">
            <div class="chart-container">
              <div class="chart-title">支付成功率</div>
              <div ref="successRateChart" class="chart"></div>
            </div>
            
            <div class="chart-container">
              <div class="chart-title">支付延迟(ms)</div>
              <div ref="latencyChart" class="chart"></div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card class="payment-integrity-card">
          <template #header>
            <div class="card-header">
              <span>支付完整性验证</span>
              <PaymentIntegrityValidator @validation-complete="handleValidationComplete" />
            </div>
          </template>
          
          <el-table :data="integrityData" stripe style="width: 100%">
            <el-table-column prop="transactionId" label="交易ID" width="180" />
            <el-table-column prop="amount" label="金额" width="120" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === 'valid' ? 'success' : 'danger'">
                  {{ row.status === 'valid' ? '有效' : '无效' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="timestamp" label="时间" width="180" />
            <el-table-column prop="verification" label="验证结果" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import axios from '../api/axios';
import PaymentIntegrityValidator from '../components/PaymentIntegrityValidator.vue';
import { Refresh } from '@element-plus/icons-vue';

export default {
  name: 'SecurityObservability',
  
  components: {
    PaymentIntegrityValidator,
    Refresh
  },
  
  setup() {
    const securityData = ref({
      pciCompliant: true,
      encryptedTransactions: 100,
      suspiciousTransactions: 0,
      recentEvents: []
    });
    
    const observabilityData = ref({
      successRate: [],
      latency: []
    });
    
    const integrityData = ref([]);
    const timeRange = ref('1h');
    const successRateChart = ref(null);
    const latencyChart = ref(null);
    
    const fetchSecurityData = async () => {
      try {
        const response = await axios.get('/api/v1/payments/security');
        securityData.value = response.data;
      } catch (error) {
        console.error('Failed to fetch security data:', error);
      }
    };
    
    const fetchObservabilityData = async () => {
      try {
        const response = await axios.get(`/api/v1/payments/observability?range=${timeRange.value}`);
        observabilityData.value = response.data;
        renderCharts();
      } catch (error) {
        console.error('Failed to fetch observability data:', error);
      }
    };
    
    const fetchIntegrityData = async () => {
      try {
        const response = await axios.get('/api/v1/payments/integrity');
        integrityData.value = response.data;
      } catch (error) {
        console.error('Failed to fetch integrity data:', error);
      }
    };
    
    const handleValidationComplete = (data) => {
      integrityData.value.unshift({
        transactionId: data.transactionId,
        amount: data.amount,
        status: data.valid ? 'valid' : 'invalid',
        timestamp: new Date().toLocaleString(),
        verification: data.message
      });
    };
    
    const renderCharts = () => {
      nextTick(() => {
        // 渲染成功率图表
        const successRateChartInstance = echarts.init(successRateChart.value);
        successRateChartInstance.setOption({
          tooltip: {
            trigger: 'axis'
          },
          xAxis: {
            type: 'category',
            data: observabilityData.value.successRate.map(item => item.time)
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            axisLabel: {
              formatter: '{value}%'
            }
          },
          series: [{
            data: observabilityData.value.successRate.map(item => item.rate),
            type: 'line',
            smooth: true,
            areaStyle: {}
          }]
        });
        
        // 渲染延迟图表
        const latencyChartInstance = echarts.init(latencyChart.value);
        latencyChartInstance.setOption({
          tooltip: {
            trigger: 'axis'
          },
          xAxis: {
            type: 'category',
            data: observabilityData.value.latency.map(item => item.time)
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: '{value} ms'
            }
          },
          series: [{
            data: observabilityData.value.latency.map(item => item.latency),
            type: 'line',
            smooth: true,
            areaStyle: {}
          }]
        });
        
        window.addEventListener('resize', () => {
          successRateChartInstance.resize();
          latencyChartInstance.resize();
        });
      });
    };
    
    onMounted(() => {
      fetchSecurityData();
      fetchObservabilityData();
      fetchIntegrityData();
    });
    
    return {
      securityData,
      observabilityData,
      integrityData,
      timeRange,
      successRateChart,
      latencyChart,
      fetchSecurityData,
      fetchObservabilityData,
      handleValidationComplete
    };
  }
};
</script>

<style scoped>
.security-observability-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.refresh-tag {
  cursor: pointer;
}

.security-card, .observability-card, .payment-integrity-card {
  margin-bottom: 20px;
  height: 100%;
}

.metric-item {
  text-align: center;
  padding: 10px;
}

.metric-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
}

.metric-value.success {
  color: #67C23A;
}

.metric-value.danger {
  color: #F56C6C;
}

.metric-value.warning {
  color: #E6A23C;
}

.section-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
}

.time-select {
  width: 120px;
}

.observability-charts {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-container {
  height: 250px;
}

.chart-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.chart {
  height: 200px;
  width: 100%;
}

.mt-20 {
  margin-top: 20px;
}
</style>