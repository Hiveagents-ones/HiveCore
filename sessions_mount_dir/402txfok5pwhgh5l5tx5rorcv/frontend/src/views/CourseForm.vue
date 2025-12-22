<template>
  <div class="course-form-container">
    <h2>{{ isEditing ? '编辑课程' : '创建新课程' }}</h2>
    <form @submit.prevent="handleSubmit" class="course-form">
      <div class="form-group">
        <label for="name">课程名称</label>
        <input
          type="text"
          id="name"
          v-model="course.name"
          required
          placeholder="例如：瑜伽、动感单车"
        />
      </div>

      <div class="form-group">
        <label for="coach">教练</label>
        <input
          type="text"
          id="coach"
          v-model="course.coach"
          required
          placeholder="请输入教练姓名"
        />
      </div>

      <div class="form-group">
        <label for="time">上课时间</label>
        <input
          type="datetime-local"
          id="time"
          v-model="course.time"
          required
        />
      </div>

      <div class="form-group">
        <label for="location">上课地点</label>
        <input
          type="text"
          id="location"
          v-model="course.location"
          required
          placeholder="例如：A教室、瑜伽室"
        />
      </div>

      <div class="form-group">
        <label for="capacity">容量限制</label>
        <input
          type="number"
          id="capacity"
          v-model.number="course.capacity"
          required
          min="1"
          placeholder="请输入最大容纳人数"
        />
      </div>

      <div class="form-group">
        <label for="description">课程描述</label>
        <textarea
          id="description"
          v-model="course.description"
          rows="4"
          placeholder="请输入课程详细描述"
        ></textarea>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
          {{ isSubmitting ? '提交中...' : (isEditing ? '更新课程' : '创建课程') }}
        </button>
        <button type="button" class="btn btn-secondary" @click="handleCancel">
          取消
        </button>
      </div>
    </form>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter, useRoute } from 'vue-router';
    const authStore = useAuthStore();

    // 检查管理员权限
    if (!authStore.isAdmin) {
      router.push('/');
      return;
    }
import { coursesApi } from '../api/courses.js';

export default {
  name: 'CourseForm',
  setup() {
    const router = useRouter();
    const route = useRoute();
    
    const isEditing = ref(false);
    const isSubmitting = ref(false);
    const error = ref('');
    
    const course = ref({
      name: '',
      coach: '',
      time: '',
      location: '',
      capacity: 20,
      description: ''
    });

    // 格式化日期时间以适应datetime-local输入
    const formatDateTimeForInput = (dateString) => {
      if (!dateString) return '';
      const date = new Date(dateString);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    };

    // 加载课程数据（编辑模式）
    const loadCourse = async (courseId) => {
      try {
        const data = await coursesApi.getCourseById(courseId);
        course.value = {
          ...data,
          time: formatDateTimeForInput(data.time)
        };
      } catch (err) {
        error.value = '加载课程数据失败';
        console.error('Error loading course:', err);
      }
    };

    // 处理表单提交
    const handleSubmit = async () => {
      isSubmitting.value = true;
      error.value = '';
      
      try {
        const courseData = {
          ...course.value,
          time: new Date(course.value.time).toISOString()
        };
        
        if (isEditing.value) {
          await coursesApi.updateCourse(route.params.id, courseData);
        } else {
          await coursesApi.createCourse(courseData);
        }
        
        router.push('/courses');
      } catch (err) {
        error.value = isEditing.value ? '更新课程失败' : '创建课程失败';
        console.error('Error submitting form:', err);
      } finally {
        isSubmitting.value = false;
      }
    };

    // 处理取消操作
    const handleCancel = () => {
      router.push('/courses');
    };

    // 组件挂载时检查是否为编辑模式
    onMounted(() => {
      const courseId = route.params.id;
      if (courseId) {
        isEditing.value = true;
        loadCourse(courseId);
      }
    });

    return {
      isEditing,
      isSubmitting,
      error,
      course,
      handleSubmit,
      handleCancel
    };
  }
};
</script>

<style scoped>
.course-form-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

h2 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.course-form {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}

input[type="text"],
input[type="number"],
input[type="datetime-local"],
textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: #4CAF50;
}

textarea {
  resize: vertical;
  min-height: 100px;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 30px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #45a049;
}

.btn-primary:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #f44336;
  color: white;
}

.btn-secondary:hover {
  background-color: #da190b;
}

.error-message {
  margin-top: 20px;
  padding: 10px;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 4px;
  text-align: center;
}
</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

    const authStore = useAuthStore();
    
    // 检查管理员权限
    if (!authStore.isAdmin) {
      router.push('/');
      return;
    }