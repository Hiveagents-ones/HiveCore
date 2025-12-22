<template>
  <div class="member-form">
    <h2>{{ formTitle }}</h2>
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
        <label for="joinDate">加入日期</label>
        <input 
          type="date" 
          id="joinDate" 
          v-model="formData.join_date"
          required
        />
      </div>
      
      <div class="form-actions">
        <button type="submit" class="btn-submit">提交</button>
        <button type="button" class="btn-cancel" @click="resetForm">重置</button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { useMemberStore } from '@/stores/member';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

export default {
  name: 'MemberForm',
  props: {
    member: {
      type: Object,
      default: () => ({
        id: null,
        name: '',
        phone: '',
        email: '',
        join_date: new Date().toISOString().split('T')[0]
      })
    },
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const router = useRouter();
    const authStore = useAuthStore();
    const formData = ref({ ...props.member });
    
    // 敏感字段掩码处理
    if (props.isEdit && formData.value.phone) {
      formData.value.phone = formData.value.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
    }
    
    const formTitle = computed(() => {
      return props.isEdit ? '编辑会员信息' : '新增会员';
    });
    
    const submitForm = async () => {
      try {
        const url = '/api/v1/members';
        const method = props.isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData.value)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || '提交失败');
        }
        
        router.push({ name: 'Members' });
      } catch (error) {
        console.error('Error submitting form:', error);
        alert('提交失败，请重试');
      }
    };
    
    const resetForm = () => {
      formData.value = { ...props.member };
    };
    
    return {
      formData,
      formTitle,
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
  margin-bottom: 20px;
  color: #333;
  text-align: center;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

input {
  input[type="date"] {
    appearance: none;
    -webkit-appearance: none;
    min-height: 38px;
  }
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
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
}

.btn-submit {
  background-color: #4CAF50;
  color: white;
}

.btn-cancel {
  background-color: #f44336;
  color: white;
}

button:hover {
  opacity: 0.9;
}
</style>