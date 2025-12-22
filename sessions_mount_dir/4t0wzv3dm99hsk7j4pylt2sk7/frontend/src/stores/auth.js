import { defineStore } from 'pinia';
import { authAPI } from '../api/auth';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    roles: [],
    permissions: [],
    isAuthenticated: false,
    loading: false,
    error: null,
  }),

  getters: {
    hasRole: (state) => (roleName) => {
      return state.roles.some(role => role.name === roleName);
    },

    hasPermission: (state) => (resource, action) => {
      return state.permissions.some(permission => 
        permission.resource === resource && permission.action === action
      );
    },

    isCoach: (state) => state.hasRole('coach'),
    isAdmin: (state) => state.hasRole('admin') || state.hasRole('super_admin'),
    isReceptionist: (state) => state.hasRole('receptionist'),
  },

  actions: {
    async login(username, password) {
      this.loading = true;
      this.error = null;
      
      try {
        await authAPI.login(username, password);
        this.isAuthenticated = true;
        await this.fetchCurrentUser();
      } catch (error) {
        this.error = error.response?.data?.detail || 'Login failed';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    logout() {
      authAPI.logout();
      this.user = null;
      this.roles = [];
      this.permissions = [];
      this.isAuthenticated = false;
    },

    async fetchCurrentUser() {
      try {
        const userData = await authAPI.getCurrentUser();
        this.user = userData;
        this.roles = userData.roles || [];
        this.permissions = userData.roles?.flatMap(role => role.permissions) || [];
        this.isAuthenticated = true;
      } catch (error) {
        this.logout();
      }
    },

    async fetchRoles() {
      try {
        this.roles = await authAPI.getRoles();
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch roles';
      }
    },

    async createRole(roleData) {
      try {
        const newRole = await authAPI.createRole(roleData);
        this.roles.push(newRole);
        return newRole;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create role';
        throw error;
      }
    },

    async updateRole(roleId, roleData) {
      try {
        const updatedRole = await authAPI.updateRole(roleId, roleData);
        const index = this.roles.findIndex(role => role.id === roleId);
        if (index !== -1) {
          this.roles[index] = updatedRole;
        }
        return updatedRole;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update role';
        throw error;
      }
    },

    async deleteRole(roleId) {
      try {
        await authAPI.deleteRole(roleId);
        this.roles = this.roles.filter(role => role.id !== roleId);
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete role';
        throw error;
      }
    },

    async fetchPermissions() {
      try {
        const permissions = await authAPI.getPermissions();
        this.permissions = permissions;
        return permissions;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch permissions';
      }
    },

    checkAuth() {
      const token = localStorage.getItem('access_token');
      if (token && !this.isAuthenticated) {
        this.fetchCurrentUser();
      }
      return this.isAuthenticated;
    },
  },
});