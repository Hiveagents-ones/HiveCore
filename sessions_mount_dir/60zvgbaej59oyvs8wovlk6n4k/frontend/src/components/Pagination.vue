<template>
  <div class="pagination">
    <button 
      @click="changePage(currentPage - 1)" 
      :disabled="currentPage <= 1"
      class="pagination-btn"
    >
      上一页
    </button>
    
    <div class="page-numbers">
      <button 
        v-for="page in visiblePages" 
        :key="page"
        @click="changePage(page)"
        :class="['page-number', { active: page === currentPage }]"
        :disabled="page === '...'"
      >
        {{ page }}
      </button>
    </div>
    
    <button 
      @click="changePage(currentPage + 1)" 
      :disabled="currentPage >= totalPages"
      class="pagination-btn"
    >
      下一页
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: {
    type: Number,
    required: true,
    default: 1
  },
  totalPages: {
    type: Number,
    required: true,
    default: 1
  }
})

const emit = defineEmits(['page-change'])

const visiblePages = computed(() => {
  const delta = 2
  const range = []
  const rangeWithDots = []
  let l

  for (let i = 1; i <= props.totalPages; i++) {
    if (i === 1 || i === props.totalPages || (i >= props.currentPage - delta && i <= props.currentPage + delta)) {
      range.push(i)
    }
  }

  range.forEach((i) => {
    if (l) {
      if (i - l === 2) {
        rangeWithDots.push(l + 1)
      } else if (i - l !== 1) {
        rangeWithDots.push('...')
      }
    }
    rangeWithDots.push(i)
    l = i
  })

  return rangeWithDots
})

const changePage = (page) => {
  if (page >= 1 && page <= props.totalPages) {
    emit('page-change', page)
  }
}
</script>

<style scoped>
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background-color: #f0f0f0;
  border-color: #999;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}


</style>

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:

.page-number {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.page-number:hover:not(:disabled) {
  background-color: #f0f0f0;
  border-color: #999;
}

.page-number.active {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

.page-number:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}