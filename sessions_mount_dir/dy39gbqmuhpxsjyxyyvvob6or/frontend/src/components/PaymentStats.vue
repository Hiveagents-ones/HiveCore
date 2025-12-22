<template>
  <div class="payment-stats-container">
    <div class="stats-header">
      <h2>缴费统计报表</h2>
      <div class="time-filter">
        <el-date-picker
          v-model="timeRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="fetchPaymentStats"
        />
      </div>
    </div>

    <div class="stats-content">
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="chart-container">
            <h3>收入趋势</h3>
            <div ref="trendChart" style="width: 100%; height: 300px;"></div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-container">
            <h3>支付方式分布</h3>
            <div ref="methodChart" style="width: 100%; height: 300px;"></div>
          </div>
        </el-col>
      </el-row>

      <div class="drilldown-table">
        <h3>详细数据</h3>
        <el-table
          :data="paymentData"
          border
          style="width: 100%"
          @row-click="handleRowClick"
        >
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column prop="memberName" label="会员" />
          <el-table-column prop="amount" label="金额" width="120" />
          <el-table-column prop="method" label="支付方式" width="120" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import * as echarts from 'echarts';
import { getPaymentStats } from '../api/payment';

export default {
  name: 'PaymentStats',
  setup() {
    const timeRange = ref([new Date(new Date().setDate(new Date().getDate() - 30)), new Date()]);
    const trendChart = ref(null);
    const methodChart = ref(null);
    const paymentData = ref([]);

    const initCharts = () => {
      const trendInstance = echarts.init(trendChart.value);
      const methodInstance = echarts.init(methodChart.value);

      trendInstance.setOption({
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: []
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            data: [],
            type: 'line',
            smooth: true
          }
        ]
      });

      methodInstance.setOption({
        tooltip: {
          trigger: 'item'
        },
        series: [
          {
            name: '支付方式',
            type: 'pie',
            radius: '50%',
            data: [],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      });

      return { trendInstance, methodInstance };
    };

    const fetchPaymentStats = async () => {
      try {
        const [startDate, endDate] = timeRange.value;
        const params = {
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0]
        };

        const { trendData, methodData, detailData } = await getPaymentStats(params);
        
        const { trendInstance, methodInstance } = initCharts();
        
        trendInstance.setOption({
          xAxis: {
            data: trendData.dates
          },
          series: [
            {
              data: trendData.amounts
            }
          ]
        });

        methodInstance.setOption({
          series: [
            {
              data: methodData.map(item => ({
                value: item.count,
                name: item.method
              }))
            }
          ]
        });

        paymentData.value = detailData;
      } catch (error) {
        console.error('获取统计信息失败:', error);
      }
    };

    const handleRowClick = (row) => {
      // 钻取到会员详情或支付详情
      console.log('钻取数据:', row);
    };

    onMounted(() => {
      fetchPaymentStats();
    });

    return {
      timeRange,
      trendChart,
      methodChart,
      paymentData,
      fetchPaymentStats,
      handleRowClick
    };
  }
};
</script>

<style scoped>
.payment-stats-container {
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-container {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.drilldown-table {
  margin-top: 20px;
}
</style>