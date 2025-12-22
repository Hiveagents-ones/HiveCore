<template>
  <div class="renewal-view">
    <div class="container">
      <h1 class="page-title">{{ $t('renewal.title') }}</h1>
      
      <!-- Membership Status Section -->
      <section class="membership-status">
        <h2>{{ $t('renewal.currentStatus') }}</h2>
        <div v-if="membershipStatus" class="status-card">
          <div class="status-info">
            <div class="status-badge" :class="membershipStatus.status">
              {{ $t(`membership.status.${membershipStatus.status}`) }}
            </div>
            <div class="expiry-info">
              <p>{{ $t('renewal.expiresOn') }}: {{ formatDate(membershipStatus.expires_at) }}</p>
              <p v-if="membershipStatus.days_remaining !== undefined" class="days-remaining">
                {{ $t('renewal.daysRemaining', { days: membershipStatus.days_remaining }) }}
              </p>
            </div>
          </div>
          <div class="status-actions">
            <button 
              v-if="membershipStatus.status === 'active'" 
              class="btn btn-secondary"
              @click="showCancelConfirmation = true"
            >
              {{ $t('renewal.cancelMembership') }}
            </button>
          </div>
        </div>
        <div v-else class="loading-placeholder">
          <div class="skeleton"></div>
        </div>
      </section>

      <!-- Membership Plans Section -->
      <section class="membership-plans">
        <h2>{{ $t('renewal.selectPlan') }}</h2>
        <div v-if="plans.length" class="plans-grid">
          <div 
            v-for="plan in plans" 
            :key="plan.id" 
            class="plan-card"
            :class="{ 
              'selected': selectedPlan?.id === plan.id,
              'recommended': plan.recommended 
            }"
            @click="selectPlan(plan)"
          >
            <div v-if="plan.recommended" class="recommended-badge">
              {{ $t('renewal.recommended') }}
            </div>
            <h3>{{ plan.name }}</h3>
            <div class="plan-price">
              <span class="currency">{{ plan.currency }}</span>
              <span class="amount">{{ plan.price }}</span>
              <span class="period">/{{ $t(`renewal.period.${plan.duration_unit}`) }}</span>
            </div>
            <ul class="plan-features">
              <li v-for="feature in plan.features" :key="feature">
                {{ feature }}
              </li>
            </ul>
            <button 
              class="btn btn-primary"
              :disabled="selectedPlan?.id === plan.id"
            >
              {{ selectedPlan?.id === plan.id ? $t('renewal.selected') : $t('renewal.select') }}
            </button>
          </div>
        </div>
        <div v-else class="loading-placeholder">
          <div class="skeleton"></div>
        </div>
      </section>

      <!-- Payment Section -->
      <section v-if="selectedPlan" class="payment-section">
        <h2>{{ $t('renewal.payment') }}</h2>
        <div class="selected-plan-summary">
          <h3>{{ $t('renewal.selectedPlanSummary') }}</h3>
          <div class="summary-item">
            <span>{{ $t('renewal.plan') }}:</span>
            <span>{{ selectedPlan.name }}</span>
          </div>
          <div class="summary-item">
            <span>{{ $t('renewal.price') }}:</span>
            <span>{{ formatCurrency(selectedPlan.price, selectedPlan.currency) }}</span>
          </div>
          <div class="summary-item">
            <span>{{ $t('renewal.duration') }}:</span>
            <span>{{ selectedPlan.duration }} {{ $t(`renewal.period.${selectedPlan.duration_unit}`) }}</span>
          </div>
        </div>
        <button class="btn btn-primary btn-large" @click="proceedToPayment">
          {{ $t('renewal.proceedToPayment') }}
        </button>
      </section>

      <!-- Membership History Section -->
      <section class="membership-history">
        <h2>{{ $t('renewal.history') }}</h2>
        <div v-if="history.length" class="history-list">
          <div v-for="item in history" :key="item.id" class="history-item">
            <div class="history-info">
              <h4>{{ item.plan_name }}</h4>
              <p>{{ $t('renewal.purchasedOn') }}: {{ formatDate(item.created_at) }}</p>
              <p>{{ $t('renewal.amount') }}: {{ formatCurrency(item.amount, item.currency) }}</p>
            </div>
            <div class="history-status">
              <span class="status-badge" :class="item.status">
                {{ $t(`payment.status.${item.status}`) }}
              </span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>{{ $t('renewal.noHistory') }}</p>
        </div>
      </section>
    </div>

    <!-- Payment Modal -->
    <PaymentModal
      :isVisible="isPaymentModalVisible"
      :selectedPlan="selectedPlan"
      @close="closePaymentModal"
      @payment-success="handlePaymentSuccess"
    />

    <!-- Cancel Confirmation Modal -->
    <div v-if="showCancelConfirmation" class="modal-overlay" @click.self="showCancelConfirmation = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ $t('renewal.confirmCancel') }}</h2>
          <button class="close-btn" @click="showCancelConfirmation = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>{{ $t('renewal.cancelWarning') }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCancelConfirmation = false">
            {{ $t('common.cancel') }}
          </button>
          <button class="btn btn-danger" @click="cancelMembership">
            {{ $t('renewal.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { membershipAPI } from '@/services/api';
import PaymentModal from '@/components/PaymentModal.vue';

const { t } = useI18n();

const membershipStatus = ref(null);
const plans = ref([]);
const selectedPlan = ref(null);
const history = ref([]);
const isPaymentModalVisible = ref(false);
const showCancelConfirmation = ref(false);
const loading = ref(false);
const error = ref(null);

onMounted(async () => {
  await fetchMembershipData();
});

const fetchMembershipData = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const [statusData, plansData, historyData] = await Promise.all([
      membershipAPI.getMembershipStatus(),
      membershipAPI.getMembershipPlans(),
      membershipAPI.getMembershipHistory()
    ]);
    
    membershipStatus.value = statusData;
    plans.value = plansData;
    history.value = historyData;
  } catch (err) {
    error.value = err.message;
    console.error('Failed to fetch membership data:', err);
  } finally {
    loading.value = false;
  }
};

const selectPlan = (plan) => {
  selectedPlan.value = plan;
};

const proceedToPayment = () => {
  if (selectedPlan.value) {
    isPaymentModalVisible.value = true;
  }
};

const closePaymentModal = () => {
  isPaymentModalVisible.value = false;
};

const handlePaymentSuccess = async () => {
  closePaymentModal();
  selectedPlan.value = null;
  await fetchMembershipData();
};

const cancelMembership = async () => {
  try {
    await membershipAPI.cancelMembership();
    showCancelConfirmation.value = false;
    await fetchMembershipData();
  } catch (err) {
    error.value = err.message;
    console.error('Failed to cancel membership:', err);
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const formatCurrency = (amount, currency = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
};
</script>

<style scoped>
.renewal-view {
  padding: 2rem 0;
  background-color: #f8f9fa;
  min-height: 100vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 2rem;
  text-align: center;
}

section {
  background-color: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 0.5rem;
}

/* Membership Status Styles */
.status-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #28a745;
}

.status-info {
  flex: 1;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.status-badge.active {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.expired {
  background-color: #f8d7da;
  color: #721c24;
}

.status-badge.inactive {
  background-color: #fff3cd;
  color: #856404;
}

.expiry-info p {
  margin: 0.25rem 0;
  color: #666;
}

.days-remaining {
  font-weight: 600;
  color: #28a745;
}

/* Membership Plans Styles */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.plan-card {
  position: relative;
  padding: 1.5rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.plan-card:hover {
  border-color: #007bff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.plan-card.selected {
  border-color: #007bff;
  background-color: #f8f9ff;
}

.plan-card.recommended {
  border-color: #28a745;
}

.recommended-badge {
  position: absolute;
  top: -10px;
  right: 20px;
  background-color: #28a745;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.plan-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
}

.plan-price {
  margin-bottom: 1.5rem;
}

.currency {
  font-size: 1rem;
  color: #666;
  vertical-align: super;
}

.amount {
  font-size: 2.5rem;
  font-weight: 700;
  color: #333;
}

.period {
  font-size: 1rem;
  color: #666;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem;
  text-align: left;
}

.plan-features li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
  color: #666;
}

.plan-features li:last-child {
  border-bottom: none;
}

/* Payment Section Styles */
.selected-plan-summary {
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.selected-plan-summary h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 1rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e9ecef;
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-item span:first-child {
  color: #666;
}

.summary-item span:last-child {
  font-weight: 600;
  color: #333;
}

/* History Section Styles */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.history-info h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
}

.history-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
}

/* Button Styles */
.btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  border: none;
  padding: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e9ecef;
}

/* Loading and Empty States */
.loading-placeholder {
  padding: 2rem;
  text-align: center;
}

.skeleton {
  height: 100px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}

/* Responsive Design */
@media (max-width: 768px) {
  .page-title {
    font-size: 2rem;
  }
  
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .status-card {
    flex-direction: column;
    text-align: center;
  }
  
  .status-actions {
    margin-top: 1rem;
  }
  
  .history-item {
    flex-direction: column;
    text-align: center;
  }
  
  .history-status {
    margin-top: 1rem;
  }
}
</style>