import { defineStore } from 'pinia';
import { api } from '../utils/api.js';

export const usePlanStore = defineStore('plan', {
  state: () => ({
    currentPlan: null,
    selectedPlan: null,
    plans: [],
    membershipStatus: null,
    loading: false,
    error: null
  }),

  getters: {
    isExpired: (state) => {
      if (!state.membershipStatus?.expiryDate) return true;
      return new Date(state.membershipStatus.expiryDate) < new Date();
    },
    daysUntilExpiry: (state) => {
      if (!state.membershipStatus?.expiryDate) return 0;
      const diff = new Date(state.membershipStatus.expiryDate) - new Date();
      return Math.ceil(diff / (1000 * 60 * 60 * 24));
    }
  },

  actions: {
    async fetchPlans() {
      this.loading = true;
      try {
        const response = await api.get('/plans');
        this.plans = response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchMembershipStatus() {
      this.loading = true;
      try {
        const response = await api.get('/membership/status');
        this.membershipStatus = response.data;
        this.currentPlan = response.data.plan;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    selectPlan(plan) {
      this.selectedPlan = plan;
      this.saveToLocalStorage();
    },

    async renewMembership(paymentMethod) {
      if (!this.selectedPlan) {
        throw new Error('No plan selected');
      }

      this.loading = true;
      try {
        const response = await api.post('/membership/renew', {
          planId: this.selectedPlan.id,
          paymentMethod
        });
        
        if (response.data.success) {
          await this.fetchMembershipStatus();
          this.selectedPlan = null;
          this.saveToLocalStorage();
        }
        
        return response.data;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    saveToLocalStorage() {
      const state = {
        selectedPlan: this.selectedPlan,
        currentPlan: this.currentPlan,
        membershipStatus: this.membershipStatus
      };
      localStorage.setItem('planStore', JSON.stringify(state));
    },

    loadFromLocalStorage() {
      const saved = localStorage.getItem('planStore');
      if (saved) {
        const state = JSON.parse(saved);
        this.selectedPlan = state.selectedPlan || null;
        this.currentPlan = state.currentPlan || null;
        this.membershipStatus = state.membershipStatus || null;
      }
    },

    clearError() {
      this.error = null;
    }
  }
});
