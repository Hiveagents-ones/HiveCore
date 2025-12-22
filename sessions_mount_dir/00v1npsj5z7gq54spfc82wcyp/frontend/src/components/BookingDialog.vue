<template>
  <v-dialog
    v-model="dialog"
    max-width="500"
    persistent
  >
    <v-card>
      <v-card-title class="text-h5">
        {{ isBooking ? '确认预约' : '确认取消预约' }}
      </v-card-title>

      <v-card-text>
        <p v-if="isBooking">您确定要预约该课程吗？</p>
        <p v-else>您确定要取消该课程的预约吗？</p>
        
        <v-alert
          v-if="remainingSeatsWarning"
          type="warning"
          class="mt-4"
        >
          该课程仅剩 {{ remainingSeats }} 个名额
        </v-alert>
        
        <v-alert
          v-if="concurrencyWarning"
          type="warning"
          class="mt-4"
        >
          该课程预约人数较多，请尽快确认
        </v-alert>

        <v-alert
          v-if="error"
          type="error"
          class="mt-4"
        >
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="secondary"
          @click="closeDialog"
        >
          取消
        </v-btn>
        <v-btn
          color="primary"
          :loading="loading"
          @click="confirmAction"
        >
          确认
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue';
import { useSnackbar } from '../composables/useSnackbar';

const { showSnackbar } = useSnackbar();

const props = defineProps({
  isBooking: {
    type: Boolean,
    default: true
  },
  courseId: {
    type: Number,
    required: true
  }
});

const emit = defineEmits(['confirmed', 'closed']);

const dialog = ref(false);
const loading = ref(false);
const error = ref(null);
const concurrencyWarning = ref(false);
const remainingSeats = ref(0);
const remainingSeatsWarning = ref(false);
const permissionWarning = ref(false);

const openDialog = (seatsInfo, hasPermission = true) => {
  permissionWarning.value = false;
  concurrencyWarning.value = false;
  remainingSeatsWarning.value = false;
  dialog.value = true;
  error.value = null;
  
  if (seatsInfo && seatsInfo.remainingSeats > 0 && seatsInfo.remainingSeats <= 3) {
    remainingSeats.value = seatsInfo.remainingSeats;
    remainingSeatsWarning.value = true;
  }
  
  if (!hasPermission) {
    permissionWarning.value = true;
  }
  }
};

const closeDialog = () => {
  dialog.value = false;
  error.value = null;
  emit('closed');
};

const confirmAction = async () => {
  loading.value = true;
  error.value = null;

  try {
    emit('confirmed', props.courseId);
    closeDialog();
    showSnackbar({
      message: props.isBooking ? '课程预约成功' : '课程取消成功',
      color: 'success'
    });
  } catch (err) {
    error.value = err.message || (props.isBooking ? '预约失败' : '取消预约失败');
  } finally {
    loading.value = false;
  }
};

defineExpose({
  openDialog,
  closeDialog
});
</script>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

        <v-alert
          v-if="permissionWarning"
          type="warning"
          class="mt-4"
        >
          您没有预约该课程的权限
        </v-alert>