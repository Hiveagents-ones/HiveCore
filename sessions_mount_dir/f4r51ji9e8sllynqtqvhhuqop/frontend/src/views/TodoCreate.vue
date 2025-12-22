<template>
  <div class="todo-create">
    <h2>创建新的待办事项</h2>
    <form @submit.prevent="handleSubmit" class="todo-form">
      <div class="form-group">
        <label for="content">待办事项内容:</label>
        <input
          id="content"
          v-model="content"
          type="text"
          placeholder="请输入待办事项内容"
          required
          class="form-input"
        />
      </div>
      <button type="submit" :disabled="isSubmitting" class="submit-btn">
        {{ isSubmitting ? '创建中...' : '创建' }}
      </button>
    </form>
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { todosApi } from '../api/todos.js';

export default {
  name: 'TodoCreate',
  emits: ['created'],
  setup(props, { emit }) {
    const content = ref('');
    const isSubmitting = ref(false);
    const error = ref('');

    const handleSubmit = async () => {
      if (!content.value.trim()) {
        error.value = '请输入待办事项内容';
        return;
      }

      isSubmitting.value = true;
      error.value = '';

      try {
        const newTodo = await todosApi.createTodo(content.value);
        content.value = '';
        emit('created', newTodo);
      } catch (err) {
        error.value = '创建待办事项失败，请重试';
        console.error('Create todo error:', err);
      } finally {
        isSubmitting.value = false;
      }
    };

    return {
      content,
      isSubmitting,
      error,
      handleSubmit,
    };
  },
};
</script>

<style scoped>
.todo-create {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.todo-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-weight: bold;
  color: #333;
}

.form-input {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

.form-input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
}

.submit-btn {
  padding: 10px 20px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover:not(:disabled) {
  background-color: #357abd;
}

.submit-btn:disabled {
  background-color: #a0a0a0;
  cursor: not-allowed;
}

.error-message {
  margin-top: 10px;
  padding: 10px;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 4px;
  border: 1px solid #ef5350;
}
</style>