<template>
  <div class="member-detail-view">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="member-detail-container">
      <h1>Member Details</h1>
      
      <div class="member-info">
        <div class="info-row">
        <div class="info-row">
          <span class="label">Membership Status:</span>
          <div class="value">
            <select v-model="member.membership_status" @change="updateStatus" class="status-select">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
              <option value="expired">Expired</option>
            </select>
          </div>
        </div>
          <span class="label">ID:</span>
          <span class="value">{{ member.id }}</span>
        </div>
        <div class="info-row">
          <span class="label">Name:</span>
          <span class="value">{{ member.name }}</span>
        </div>
        <div class="info-row">
          <span class="label">Email:</span>
          <span class="value">{{ member.email }}</span>
        </div>
        <div class="info-row">
          <span class="label">Phone:</span>
          <span class="value">{{ member.phone }}</span>
        </div>

      </div>
      
      <div class="action-buttons">
        <button @click="goBack" class="btn btn-secondary">Back</button>
        <button @click="editMember" class="btn btn-primary">Edit</button>
        <button @click="deleteMember" class="btn btn-danger">Delete</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getMemberById, deleteMember as apiDeleteMember } from '../api/members';
import { updateMemberStatus } from '../api/members';

export default {
  name: 'MemberDetailView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const memberId = route.params.id;
    
    const member = ref({});
    const loading = ref(true);
    const error = ref(null);

    const fetchMember = async () => {
      try {
        loading.value = true;
        const response = await getMemberById(memberId);
        member.value = response.data;
      } catch (err) {
        error.value = 'Failed to fetch member details';
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    const goBack = () => {
      router.push('/members');
    };

    const editMember = () => {
      router.push(`/members/${memberId}/edit`);
    };

    const updateStatus = async () => {
      try {
        await updateMemberStatus(memberId, { membership_status: member.value.membership_status });
      } catch (err) {
        error.value = 'Failed to update membership status';
        console.error(err);
      }
    };

    const deleteMember = async () => {
      if (confirm('Are you sure you want to delete this member?')) {
        try {
          await apiDeleteMember(memberId);
          router.push('/members');
        } catch (err) {
          error.value = 'Failed to delete member';
          console.error(err);
        }
      }
    };

    onMounted(() => {
      fetchMember();
    });

    return {
      member,
      loading,
      error,
      goBack,
      editMember,
      deleteMember,
      updateStatus
    };
  }
};
</script>

<style scoped>
.member-detail-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  font-size: 18px;
}

.error {
  color: red;
}

.member-detail-container {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.member-info {
  margin-bottom: 20px;
}

.info-row {
  display: flex;
  margin-bottom: 10px;
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.label {
  font-weight: bold;
  width: 150px;
}

.value {
  flex: 1;
}

.status-select {
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 150px;
  flex: 1;
}

.action-buttons {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}
</style>