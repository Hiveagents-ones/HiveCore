<template>
  <div class="payment-audit-container">
    <h2>支付审计日志</h2>
    
    <div class="filter-controls">
      <div class="filter-group">
        <label for="memberId">会员ID:</label>
        <input 
          id="memberId" 
          type="number" 
          v-model="filters.memberId" 
          placeholder="输入会员ID" 
          min="1"
        />
      </div>
      
      <div class="filter-group">
        <label for="dateRange">日期范围:</label>
        <input 
          id="startDate" 
          type="date" 
          v-model="filters.startDate" 
        />
        <span>至</span>
        <input 
          id="endDate" 
          type="date" 
          v-model="filters.endDate" 
        />
      </div>
      
      <button @click="fetchAuditLogs" class="search-button">查询</button>
      <button @click="resetFilters" class="reset-button">重置</button>
    </div>
    
    <div v-if="loading" class="loading-indicator">加载中...</div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    
    <div class="audit-log-table">
      <table v-if="auditLogs.length > 0">
        <thead>
          <tr>
            <th>日志ID</th>
            <th>操作类型</th>
            <th>会员ID</th>
            <th>金额</th>
            <th>支付方式</th>
            <th>操作时间</th>
            <th>操作人</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in auditLogs" :key="log.id">
            <td>{{ log.id }}</td>
            <td>{{ log.action }}</td>
            <td>{{ log.member_id }}</td>
            <td>{{ log.amount }}</td>
            <td>{{ log.payment_method }}</td>
            <td>{{ formatDateTime(log.action_time) }}</td>
            <td>{{ log.operator }}</td>
          </tr>
        </tbody>
      </table>
      
      <div v-else class="no-data">
        没有找到匹配的审计日志
      </div>
    </div>
    
    <div class="pagination-controls" v-if="auditLogs.length > 0">
      <button 
        @click="prevPage" 
        :disabled="currentPage === 1"
      >上一页</button>
      
      <span>第 {{ currentPage }} 页</span>
      
      <button 
        @click="nextPage" 
        :disabled="auditLogs.length < pageSize"
      >下一页</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getPaymentAuditLogs } from '@/api/payments';

export default {
  name: 'PaymentAudit',
  
  setup() {
    const auditLogs = ref([]);
    const loading = ref(false);
    const error = ref(null);
    const currentPage = ref(1);
    const pageSize = ref(10);
    
    const filters = ref({
      memberId: null,
      startDate: '',
      endDate: ''
    });
    
    const fetchAuditLogs = async () => {
      loading.value = true;
      error.value = null;
      
      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        };
        
        if (filters.value.memberId) {
          params.member_id = filters.value.memberId;
        }
        
        if (filters.value.startDate) {
          params.start_date = filters.value.startDate;
        }
        
        if (filters.value.endDate) {
          params.end_date = filters.value.endDate;
        }
        
        const response = await getPaymentAuditLogs(params);
        auditLogs.value = response.data || [];
      } catch (err) {
        console.error('获取审计日志失败:', err);
        error.value = '获取审计日志失败，请稍后重试';
        auditLogs.value = [];
      } finally {
        loading.value = false;
      }
    };
    
    const resetFilters = () => {
      filters.value = {
        memberId: null,
        startDate: '',
        endDate: ''
      };
      currentPage.value = 1;
      fetchAuditLogs();
    };
    
    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        fetchAuditLogs();
      }
    };
    
    const nextPage = () => {
      if (auditLogs.value.length === pageSize.value) {
        currentPage.value++;
        fetchAuditLogs();
      }
    };
    
    const formatDateTime = (dateTime) => {
      if (!dateTime) return '';
      return new Date(dateTime).toLocaleString();
    };
    
    onMounted(() => {
      fetchAuditLogs();
    });
    
    return {
      auditLogs,
      loading,
      error,
      currentPage,
      filters,
      fetchAuditLogs,
      resetFilters,
      prevPage,
      nextPage,
      formatDateTime
    };
  }
};
</script>

<style scoped>
.payment-audit-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.filter-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
  align-items: center;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: bold;
}

input[type="number"],
input[type="date"] {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.search-button {
  background-color: #4CAF50;
  color: white;
}

.reset-button {
  background-color: #f44336;
  color: white;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-indicator,
.error-message,
.no-data {
  padding: 15px;
  text-align: center;
  margin: 20px 0;
}

.loading-indicator {
  color: #2196F3;
}

.error-message {
  color: #f44336;
  background-color: #ffebee;
  border-radius: 4px;
}

.no-data {
  color: #757575;
  background-color: #f5f5f5;
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f8f9fa;
  font-weight: bold;
}

tr:hover {
  background-color: #f5f5f5;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
}

.pagination-controls button {
  background-color: #2196F3;
  color: white;
}
</style>