<template>
  <slot v-if="hasPermission"></slot>
</template>

<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';

const props = defineProps({
  requiredPermission: {
    type: String,
    required: true
  },
  resource: {
    type: String,
    default: ''
  }
});

const store = useStore();
const router = useRouter();

const hasPermission = computed(() => {
  const userPermissions = store.getters['auth/permissions'];
  
  // Check if user has the required permission
  if (props.resource) {
    // For resource-specific permissions (e.g. 'payments:read')
    return userPermissions.includes(`${props.resource}:${props.requiredPermission}`);
  } else {
    // For general permissions (e.g. 'admin')
    return userPermissions.includes(props.requiredPermission);
  }
});
</script>

<style scoped>
/* Add any component-specific styles here */
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
const hasPermission = computed(() => {
  const userPermissions = store.getters['auth/permissions'];
  const currentRoute = router.currentRoute.value;

  // Check if user has the required permission
  if (props.resource) {
    // For resource-specific permissions (e.g. 'payments:read')
    return userPermissions.includes(`${props.resource}:${props.requiredPermission}`);
  } else {
    // For general permissions (e.g. 'admin')
    return userPermissions.includes(props.requiredPermission);
  }
});