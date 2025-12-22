<template>
  <v-dialog
    v-model="dialog"
    max-width="500"
    persistent
  >
    <v-card>
      <v-card-title class="text-h5">
        排班冲突
      </v-card-title>

      <v-card-text>
        <p>您选择的排班时间与以下已有排班冲突：</p>
        <v-list>
          <v-list-item
            v-for="(conflict, index) in conflicts"
            :key="index"
          >
            <v-list-item-content>
              <v-list-item-title>{{ conflict.coachName }} 教练</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatTime(conflict.startTime) }} - {{ formatTime(conflict.endTime) }}
              </v-list-item-subtitle>
              <v-list-item-subtitle>
                课程: {{ conflict.courseName }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          color="primary"
          text
          @click="onConfirm"
        >
          确定
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref } from 'vue';
import { format } from 'date-fns';

export default {
  name: 'ScheduleConflictDialog',
  
  props: {
    value: {
      type: Boolean,
      required: true
    },
    conflicts: {
      type: Array,
      default: () => []
    }
  },
  
  emits: ['input', 'confirm'],
  
  setup(props, { emit }) {
    const dialog = ref(props.value);
    
    const onConfirm = () => {
      emit('confirm');
      emit('input', false);
    };
    
    const formatTime = (time) => {
      return format(new Date(time), 'yyyy-MM-dd HH:mm');
    };
    
    return {
      dialog,
      onConfirm,
      formatTime
    };
  },
  
  watch: {
    value(newVal) {
      this.dialog = newVal;
    },
    dialog(newVal) {
      this.$emit('input', newVal);
    }
  }
};
</script>

<style scoped>
.v-card-text {
  padding-bottom: 0;
}
</style>