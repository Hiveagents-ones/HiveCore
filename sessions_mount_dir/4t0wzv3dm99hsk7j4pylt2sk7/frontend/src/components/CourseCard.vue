<template>
  <div class="course-card">
    <h3>{{ course.name }}</h3>
    <p><strong>教练:</strong> {{ course.coach }}</p>
    <p><strong>时间:</strong> {{ formattedTime }}</p>
    <p><strong>地点:</strong> {{ course.location }}</p>
    <p><strong>剩余名额:</strong> {{ remainingSlots }}</p>
    <p v-if="course.description" class="description">{{ course.description }}</p>
    <button 
      @click="$emit('enroll', course.id)" 
      :disabled="remainingSlots === 0"
      class="enroll-btn"
    >
      {{ remainingSlots > 0 ? '立即报名' : '已满员' }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  course: {
    type: Object,
    required: true
  },
  enrolledCount: {
    type: Number,
    default: 0
  }
})

defineEmits(['enroll'])

const formattedTime = computed(() => {
  return new Date(props.course.time).toLocaleString()
})

const remainingSlots = computed(() => {
  return Math.max(0, props.course.capacity - props.enrolledCount)
})
</script>

<style scoped>
.course-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.course-card h3 {
  margin-top: 0;
  color: #333;
}

.description {
  color: #666;
  font-style: italic;
  margin: 10px 0;
}

.enroll-btn {
  width: 100%;
  padding: 10px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.enroll-btn:hover:not(:disabled) {
  background-color: #218838;
}

.enroll-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
</style>
