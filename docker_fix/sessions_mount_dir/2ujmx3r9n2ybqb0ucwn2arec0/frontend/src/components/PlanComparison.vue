<template>
  <div class="plan-comparison">
    <h2 class="comparison-title">{{ $t('planComparison.title') }}</h2>
    
    <div class="plans-container">
      <div 
        v-for="plan in plans" 
        :key="plan.id"
        class="plan-card"
        :class="{ 'selected': selectedPlan?.id === plan.id, 'recommended': plan.recommended }"
        @click="selectPlan(plan)"
      >
        <div v-if="plan.recommended" class="recommended-badge">
          {{ $t('planComparison.recommended') }}
        </div>
        
        <h3 class="plan-name">{{ plan.name }}</h3>
        <div class="plan-price">
          <span class="currency">{{ plan.currency }}</span>
          <span class="amount">{{ plan.price }}</span>
          <span class="period">/{{ plan.billingPeriod }}</span>
        </div>
        
        <ul class="plan-features">
          <li 
            v-for="feature in plan.features" 
            :key="feature.id"
            class="feature-item"
          >
            <i class="feature-icon" :class="feature.included ? 'included' : 'excluded'">
              {{ feature.included ? '✓' : '✗' }}
            </i>
            <span>{{ feature.name }}</span>
          </li>
        </ul>
        
        <button 
          class="select-button"
          :class="{ 'selected': selectedPlan?.id === plan.id }"
        >
          {{ selectedPlan?.id === plan.id ? $t('planComparison.selected') : $t('planComparison.select') }}
        </button>
      </div>
    </div>
    
    <div v-if="selectedPlan" class="selected-plan-info">
      <h3>{{ $t('planComparison.selectedPlan') }}</h3>
      <p>{{ selectedPlan.name }} - {{ selectedPlan.currency }}{{ selectedPlan.price }}/{{ selectedPlan.billingPeriod }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  plans: {
    type: Array,
    required: true,
    default: () => []
  },
  currentPlanId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['plan-selected'])

const selectedPlan = ref(null)

const selectPlan = (plan) => {
  selectedPlan.value = plan
  emit('plan-selected', plan)
}
</script>

<style scoped>
.plan-comparison {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.comparison-title {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 2rem;
  color: #2c3e50;
}

.plans-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.plan-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  position: relative;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
}

.plan-card.selected {
  border: 2px solid #42b983;
  box-shadow: 0 0 0 4px rgba(66, 185, 131, 0.2);
}

.plan-card.recommended {
  border: 2px solid #ff9800;
}

.recommended-badge {
  position: absolute;
  top: -12px;
  right: 20px;
  background: #ff9800;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: bold;
}

.plan-name {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #2c3e50;
}

.plan-price {
  margin-bottom: 1.5rem;
}

.currency {
  font-size: 1.2rem;
  color: #7f8c8d;
}

.amount {
  font-size: 2.5rem;
  font-weight: bold;
  color: #2c3e50;
}

.period {
  color: #7f8c8d;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin-bottom: 2rem;
}

.feature-item {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
  color: #34495e;
}

.feature-icon {
  margin-right: 0.75rem;
  font-weight: bold;
}

.feature-icon.included {
  color: #42b983;
}

.feature-icon.excluded {
  color: #e74c3c;
}

.select-button {
  width: 100%;
  padding: 0.75rem;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s ease;
}

.select-button:hover {
  background: #3aa876;
}

.select-button.selected {
  background: #2c3e50;
}

.selected-plan-info {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
}

.selected-plan-info h3 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.selected-plan-info p {
  color: #7f8c8d;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .plans-container {
    grid-template-columns: 1fr;
  }
  
  .comparison-title {
    font-size: 1.5rem;
  }
}
</style>