<template>
  <div class="revenue-dashboard">
    <h1>收入仪表盘</h1>
    <div v-if="loading" class="loading-indicator">加载中...</div>
    <div v-if="error" class="error-message">
      加载数据时出错: {{ error.message }}
      <button @click="$router.go(0)">重试</button>
    </div>
    
    <div class="dashboard-container">
      <div class="summary-cards">
        <div class="card total-revenue">
          <h3>总收入</h3>
          <p class="amount">{{ formatCurrency(totalRevenue) }}</p>
          <p class="subtext">所有支付记录总和</p>
        </div>
        
        <div class="card monthly-revenue">
          <h3>本月收入</h3>
          <p class="amount">{{ formatCurrency(monthlyRevenue) }}</p>
          <p class="subtext">{{ currentMonth }}月收入</p>
        </div>
        
        <div class="card payment-count">
          <h3>支付记录数</h3>
          <p class="amount">{{ paymentCount }}</p>
          <p class="subtext">总支付记录数量</p>
        </div>
      </div>
      
      <div class="charts-container">
        <div class="revenue-chart">
          <h3>月度收入趋势</h3>
          <line-chart 
            :chart-data="revenueTrendData" 
            :options="chartOptions" 
            v-if="revenueTrendData.labels.length > 0"
          />
        </div>
        
        <div class="payment-type-chart">
          <h3>支付类型分布</h3>
          <pie-chart 
            :chart-data="paymentTypeData" 
            :options="chartOptions" 
            v-if="paymentTypeData.labels.length > 0"
          />
        </div>
      </div>
      
      <div class="recent-payments">
        <h3>最近支付记录</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>会员ID</th>
              <th>金额</th>
              <th>类型</th>
              <th>日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="payment in recentPayments" :key="payment.id">
              <td>{{ payment.id }}</td>
              <td>{{ payment.member_id }}</td>
              <td>{{ formatCurrency(payment.amount) }}</td>
              <td>{{ payment.payment_type }}</td>
              <td>{{ formatDate(payment.payment_date) }}</td>
,
      fetchMemberPayments,
      loading,
      error
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getPayments } from '../api/payments';
import { getPaymentsByMemberId } from '../api/payments';
import LineChart from '../components/charts/LineChart.vue';
import PieChart from '../components/charts/PieChart.vue';

export default {
  name: 'RevenueDashboard',
  components: {
    LineChart,
    PieChart
  },
  setup() {
    const payments = ref([]);
    const totalRevenue = ref(0);
    const monthlyRevenue = ref(0);
    const paymentCount = ref(0);
    const recentPayments = ref([]);
    const revenueTrendData = ref({
      labels: [],
      datasets: [
        {
          label: '月度收入',
          backgroundColor: '#42b983',
          data: []
        }
      ]
    });
    const paymentTypeData = ref({
      labels: [],
      datasets: [
        {
          backgroundColor: ['#41B883', '#E46651', '#00D8FF', '#DD1B16'],
          data: []
        }
      ]
    });
    const chartOptions = ref({
      responsive: true,
      maintainAspectRatio: false
    });
    
    const currentMonth = new Date().getMonth() + 1;
    const loading = ref(false);
    const error = ref(null);
    
    const formatCurrency = (value) => {
      return '¥' + value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    
    const formatDate = (dateString) => {
    const fetchMemberPayments = async (memberId) => {
      try {
        loading.value = true;
        const memberPayments = await getPaymentsByMemberId(memberId);
        return memberPayments;
      } catch (err) {
        error.value = err;
        console.error('Error fetching member payments:', err);
        return [];
      } finally {
        loading.value = false;
      }
    };
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN');
    };
    
    const calculateRevenueData = () => {
      // 计算总收入
      totalRevenue.value = payments.value.reduce((sum, payment) => sum + payment.amount, 0);
      
      // 计算本月收入
      const currentYear = new Date().getFullYear();
      monthlyRevenue.value = payments.value
        .filter(payment => {
          const paymentDate = new Date(payment.payment_date);
          return paymentDate.getFullYear() === currentYear && 
                 paymentDate.getMonth() + 1 === currentMonth;
        })
        .reduce((sum, payment) => sum + payment.amount, 0);
      
      // 计算支付记录数
      paymentCount.value = payments.value.length;
      
      // 获取最近5条支付记录
      recentPayments.value = [...payments.value]
        .sort((a, b) => new Date(b.payment_date) - new Date(a.payment_date))
        .slice(0, 5);
      
      // 准备月度趋势数据
      const monthlyData = {};
      payments.value.forEach(payment => {
        const date = new Date(payment.payment_date);
        const month = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}`;
        
        if (!monthlyData[month]) {
          monthlyData[month] = 0;
        }
        monthlyData[month] += payment.amount;
      });
      
      revenueTrendData.value.labels = Object.keys(monthlyData);
      revenueTrendData.value.datasets[0].data = Object.values(monthlyData);
      
      // 准备支付类型数据
      const typeData = {};
      payments.value.forEach(payment => {
        if (!typeData[payment.payment_type]) {
          typeData[payment.payment_type] = 0;
        }
        typeData[payment.payment_type] += payment.amount;
      });
      
      paymentTypeData.value.labels = Object.keys(typeData);
      paymentTypeData.value.datasets[0].data = Object.values(typeData);
    };
    
    onMounted(async () => {
      try {
        loading.value = true;
        payments.value = await getPayments();
        calculateRevenueData();
      } catch (err) {
        error.value = err;
        console.error('Error loading payment data:', err);
      } finally {
        loading.value = false;
      }
    });
    
    return {
      totalRevenue,
      monthlyRevenue,
      paymentCount,
      recentPayments,
      revenueTrendData,
      paymentTypeData,
      chartOptions,
      currentMonth,
      formatCurrency,
      formatDate
    };
  }
};
</script>

<style scoped>
.revenue-dashboard {
  position: relative;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  color: #2c3e50;
  margin-bottom: 30px;
}

.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin-top: 0;
  color: #666;
  font-size: 16px;
}

.card .amount {
  font-size: 28px;
  font-weight: bold;
  margin: 10px 0 5px;
  color: #2c3e50;
}

.card .subtext {
  color: #999;
  margin: 0;
  font-size: 14px;
}

.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.revenue-chart, .payment-type-chart {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 300px;
}

.revenue-chart h3, .payment-type-chart h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #666;
}

.recent-payments {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.recent-payments h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #666;
}

table {
  width: 100%;
  border-collapse: collapse;
}

table th, table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

table th {
  background-color: #f8f9fa;
  color: #555;
  font-weight: 600;
}

table tr:hover {
}

.loading-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 20px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 20px;
  background: #ffecec;
  border: 1px solid #ffb3b3;
  border-radius: 8px;
  color: #d33;
  text-align: center;
  z-index: 100;
}

.error-message button {
  margin-top: 10px;
  padding: 8px 16px;
  background: #d33;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-message button:hover {
  background: #b30000;
}
  background-color: #f5f5f5;
}
</style>