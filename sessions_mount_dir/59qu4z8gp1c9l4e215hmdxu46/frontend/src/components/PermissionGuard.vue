<template>
  <slot v-if="hasPermission" />
  <div v-else class="permission-denied">
    <el-alert
      title="权限不足"
      type="error"
      :closable="false"
      center
    >
      您没有访问此页面的权限，请联系管理员
    </el-alert>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';

const props = defineProps({
  requiredPermission: {
    type: String,
    required: true
  }
});

const store = useStore();

const hasPermission = computed(() => {
  const userPermissions = store.state.user.permissions || [];
  return userPermissions.includes(props.requiredPermission);
});
</script>

<style scoped>
.permission-denied {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 20px;
}
</style>