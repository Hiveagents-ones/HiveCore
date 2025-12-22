<template>
  <div class="virtual-scroll-container" ref="containerRef" @scroll="handleScroll">
    <div class="virtual-scroll-phantom" :style="{ height: `${totalHeight}px` }"></div>
    <div class="virtual-scroll-content" :style="{ transform: `translateY(${offsetY}px)` }">
      <div
        v-for="(item, index) in visibleItems"
        :key="getItemKey(item, startIndex + index)"
        class="virtual-scroll-item"
        :style="{ height: `${itemHeight}px` }"
      >
        <slot :item="item" :index="startIndex + index"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    required: true
  },
  itemHeight: {
    type: Number,
    default: 50
  },
  containerHeight: {
    type: Number,
    default: 400
  },
  keyField: {
    type: String,
    default: 'id'
  },
  buffer: {
    type: Number,
    default: 5
  }
})

const emit = defineEmits(['scroll'])

const containerRef = ref(null)
const scrollTop = ref(0)
const containerHeight = ref(props.containerHeight)
const isScrolling = ref(false)
let scrollTimer = null

const totalHeight = computed(() => props.items.length * props.itemHeight)

const startIndex = computed(() => {
  return Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.buffer)
})

const endIndex = computed(() => {
  const visibleCount = Math.ceil(containerHeight.value / props.itemHeight)
  return Math.min(
    props.items.length - 1,
    startIndex.value + visibleCount + props.buffer * 2
  )
})

const visibleItems = computed(() => {
  return props.items.slice(startIndex.value, endIndex.value + 1)
})

const offsetY = computed(() => {
  return startIndex.value * props.itemHeight
})

const getItemKey = (item, index) => {
  return item[props.keyField] || index
}

const handleScroll = (e) => {
  scrollTop.value = e.target.scrollTop
  isScrolling.value = true
  
  clearTimeout(scrollTimer)
  scrollTimer = setTimeout(() => {
    isScrolling.value = false
  }, 150)
  
  emit('scroll', e)
}

const updateContainerHeight = () => {
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight
  }
}

const resizeObserver = new ResizeObserver(updateContainerHeight)

onMounted(() => {
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  resizeObserver.disconnect()
})

watch(() => props.containerHeight, (newHeight) => {
  containerHeight.value = newHeight
})

watch(() => props.items, () => {
  if (containerRef.value) {
    scrollTop.value = 0
    containerRef.value.scrollTop = 0
  }
}, { deep: true })
</script>

<style scoped>
.virtual-scroll-container {
  height: 100%;
  overflow-y: auto;
  position: relative;
}

.virtual-scroll-phantom {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  z-index: -1;
}

.virtual-scroll-content {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
}

.virtual-scroll-item {

  transition: opacity 0.15s ease-in-out;
  box-sizing: border-box;
}
</style>