<template>
  <div class="member-form-container">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑会员' : '创建会员' }}</span>
          <el-button @click="$router.go(-1)">返回</el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="120px"
        label-position="right"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入会员姓名" />
        </el-form-item>

        <el-form-item label="联系方式" prop="contact_info">
          <el-input
            v-model="formData.contact_info"
            placeholder="请输入手机号或邮箱"
          />
        </el-form-item>

        <el-form-item label="会员等级" prop="membership_level">
          <el-select
            v-model="formData.membership_level"
            placeholder="请选择会员等级"
            style="width: 100%"
          >
            <el-option label="普通会员" value="regular" />
            <el-option label="银卡会员" value="silver" />
            <el-option label="金卡会员" value="gold" />
            <el-option label="钻石会员" value="diamond" />
          </el-select>
        </el-form-item>

        <el-form-item label="入会日期" prop="join_date">
          <el-date-picker
            v-model="formData.join_date"
            type="date"
            placeholder="选择入会日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="到期日期" prop="expiry_date">
          <el-date-picker
            v-model="formData.expiry_date"
            type="date"
            placeholder="选择到期日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="健康状况" prop="health_status">
          <el-input
            v-model="formData.health_status"
            type="textarea"
            :rows="3"
            placeholder="请输入健康状况备注"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleSubmit"
          >
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { memberApi } from '@/api/member';

const route = useRoute();
const router = useRouter();
const formRef = ref(null);
const loading = ref(false);

// 表单数据
const formData = reactive({
  name: '',
  contact_info: '',
  membership_level: '',
  join_date: '',
  expiry_date: '',
  health_status: '',
});

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入会员姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  contact_info: [
    { required: true, message: '请输入联系方式', trigger: 'blur' },
    {
      pattern: /^1[3-9]\d{9}$|^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/,
      message: '请输入有效的手机号或邮箱',
      trigger: 'blur',
    },
  ],
  membership_level: [
    { required: true, message: '请选择会员等级', trigger: 'change' },
  ],
  join_date: [
    { required: true, message: '请选择入会日期', trigger: 'change' },
  ],
  expiry_date: [
    { required: true, message: '请选择到期日期', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (value && formData.join_date && value < formData.join_date) {
          callback(new Error('到期日期不能早于入会日期'));
        } else {
          callback();
        }
      },
      trigger: 'change',
    },
  ],
};

// 判断是否为编辑模式
const isEdit = computed(() => !!route.params.id);

// 获取会员详情
const fetchMemberDetail = async (id) => {
  try {
    loading.value = true;
    const data = await memberApi.getMember(id);
    Object.assign(formData, data);
  } catch (error) {
    ElMessage.error('获取会员信息失败');
    router.push('/members');
  } finally {
    loading.value = false;
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    loading.value = true;

    if (isEdit.value) {
      await memberApi.updateMember(route.params.id, formData);
      ElMessage.success('会员信息更新成功');
    } else {
      await memberApi.createMember(formData);
      ElMessage.success('会员创建成功');
    }

    router.push('/members');
  } catch (error) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail);
    } else {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败');
    }
  } finally {
    loading.value = false;
  }
};

// 重置表单
const handleReset = () => {
  if (!formRef.value) return;
  formRef.value.resetFields();
};

// 页面加载时获取会员详情（编辑模式）
onMounted(() => {
  if (isEdit.value) {
    fetchMemberDetail(route.params.id);
  }
});
</script>

<style scoped>
.member-form-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.form-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  font-size: 18px;
  font-weight: bold;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-button) {
  min-width: 100px;
}
</style>