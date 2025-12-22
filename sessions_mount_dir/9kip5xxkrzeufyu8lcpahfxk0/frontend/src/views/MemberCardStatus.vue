<template>
  <div class="member-card-status">
    <h2>会员卡状态管理</h2>
    <div class="filter-bar">
      <select v-model="statusFilter" @change="fetchMemberCards" class="status-filter">
        <option value="">所有状态</option>
        <option value="ACTIVE">激活</option>
        <option value="SUSPENDED">暂停</option>
        <option value="EXPIRED">已过期</option>
        <option value="CANCELLED">已注销</option>
      </select>
    </div>
    
    <div class="search-bar">
      <input 
        v-model="searchQuery" 
        placeholder="搜索会员卡号或会员姓名" 
        @input="fetchMemberCards"
      />
    </div>
    
    <div class="card-list">
      <div class="pagination" v-if="!loading && memberCards.length > 0">
        <button 
          @click="page--; fetchMemberCards();" 
          :disabled="page === 1"
          class="pagination-btn"
        >
          上一页
        </button>
        <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(totalItems / pageSize) }} 页</span>
        <button 
          @click="page++; fetchMemberCards();" 
          :disabled="page * pageSize >= totalItems"
          class="pagination-btn"
        >
          下一页
        </button>
      </div>
      <div v-if="loading" class="loading">加载中...</div>
      
      <div v-if="!loading && memberCards.length === 0" class="empty">
        没有找到会员卡记录
      </div>
      
      <div 
        v-for="card in memberCards" 
        :key="card.id" 
        class="card-item"
        :class="{ 'expired': isCardExpired(card) }"
      >
        <div class="card-header">
          <span class="card-number">{{ card.card_number }}</span>
          <span class="card-status" :class="card.status.toLowerCase()">
            {{ getStatusText(card.status) }}
          </span>
        </div>
        
        <div class="card-details">
          <p><strong>会员姓名:</strong> {{ card.member.name }}</p>
          <p><strong>有效期至:</strong> {{ formatDate(card.expiry_date) }}</p>
          <p><strong>手机号码:</strong> {{ card.member.phone }}</p>
        </div>
        
        <div class="card-actions">
          <button 
            v-if="card.status === 'ACTIVE'" 
            @click="updateCardStatus(card.id, 'SUSPENDED')"
            class="btn-suspend"
          >
            暂停
          </button>
          <button 
            v-if="card.status === 'SUSPENDED'" 
            @click="updateCardStatus(card.id, 'ACTIVE')"
            class="btn-activate"
          >
            激活
          </button>
          <button 
            @click="confirmCancelCard(card.id)"
            class="btn-cancel"
          >
            注销
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useToast } from 'vue-toastification';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
import { useMemberStore } from '../stores/member';

export default {
  name: 'MemberCardStatus',
  
  setup() {
    const toast = useToast();
    const memberCards = ref([]);
    const loading = ref(false);
    const searchQuery = ref('');
const statusFilter = ref('');
    const page = ref(1);
    const pageSize = ref(10);
    const totalItems = ref(0);
const memberStore = useMemberStore();
    
    const fetchMemberCards = async () => {
      try {
        loading.value = true;
        const response = await memberStore.fetchMemberCards({
          search: searchQuery.value,
          status: statusFilter.value,
          page: page.value,
          pageSize: pageSize.value
        });
        totalItems.value = response.total;
        memberCards.value = response.data;
      } catch (error) {
        toast.error('获取会员卡信息失败');
        console.error('Error fetching member cards:', error);
      } finally {
        loading.value = false;
      }
    };
    
    const updateCardStatus = async (cardId, newStatus) => {
      try {
        await memberStore.updateCardStatus(cardId, newStatus);
        toast.success(`会员卡状态已更新为${getStatusText(newStatus)}`);
        fetchMemberCards();
      } catch (error) {
        toast.error('更新会员卡状态失败');
        console.error('Error updating card status:', error);
      }
    };
    
    const cancelCard = async (cardId) => {
      try {
        await memberStore.cancelCard(cardId);
        toast.success('会员卡已注销');
        fetchMemberCards();
      } catch (error) {
        toast.error('注销会员卡失败');
        console.error('Error canceling card:', error);
      }
    };
    
    const confirmCancelCard = (cardId) => {
      if (confirm('确定要注销此会员卡吗？此操作不可撤销。')) {
        cancelCard(cardId);
      }
    };
    
    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString();
    };
    
    const isCardExpired = (card) => {
      return new Date(card.expiry_date) < new Date();
    };
    
    const getStatusText = (status) => {
      const statusMap = {
        'ACTIVE': '激活',
        'SUSPENDED': '暂停',
        'CANCELLED': '已注销',
        'EXPIRED': '已过期'
      };
      return statusMap[status] || status;
    };
    
    onMounted(() => {
      fetchMemberCards();
    });
    
    return {
      memberCards,
      loading,
      searchQuery,
      fetchMemberCards,
      updateCardStatus,
      confirmCancelCard,
      formatDate,
      isCardExpired,
      getStatusText
    };
  }
};
</script>

<style scoped>
.member-card-status {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  color: #333;
  margin-bottom: 20px;
}

.search-bar {
  margin-bottom: 20px;
}

.search-bar input {
  .filter-bar {
    margin-bottom: 20px;
  }
  
  .status-filter {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
    min-width: 150px;
  }
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.card-item {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-item.expired {
  border-left: 4px solid #ff5252;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.card-number {
  font-weight: bold;
  font-size: 18px;
}

.card-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: bold;
}

.card-status.active {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.card-status.suspended {
  background-color: #fff8e1;
  color: #ff8f00;
}

.card-status.cancelled, .card-status.expired {
  background-color: #ffebee;
  color: #c62828;
}

.card-details p {
  margin: 5px 0;
  color: #555;
}

.card-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.card-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-activate {
  background-color: #4caf50;
  color: white;
}

.btn-suspend {
  background-color: #ff9800;
  color: white;
}

.btn-cancel {
  background-color: #f44336;
  color: white;
}

.loading, .empty {
  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin: 20px 0;
    grid-column: 1 / -1;
  }

  .pagination-btn {
    padding: 8px 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #fff;
    cursor: pointer;
  }

  .pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-info {
    color: #666;
  }
  text-align: center;
  padding: 20px;
  grid-column: 1 / -1;
  color: #666;
}
</style>