<template>
  <div v-if="show" class="conflict-alert">
    <div class="alert-content">
      <div class="alert-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-triangle">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <h3>教练排班冲突</h3>
      </div>
      <div class="alert-body">
        <p>{{ message }}</p>
        <ul v-if="conflicts && conflicts.length" class="conflict-list">
          <li v-for="(conflict, index) in conflicts" :key="index">
            {{ conflict }}
          </li>
        </ul>
      </div>
      <div class="alert-footer">
        <button @click="onConfirm">确认</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ScheduleConflictAlert',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    message: {
      type: String,
      default: '检测到排班时间冲突，请调整时间安排。'
    },
    conflicts: {
      type: Array,
      default: () => []
    }
  },
  methods: {
    onConfirm() {
      this.$emit('confirm');
    }
  }
};
</script>

<style scoped>
.conflict-alert {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.alert-content {
  background-color: white;
  border-radius: 8px;
  width: 400px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.alert-header {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.alert-header svg {
  color: #ff9800;
  margin-right: 10px;
}

.alert-header h3 {
  margin: 0;
  color: #333;
}

.alert-body {
  margin-bottom: 20px;
}

.alert-body p {
  margin-bottom: 10px;
}

.conflict-list {
  margin: 0;
  padding-left: 20px;
}

.conflict-list li {
  color: #f44336;
  margin-bottom: 5px;
}
  margin: 0;
  color: #666;
}

.alert-footer {
  display: flex;
  justify-content: flex-end;
}

.alert-footer button {
  padding: 8px 16px;
  background-color: #ff9800;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.alert-footer button:hover {
  background-color: #f57c00;
}
</style>