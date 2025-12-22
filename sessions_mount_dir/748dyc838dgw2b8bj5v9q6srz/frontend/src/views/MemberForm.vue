<template>
  <div class="member-form-container">
    <el-card class="form-card">
      <h2 class="form-title">会员注册</h2>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="register-form"
      >
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="请输入11位手机号"
            maxlength="11"
          />
        </el-form-item>

        <el-form-item label="电子邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入有效邮箱地址"
            type="email"
          />
        </el-form-item>

        <el-form-item label="登录密码" prop="password">
          <el-input
            v-model="form.password"
            placeholder="至少8位字符"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="submitForm"
            :loading="submitting"
            class="submit-btn"
          >
            提交注册
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import axios from 'axios';

const form = reactive({
  phone: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (rule, value) => {
        return value === form.password ? true : new Error('两次密码不一致');
      },
      trigger: 'blur'
    }
  ]
};

const formRef = ref();
const submitting = ref(false);

const submitForm = async () => {
  formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true;
      try {
        const response = await axios.post('/api/v1/members', form);
        ElMessage.success('注册成功！会员卡已生成');
        // 重置表单
        form.phone = '';
        form.email = '';
        form.password = '';
        form.confirmPassword = '';
      } catch (error) {
        const message = error.response?.data?.detail || '注册失败，请重试';
        ElMessage.error(message);
      } finally {
        submitting.value = false;
      }
    }
  });
};
</script>

<style scoped>
.member-form-container {
  max-width: 600px;
  margin: 2rem auto;
}

.form-card {
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.form-title {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #303133;
}

.register-form {
  padding: 0 1rem;
}

.submit-btn {
  width: 100%;
  padding: 12px 0;
  font-size: 16px;
}
</style>