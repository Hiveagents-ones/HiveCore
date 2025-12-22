<template>
  <div class="config-item">
    <div class="config-item-header">
      <label class="config-label">{{ config.label }}</label>
      <span class="config-key">({{ config.key }})</span>
    </div>
    
    <div class="config-item-content">
      <!-- String input -->
      <el-input
        v-if="config.type === 'string'"
        v-model="localValue"
        :placeholder="config.placeholder || '请输入' + config.label"
        @change="handleValueChange"
      />
      
      <!-- Number input -->
      <el-input-number
        v-else-if="config.type === 'number'"
        v-model="localValue"
        :min="config.min"
        :max="config.max"
        :step="config.step || 1"
        @change="handleValueChange"
      />
      
      <!-- Boolean switch -->
      <el-switch
        v-else-if="config.type === 'boolean'"
        v-model="localValue"
        @change="handleValueChange"
      />
      
      <!-- Textarea -->
      <el-input
        v-else-if="config.type === 'text'"
        v-model="localValue"
        type="textarea"
        :rows="4"
        :placeholder="config.placeholder || '请输入' + config.label"
        @change="handleValueChange"
      />
      
      <!-- Select dropdown -->
      <el-select
        v-else-if="config.type === 'select'"
        v-model="localValue"
        :placeholder="'请选择' + config.label"
        @change="handleValueChange"
      >
        <el-option
          v-for="option in config.options"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      
      <!-- File upload for images -->
      <el-upload
        v-else-if="config.type === 'image'"
        class="image-uploader"
        :action="uploadUrl"
        :show-file-list="false"
        :on-success="handleImageSuccess"
        :before-upload="beforeImageUpload"
      >
        <img v-if="localValue" :src="localValue" class="uploaded-image" />
        <el-icon v-else class="image-uploader-icon"><Plus /></el-icon>
      </el-upload>
      
      <!-- JSON editor -->
      <el-input
        v-else-if="config.type === 'json'"
        v-model="jsonText"
        type="textarea"
        :rows="6"
        placeholder='请输入JSON格式数据，如: {"key": "value"}'
        @change="handleJsonChange"
      />
      
      <!-- Default input for unknown types -->
      <el-input
        v-else
        v-model="localValue"
        :placeholder="config.placeholder || '请输入' + config.label"
        @change="handleValueChange"
      />
    </div>
    
    <div v-if="config.description" class="config-description">
      {{ config.description }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  },
  modelValue: {
    type: [String, Number, Boolean, Object, Array],
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localValue = ref(props.modelValue)
const jsonText = ref('')

// For image upload
const uploadUrl = computed(() => {
  return '/api/upload/image'
})

// Initialize jsonText if config type is json
if (props.config.type === 'json' && props.modelValue) {
  jsonText.value = typeof props.modelValue === 'string' 
    ? props.modelValue 
    : JSON.stringify(props.modelValue, null, 2)
}

// Watch for external value changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== localValue.value) {
    localValue.value = newValue
    
    if (props.config.type === 'json') {
      jsonText.value = typeof newValue === 'string' 
        ? newValue 
        : JSON.stringify(newValue, null, 2)
    }
  }
})

const handleValueChange = (value) => {
  emit('update:modelValue', value)
  emit('change', {
    key: props.config.key,
    value: value
  })
}

const handleJsonChange = (value) => {
  try {
    const parsedValue = JSON.parse(value)
    localValue.value = parsedValue
    emit('update:modelValue', parsedValue)
    emit('change', {
      key: props.config.key,
      value: parsedValue
    })
  } catch (error) {
    ElMessage.error('JSON格式不正确，请检查输入')
  }
}

const handleImageSuccess = (response) => {
  if (response.code === 0 && response.data && response.data.url) {
    localValue.value = response.data.url
    emit('update:modelValue', response.data.url)
    emit('change', {
      key: props.config.key,
      value: response.data.url
    })
    ElMessage.success('图片上传成功')
  } else {
    ElMessage.error('图片上传失败')
  }
}

const beforeImageUpload = (file) => {
  const isJPG = file.type === 'image/jpeg' || file.type === 'image/png'
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isJPG) {
    ElMessage.error('上传图片只能是 JPG/PNG 格式!')
  }
  if (!isLt2M) {
    ElMessage.error('上传图片大小不能超过 2MB!')
  }
  return isJPG && isLt2M
}
</script>

<style scoped>
.config-item {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fff;
}

.config-item-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.config-label {
  font-weight: 500;
  color: #303133;
  margin-right: 8px;
}

.config-key {
  font-size: 12px;
  color: #909399;
}

.config-item-content {
  margin-bottom: 10px;
}

.config-description {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.image-uploader {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  width: 178px;
  height: 178px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-uploader:hover {
  border-color: #409EFF;
}

.image-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 178px;
  height: 178px;
  text-align: center;
  line-height: 178px;
}

.uploaded-image {
  width: 178px;
  height: 178px;
  object-fit: cover;
  display: block;
}
</style>