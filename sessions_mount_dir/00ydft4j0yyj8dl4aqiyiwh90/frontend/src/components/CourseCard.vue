<template>
  <div class="course-card">
    <div class="card-header">
      <h3>{{ course.name }}</h3>
      <span class="course-type" :class="course.type.toLowerCase()">{{ course.type }}</span>
    </div>
    
    <div class="card-body">
      <div class="course-schedule">
        <span class="label">时间:</span>
        <span>{{ formatSchedule(course.schedule) }}</span>
      </div>
      
      <div class="course-duration">
        <span class="label">时长:</span>
        <span>{{ course.duration }}分钟</span>
      </div>
    </div>
    
    <div class="card-footer">
      <button 
        class="book-btn" 
        @click="handleBooking"
        :disabled="isBooked"
      >
        {{ isBooked ? '已预约' : '立即预约' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CourseCard',
  props: {
    course: {
      type: Object,
      required: true
    },
    isBooked: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    formatSchedule(schedule) {
      // 简单格式化日期时间显示
      return new Date(schedule).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    handleBooking() {
      this.$emit('book-course', this.course.id);
    }
  }
};
</script>

<style scoped>
.course-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.course-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #333;
}

.course-type {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
  text-transform: uppercase;
}

.course-type.group {
  background-color: #e3f2fd;
  color: #1976d2;
}

.course-type.private {
  background-color: #f3e5f5;
  color: #8e24aa;
}

.card-body {
  margin-bottom: 16px;
}

.card-body div {
  margin-bottom: 8px;
  display: flex;
}

.label {
  font-weight: bold;
  margin-right: 8px;
  color: #666;
  min-width: 40px;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

.book-btn {
  padding: 8px 16px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.book-btn:hover:not(:disabled) {
  background-color: #3aa876;
}

.book-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}
</style>