<template>
  <div class="member-form">
    <h2>{{ isEditMode ? '编辑会员信息' : '添加新会员' }}</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="name">姓名</label>
        <input 
          type="text" 
          id="name" 
          v-model="formData.name" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="phone">电话</label>
        <input 
          type="tel" 
          id="phone" 
          v-model="formData.phone" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="email">邮箱</label>
        <input 
          type="email" 
          id="email" 
          v-model="formData.email"
        />
      </div>
      
      <div class="form-group">
        <label for="card_status">会员卡状态</label>
        <select 
          id="card_status" 
          v-model="formData.card_status"
          required
        >
          <option value="active">激活</option>
          <option value="inactive">未激活</option>
          <option value="expired">已过期</option>
        </select>
      </div>
      
      <div class="form-actions">
        <button type="submit" class="btn-submit">
          {{ isEditMode ? '更新' : '提交' }}
        </button>
        <button 
          type="button" 
          class="btn-cancel"
          @click="goBack"
        >
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getMember, createMember, updateMember } from '../api/members';

export default {
  name: 'MemberFormView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    
    const isEditMode = ref(false);
    const memberId = ref(null);
    
    const formData = ref({
      name: '',
      phone: '',
      email: '',
      card_status: 'active'
    });
    
    // 检查是否是编辑模式
    onMounted(async () => {
      if (route.params.id) {
        isEditMode.value = true;
        memberId.value = route.params.id;
        try {
          const response = await getMember(memberId.value);
          formData.value = response.data;
        } catch (error) {
          console.error('获取会员信息失败:', error);
        }
      }
    });
    
    // 提交表单
    const submitForm = async () => {
      try {
        if (isEditMode.value) {
          await updateMember(memberId.value, formData.value);
        } else {
          await createMember(formData.value);
        }
        router.push({ name: 'MemberList' });
      } catch (error) {
        console.error('提交表单失败:', error);
      }
    };
    
    // 返回会员列表
    const goBack = () => {
      router.push({ name: 'MemberList' });
    };
    
    return {
      isEditMode,
      formData,
      submitForm,
      goBack
    };
  }
};
</script>

<style scoped>
.member-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input, select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

.btn-submit, .btn-cancel {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.btn-submit {
  background-color: #4CAF50;
  color: white;
}

.btn-submit:hover {
  background-color: #45a049;
}

.btn-cancel {
  background-color: #f44336;
  color: white;
}

.btn-cancel:hover {
  background-color: #d32f2f;
}
</style>