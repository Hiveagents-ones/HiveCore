<template>
  <div class="member-form">
    <h2>{{ formTitle }}</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="name">姓名</label>
        <input 
          id="name" 
          v-model="formData.name" 
          type="text" 
          required 
          placeholder="请输入姓名"
        />
      </div>
      
      <div class="form-group">
        <label for="phone">电话</label>
        <input 
          id="phone" 
          v-model="formData.phone" 
          type="tel" 
          required 
          placeholder="请输入电话号码"
        />
      </div>
      
      <div class="form-group">
        <label for="email">邮箱</label>
        <input 
          id="email" 
          v-model="formData.email" 
          type="email" 
          placeholder="请输入邮箱"
        />
      </div>
      
      <div class="form-group">
        <label for="membership_type">会员类型</label>
        <select 
          id="membership_type" 
          v-model="formData.membership_type" 
          required
        >
          <option value="">请选择会员类型</option>
          <option value="standard">标准会员</option>
          <option value="premium">高级会员</option>
          <option value="vip">VIP会员</option>
        </select>
      </div>
      
      <div class="form-actions">
        <button type="button" @click="resetForm">重置</button>
        <button type="submit">{{ submitButtonText }}</button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from '../api/axios';

export default {
  name: 'MemberForm',
  
  setup() {
    const route = useRoute();
    const router = useRouter();
    
    const isEditMode = ref(false);
    const memberId = ref(null);
    
    const formData = ref({
      name: '',
      phone: '',
      email: '',
      membership_type: ''
    });
    
    const formTitle = computed(() => {
      return isEditMode.value ? '编辑会员信息' : '新增会员';
    });
    
    const submitButtonText = computed(() => {
      return isEditMode.value ? '更新' : '提交';
    });
    
    // 初始化表单数据
    const initFormData = async () => {
      if (route.params.id) {
        isEditMode.value = true;
        memberId.value = route.params.id;
        try {
          const response = await axios.get(`/api/v1/members/${memberId.value}`);
          formData.value = response.data;
        } catch (error) {
          console.error('获取会员信息失败:', error);
        }
      }
    };
    
    // 提交表单
    const submitForm = async () => {
      try {
        if (isEditMode.value) {
          await axios.put(`/api/v1/members/${memberId.value}`, formData.value);
        } else {
          await axios.post('/api/v1/members', formData.value);
        }
        router.push('/members');
      } catch (error) {
        console.error('提交表单失败:', error);
      }
    };
    
    // 重置表单
    const resetForm = () => {
      if (isEditMode.value) {
        initFormData();
      } else {
        formData.value = {
          name: '',
          phone: '',
          email: '',
          membership_type: ''
        };
      }
    };
    
    // 初始化
    initFormData();
    
    return {
      formData,
      formTitle,
      submitButtonText,
      submitForm,
      resetForm
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

button {
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

button[type="submit"] {
  background-color: #4CAF50;
  color: white;
}

button[type="button"] {
  background-color: #f44336;
  color: white;
}

button:hover {
  opacity: 0.9;
}
</style>