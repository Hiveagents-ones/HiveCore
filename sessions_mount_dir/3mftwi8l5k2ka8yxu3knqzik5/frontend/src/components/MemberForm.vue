<template>
  <el-form
    ref="memberFormRef"
    :model="formData"
    :rules="rules"
    label-width="120px"
    class="member-form"
  >
    <el-form-item label="姓名" prop="name">
      <el-input v-model="formData.name" placeholder="请输入会员姓名" />
    </el-form-item>

    <el-form-item label="联系方式" prop="phone">
      <el-input v-model="formData.phone" placeholder="请输入手机号码" />
    </el-form-item>

    <el-form-item label="邮箱" prop="email">
      <el-input v-model="formData.email" placeholder="请输入邮箱地址" />
    </el-form-item>

    <el-form-item label="会员卡号" prop="card_number">
      <el-input v-model="formData.card_number" placeholder="请输入会员卡号" />
    </el-form-item>

    <el-form-item label="会员等级" prop="level">
      <el-select v-model="formData.level" placeholder="请选择会员等级" style="width: 100%">
        <el-option label="普通会员" value="regular" />
        <el-option label="银卡会员" value="silver" />
        <el-option label="金卡会员" value="gold" />
        <el-option label="钻石会员" value="diamond" />
      </el-select>
    </el-form-item>

    <el-form-item label="会员状态" prop="status">
      <el-select v-model="formData.status" placeholder="请选择会员状态" style="width: 100%">
        <el-option label="活跃" value="active" />
        <el-option label="冻结" value="frozen" />
        <el-option label="过期" value="expired" />
      </el-select>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="submitForm" :loading="loading">
        {{ isEdit ? '更新' : '创建' }}
      </el-button>
      <el-button @click="resetForm">重置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import memberApi from '../api/member';

const props = defineProps({
  memberId: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['success', 'cancel']);

const memberFormRef = ref(null);
const loading = ref(false);
const isEdit = ref(false);

const formData = reactive({
  name: '',
  phone: '',
  email: '',
  card_number: '',
  level: 'regular',
  status: 'active'
});

const rules = {
  name: [
    { required: true, message: '请输入会员姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  card_number: [
    { required: true, message: '请输入会员卡号', trigger: 'blur' },
    { min: 6, max: 20, message: '会员卡号长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  level: [
    { required: true, message: '请选择会员等级', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择会员状态', trigger: 'change' }
  ]
};

const submitForm = async () => {
  if (!memberFormRef.value) return;
  
  try {
    await memberFormRef.value.validate();
    loading.value = true;
    
    if (isEdit.value) {
      await memberApi.updateMember(props.memberId, formData);
      ElMessage.success('会员信息更新成功');
    } else {
      await memberApi.createMember(formData);
      ElMessage.success('会员创建成功');
    }
    
    emit('success');
    resetForm();
  } catch (error) {
    console.error('表单提交失败:', error);
    ElMessage.error(error.response?.data?.detail || '操作失败，请重试');
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  if (memberFormRef.value) {
    memberFormRef.value.resetFields();
  }
  Object.assign(formData, {
    name: '',
    phone: '',
    email: '',
    card_number: '',
    level: 'regular',
    status: 'active'
  });
};

const loadMemberData = async () => {
  if (!props.memberId) return;
  
  try {
    loading.value = true;
    const response = await memberApi.getMemberById(props.memberId);
    Object.assign(formData, response.data);
    isEdit.value = true;
  } catch (error) {
    console.error('加载会员数据失败:', error);
    ElMessage.error('加载会员数据失败');
  } finally {
    loading.value = false;
  }
};

watch(() => props.memberId, (newVal) => {
  if (newVal) {
    loadMemberData();
  } else {
    isEdit.value = false;
    resetForm();
  }
}, { immediate: true });

onMounted(() => {
  if (props.memberId) {
    loadMemberData();
  }
});
</script>

<style scoped>
.member-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.el-form-item {
  margin-bottom: 24px;
}

.el-button {
  margin-right: 12px;
}
</style>