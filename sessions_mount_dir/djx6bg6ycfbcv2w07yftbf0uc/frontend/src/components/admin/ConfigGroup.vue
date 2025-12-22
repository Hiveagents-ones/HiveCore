<template>
  <div class="config-group">
    <div class="group-header" @click="toggleCollapse">
      <h3 class="group-title">
        <i :class="['collapse-icon', isCollapsed ? 'el-icon-arrow-right' : 'el-icon-arrow-down']"></i>
        {{ title }}
      </h3>
      <span class="group-count">({{ items.length }})</span>
    </div>
    
    <el-collapse-transition>
      <div v-show="!isCollapsed" class="group-content">
        <div class="config-items">
          <div 
            v-for="item in items" 
            :key="item.key" 
            class="config-item"
          >
            <div class="item-label">
              <span>{{ item.label }}</span>
              <el-tooltip 
                v-if="item.description" 
                :content="item.description" 
                placement="top"
              >
                <i class="el-icon-question"></i>
              </el-tooltip>
            </div>
            
            <div class="item-control">
              <!-- 文本输入 -->
              <el-input
                v-if="item.type === 'text'"
                v-model="item.value"
                :placeholder="item.placeholder"
                @change="handleValueChange(item)"
              />
              
              <!-- 数字输入 -->
              <el-input-number
                v-else-if="item.type === 'number'"
                v-model="item.value"
                :min="item.min"
                :max="item.max"
                :step="item.step || 1"
                @change="handleValueChange(item)"
              />
              
              <!-- 开关 -->
              <el-switch
                v-else-if="item.type === 'boolean'"
                v-model="item.value"
                @change="handleValueChange(item)"
              />
              
              <!-- 选择器 -->
              <el-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :placeholder="item.placeholder"
                @change="handleValueChange(item)"
              >
                <el-option
                  v-for="option in item.options"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              
              <!-- 文本域 -->
              <el-input
                v-else-if="item.type === 'textarea'"
                v-model="item.value"
                type="textarea"
                :rows="3"
                :placeholder="item.placeholder"
                @change="handleValueChange(item)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-collapse-transition>
  </div>
</template>

<script>
export default {
  name: 'ConfigGroup',
  
  props: {
    title: {
      type: String,
      required: true
    },
    items: {
      type: Array,
      required: true,
      default: () => []
    },
    defaultCollapsed: {
      type: Boolean,
      default: false
    }
  },
  
  data() {
    return {
      isCollapsed: this.defaultCollapsed
    }
  },
  
  methods: {
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed
    },
    
    handleValueChange(item) {
      this.$emit('item-change', {
        key: item.key,
        value: item.value,
        type: item.type
      })
    }
  }
}
</script>

<style scoped>
.config-group {
  margin-bottom: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fff;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: #f5f7fa;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.3s;
}

.group-header:hover {
  background-color: #e6e8eb;
}

.group-title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  display: flex;
  align-items: center;
}

.collapse-icon {
  margin-right: 8px;
  transition: transform 0.3s;
}

.group-count {
  color: #909399;
  font-size: 14px;
}

.group-content {
  padding: 16px;
}

.config-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.item-label {
  flex: 0 0 200px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
  padding-top: 8px;
}

.item-label .el-icon-question {
  color: #c0c4cc;
  cursor: help;
}

.item-control {
  flex: 1;
  min-width: 0;
}

.item-control .el-input,
.item-control .el-input-number,
.item-control .el-select,
.item-control .el-switch {
  width: 100%;
}

@media (max-width: 768px) {
  .config-item {
    flex-direction: column;
  }
  
  .item-label {
    flex: none;
    padding-top: 0;
  }
  
  .item-control {
    width: 100%;
  }
}
</style>