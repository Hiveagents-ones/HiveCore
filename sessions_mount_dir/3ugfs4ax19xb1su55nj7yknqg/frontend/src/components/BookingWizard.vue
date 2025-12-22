<template>
  <div class="booking-wizard">
    <div class="wizard-header">
      <h2>课程预约</h2>
    </div>
    
    <div class="wizard-steps">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        :class="['step', { 'active': currentStep === index, 'completed': currentStep > index }]"
        @click="goToStep(index)"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-title">{{ step.title }}</div>
      </div>
    </div>
    
    <div class="wizard-content">
      <component 
        :is="steps[currentStep].component" 
        @next="nextStep"
        @prev="prevStep"
        @complete="handleComplete"
      />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import Step1CourseSelection from './steps/Step1CourseSelection.vue';
import Step2TimeSelection from './steps/Step2TimeSelection.vue';
import Step3Confirmation from './steps/Step3Confirmation.vue';

export default {
  name: 'BookingWizard',
  components: {
    Step1CourseSelection,
    Step2TimeSelection,
    Step3Confirmation
  },
  setup() {
    const currentStep = ref(0);
    
    const steps = [
      { title: '选择课程', component: 'Step1CourseSelection' },
      { title: '选择时间', component: 'Step2TimeSelection' },
      { title: '确认预约', component: 'Step3Confirmation' }
    ];
    
    const nextStep = () => {
      if (currentStep.value < steps.length - 1) {
        currentStep.value++;
      }
    };
    
    const prevStep = () => {
      if (currentStep.value > 0) {
        currentStep.value--;
      }
    };
    
    const goToStep = (index) => {
      if (index < currentStep.value) {
        currentStep.value = index;
      }
    };
    
    const handleComplete = () => {
      // Handle booking completion
      console.log('Booking completed!');
      // Could emit an event to parent or redirect
    };
    
    return {
      currentStep,
      steps,
      nextStep,
      prevStep,
      goToStep,
      handleComplete
    };
  }
};
</script>

<style scoped>
.booking-wizard {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.wizard-header {
  text-align: center;
  margin-bottom: 30px;
}

.wizard-header h2 {
  color: #333;
  font-size: 24px;
}

.wizard-steps {
  display: flex;
  justify-content: space-between;
  margin-bottom: 30px;
  position: relative;
}

.wizard-steps::before {
  content: '';
  position: absolute;
  top: 15px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #e0e0e0;
  z-index: 1;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  cursor: pointer;
  flex: 1;
}

.step:not(:last-child) {
  margin-right: 10px;
}

.step-number {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: #e0e0e0;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 5px;
  transition: all 0.3s ease;
}

.step.active .step-number {
  background-color: #42b983;
  color: white;
}

.step.completed .step-number {
  background-color: #42b983;
  color: white;
}

.step-title {
  font-size: 14px;
  color: #999;
  text-align: center;
  transition: all 0.3s ease;
}

.step.active .step-title,
.step.completed .step-title {
  color: #333;
  font-weight: bold;
}

.wizard-content {
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  min-height: 300px;
}
</style>