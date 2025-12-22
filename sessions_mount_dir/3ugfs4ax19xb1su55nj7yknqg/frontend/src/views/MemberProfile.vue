<template>
  <div class="member-profile">
    <div v-if="loading" class="loading-indicator">
      Loading member data...
    </div>
    
    <div v-else-if="member" class="profile-container">
      <h1>Member Profile</h1>
      
      <div class="profile-details">
        <div class="detail-row">
          <span class="detail-label">ID:</span>
          <span class="detail-value">{{ member.id }}</span>
        </div>
        
        <div class="detail-row">
          <span class="detail-label">Name:</span>
          <span class="detail-value">{{ member.name }}</span>
        </div>
        
        <div class="detail-row">
          <span class="detail-label">Phone:</span>
          <span class="detail-value">{{ member.phone }}</span>
        </div>
        
        <div class="detail-row">
          <span class="detail-label">Email:</span>
          <span class="detail-value">{{ member.email }}</span>
        </div>
        
        <div class="detail-row">
          <span class="detail-label">Membership Type:</span>
          <span class="detail-value">{{ member.membership_type }}</span>
        </div>
      </div>
      
      <router-link 
        :to="{ name: 'MemberForm', params: { id: member.id } }" 
        class="edit-button"
      >
        Edit Profile
      </router-link>
    </div>
    
    <div v-else class="error-message">
      Member not found
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { getMemberById } from '../api/members';

export default {
  name: 'MemberProfile',
  
  setup() {
    const member = ref(null);
    const loading = ref(true);
    const route = useRoute();
    
    onMounted(async () => {
      try {
        const memberId = route.params.id;
        const response = await getMemberById(memberId);
        member.value = response.data;
      } catch (error) {
        console.error('Error fetching member:', error);
      } finally {
        loading.value = false;
      }
    });
    
    return {
      member,
      loading
    };
  }
};
</script>

<style scoped>
.member-profile {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.loading-indicator {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.profile-container {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.profile-details {
  margin: 20px 0;
}

.detail-row {
  display: flex;
  margin-bottom: 10px;
  padding: 10px;
  background-color: white;
  border-radius: 4px;
}

.detail-label {
  font-weight: bold;
  width: 150px;
}

.detail-value {
  flex: 1;
}

.edit-button {
  display: inline-block;
  padding: 10px 15px;
  background-color: #4CAF50;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.edit-button:hover {
  background-color: #45a049;
}

.error-message {
  color: #dc3545;
  text-align: center;
  padding: 20px;
  font-size: 18px;
}
</style>