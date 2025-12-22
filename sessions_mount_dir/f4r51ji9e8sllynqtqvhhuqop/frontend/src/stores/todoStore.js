import { defineStore } from 'pinia';
import { todosApi } from '../api/todos.js';

export const useTodoStore = defineStore('todo', {
  state: () => ({
    todos: [],
    loading: false,
    error: null,
  }),

  getters: {
    completedTodos: (state) => state.todos.filter(todo => todo.completed),
    pendingTodos: (state) => state.todos.filter(todo => !todo.completed),
    totalCount: (state) => state.todos.length,
    completedCount: (state) => state.todos.filter(todo => todo.completed).length,
  },

  actions: {
    async fetchTodos() {
      this.loading = true;
      this.error = null;
      try {
        const todos = await todosApi.getTodos();
        this.todos = todos;
      } catch (error) {
        this.error = 'Failed to fetch todos';
        console.error('Store error:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async addTodo(content) {
      this.loading = true;
      this.error = null;
      try {
        const newTodo = await todosApi.createTodo(content);
        this.todos.push(newTodo);
        return newTodo;
      } catch (error) {
        this.error = 'Failed to create todo';
        console.error('Store error:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async toggleTodo(id) {
      const todo = this.todos.find(t => t.id === id);
      if (!todo) return;

      this.loading = true;
      this.error = null;
      try {
        const updatedTodo = await todosApi.updateTodo(id, !todo.completed);
        const index = this.todos.findIndex(t => t.id === id);
        if (index !== -1) {
          this.todos[index] = updatedTodo;
        }
        return updatedTodo;
      } catch (error) {
        this.error = 'Failed to update todo';
        console.error('Store error:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async removeTodo(id) {
      this.loading = true;
      this.error = null;
      try {
        await todosApi.deleteTodo(id);
        this.todos = this.todos.filter(todo => todo.id !== id);
      } catch (error) {
        this.error = 'Failed to delete todo';
        console.error('Store error:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    clearError() {
      this.error = null;
    },
  },
});