<template>
  <div class="member-detail-container">
    <div v-if="loading" class="loading-indicator">
      Loading member details...
    </div>
    
    <div v-else-if="member" class="member-detail-content">
      <div class="member-header">
        <h1>{{ member.name }}</h1>
        <router-link 
          :to="{ name: 'MemberList' }" 
          class="back-button"
        >
          Back to List
        </router-link>
      </div>
      
      <div class="member-info-section">
        <h2>Basic Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">ID:</span>
            <span class="info-value">{{ member.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Phone:</span>
            <span class="info-value">{{ member.phone }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Email:</span>
            <span class="info-value">{{ member.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Join Date:</span>
            <span class="info-value">{{ formatDate(member.join_date) }}</span>
          </div>
        </div>
      </div>
      
      <div class="member-cards-section">
        <h2>Member Cards</h2>
        <div v-if="cards.length > 0" class="cards-list">
          <div v-for="card in cards" :key="card.id" class="card-item">
            <div class="card-number">Card: {{ card.card_number }}</div>
            <div class="card-status" :class="card.status.toLowerCase()">
              {{ card.status }}
            </div>
            <div class="card-expiry">Expires: {{ formatDate(card.expiry_date) }}</div>
          </div>
        </div>
        <div v-else class="no-cards">
          No cards associated with this member
        </div>
      </div>
      
      <div class="action-buttons">
        <button 
          @click="editMember" 
          class="edit-button"
        >
          Edit Member
        </button>
        <button 
          @click="addCard" 
          class="add-card-button"
        >
          Add Card
        </button>
      </div>
    </div>
    
    <div v-else class="error-message">
      Member not found
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { format } from 'date-fns';
import { getMemberById, getMemberCards } from '@/api/members';

export default {
  name: 'MemberDetailView',
  
  setup() {
    const route = useRoute();
    const router = useRouter();
    
    const member = ref(null);
    const cards = ref([]);
    const loading = ref(true);
    
    const fetchMemberData = async () => {
      try {
        loading.value = true;
        const memberId = route.params.id;
        
        // Fetch member details
        const memberResponse = await getMemberById(memberId);
        member.value = memberResponse.data;
        
        // Fetch member cards
        const cardsResponse = await getMemberCards(memberId);
        cards.value = cardsResponse.data;
      } catch (error) {
        console.error('Error fetching member details:', error);
      } finally {
        loading.value = false;
      }
    };
    
    const formatDate = (dateString) => {
      if (!dateString) return 'N/A';
      return format(new Date(dateString), 'yyyy-MM-dd');
    };
    
    const editMember = () => {
      router.push({ name: 'MemberEdit', params: { id: route.params.id } });
    };
    
    const addCard = () => {
      router.push({ 
        name: 'MemberCardCreate', 
        params: { memberId: route.params.id } 
      });
    };
    
    onMounted(() => {
      fetchMemberData();
    });
    
    return {
      member,
      cards,
      loading,
      formatDate,
      editMember,
      addCard
    };
  }
};
</script>

<style scoped>
.member-detail-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.loading-indicator {
  text-align: center;
  padding: 40px;
  font-size: 1.2rem;
  color: #666;
}

.member-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.back-button {
  padding: 8px 16px;
  background-color: #f0f0f0;
  color: #333;
  text-decoration: none;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.back-button:hover {
  background-color: #e0e0e0;
}

.member-info-section {
  margin-bottom: 30px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-top: 15px;
}

.info-item {
  display: flex;
  gap: 10px;
}

.info-label {
  font-weight: bold;
  color: #555;
}

.member-cards-section {
  margin-bottom: 30px;
}

.cards-list {
  margin-top: 15px;
  display: grid;
  gap: 10px;
}

.card-item {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.9rem;
}

.card-status.active {
  background-color: #e6f7e6;
  color: #2e7d32;
}

.card-status.expired {
  background-color: #ffebee;
  color: #c62828;
}

.card-status.inactive {
  background-color: #fff8e1;
  color: #f57f17;
}

.no-cards {
  margin-top: 15px;
  color: #666;
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.edit-button, .add-card-button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s;
}

.edit-button {
  background-color: #2196f3;
  color: white;
}

.edit-button:hover {
  background-color: #1976d2;
}

.add-card-button {
  background-color: #4caf50;
  color: white;
}

.add-card-button:hover {
  background-color: #388e3c;
}

.error-message {
  text-align: center;
  padding: 40px;
  color: #c62828;
  font-size: 1.2rem;
}
</style>