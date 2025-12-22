<template>
  <div class="member-form-container">
    <el-page-header @back="goBack" :title="isEdit ? t('member.editMember') : t('member.createMember')">
      <template #content>
        <span class="text-ellipsis">{{ isEdit ? t('member.editMemberInfo') : t('member.fillNewMemberInfo') }}</span>
      </template>
    </el-page-header>

    <el-divider />

    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      status-icon
      class="member-form"
    >
      <el-form-item :label="t('member.name')" prop="name">
        <el-input v-model="formData.name" :placeholder="t('member.namePlaceholder')" />
      </el-form-item>

      <el-form-item :label="t('member.contactInfo')" prop="contact_info">
        <el-input v-model="formData.contact_info" :placeholder="t('member.contactInfoPlaceholder')" />
      </el-form-item>

      <el-form-item :label="t('member.level')" prop="level">
        <el-select v-model="formData.level" :placeholder="t('member.levelPlaceholder')" clearable>
          <el-option
            v-for="item in levelOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item :label="t('member.remainingMembership')" prop="remaining_membership">
        <el-input-number
          v-model="formData.remaining_membership"
          :min="0"
          :precision="2"
          :placeholder="t('member.remainingMembershipPlaceholder')"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="submitForm(formRef)" :loading="loading">
          {{ isEdit ? t('member.update') : t('member.create') }}
        </el-button>
        <el-button @click="resetForm(formRef)">{{ t('member.reset') }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { memberApi } from '@/api/member';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const formRef = ref();
const loading = ref(false);

const isEdit = ref(false);
const memberId = ref(null);

// 表单数据
const formData = reactive({
  name: '',
  contact_info: '',
  level: '',
  remaining_membership: 0,
});

// 表单校验规则
const rules = reactive({
  name: [
    { required: true, message: t('member.nameRequired'), trigger: 'blur' },
    { min: 2, max: 50, message: t('member.nameLength'), trigger: 'blur' },
  ],
  contact_info: [
    { required: true, message: t('member.contactInfoRequired'), trigger: 'blur' },
    {
      pattern: /^1[3-9]\d{9}$|^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$/,
      message: t('member.contactInfoInvalid'),
      trigger: 'blur',
    },
  ],
  level: [{ required: true, message: t('member.levelRequired'), trigger: 'change' }],
  remaining_membership: [
    { required: true, message: t('member.remainingMembershipRequired'), trigger: 'blur' },
    { type: 'number', min: 0, message: t('member.remainingMembershipMin'), trigger: 'blur' },
  ],
});

// 会员等级选项
const levelOptions = [
  { value: 'standard', label: t('member.levelStandard') },
  { value: 'silver', label: t('member.levelSilver') },
  { value: 'gold', label: t('member.levelGold') },
  { value: 'platinum', label: t('member.levelPlatinum') },
];

// 提交表单
const submitForm = async (formEl) => {
  if (!formEl) return;

  await formEl.validate(async (valid, fields) => {
    if (valid) {
      loading.value = true;
      try {
        if (isEdit.value) {
          await memberApi.updateMember(memberId.value, formData);
          ElMessage.success(t('member.updateSuccess'));
        } else {
          await memberApi.createMember(formData);
          ElMessage.success(t('member.createSuccess'));
        }
        router.push({ name: 'MemberList' });
      } catch (error) {
        console.error('提交失败:', error);
        ElMessage.error(error.response?.data?.detail || t('member.operationFailed'));
      } finally {
        loading.value = false;
      }
    } else {
      console.log('表单校验失败:', fields);
    }
  });
};

// 重置表单
const resetForm = (formEl) => {
  if (!formEl) return;
  formEl.resetFields();
};

// 返回上一页
const goBack = () => {
  router.push({ name: 'MemberList' });
};

// 获取会员详情（编辑时使用）
const fetchMemberDetail = async (id) => {
  try {
    const data = await memberApi.getMember(id);
    Object.assign(formData, data);
  } catch (error) {
    console.error('获取会员详情失败:', error);
    ElMessage.error(t('member.fetchDetailFailed'));
    router.push({ name: 'MemberList' });
  }
};

// 组件挂载时判断是创建还是编辑
onMounted(() => {
  if (route.name === 'MemberEdit' && route.params.id) {
    isEdit.value = true;
    memberId.value = route.params.id;
    fetchMemberDetail(memberId.value);
  }
});
</script>

<style scoped>
.member-form-container {
  padding: 20px;
}

.member-form {
  max-width: 600px;
  margin-top: 20px;
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>