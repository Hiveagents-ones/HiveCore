<template>
  <div class="avatar-upload">
    <div class="avatar-preview" @click="triggerFileInput">
      <img v-if="imageUrl" :src="imageUrl" alt="Avatar" />
      <div v-else class="avatar-placeholder">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        <span>Upload Avatar</span>
      </div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      @change="handleFileChange"
      style="display: none"
    />
    <div v-if="uploading" class="upload-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <span>{{ uploadProgress }}%</span>
    </div>
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'upload-success', 'upload-error'])

const userStore = useUserStore()
const fileInput = ref(null)
const imageUrl = ref(props.modelValue)
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref('')

watch(() => props.modelValue, (newValue) => {
  imageUrl.value = newValue
})

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileChange = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  // Validate file type
  if (!file.type.startsWith('image/')) {
    error.value = 'Please select an image file'
    return
  }

  // Validate file size (max 5MB)
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Image size should not exceed 5MB'
    return
  }

  error.value = ''
  uploading.value = true
  uploadProgress.value = 0

  try {
    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      imageUrl.value = e.target.result
    }
    reader.readAsDataURL(file)

    // Upload file
    const formData = new FormData()
    formData.append('avatar', file)

    // Simulate upload progress
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    const response = await userStore.uploadAvatar(formData)
    
    clearInterval(progressInterval)
    uploadProgress.value = 100
    
    // Update model value with the new URL
    emit('update:modelValue', response.avatar_url)
    emit('upload-success', response.avatar_url)
    
    // Reset file input
    event.target.value = ''
  } catch (err) {
    error.value = err.message || 'Failed to upload avatar'
    emit('upload-error', err)
    // Reset to previous image on error
    imageUrl.value = props.modelValue
  } finally {
    uploading.value = false
    setTimeout(() => {
      uploadProgress.value = 0
    }, 1000)
  }
}
</script>

<style scoped>
.avatar-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.avatar-preview {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 2px dashed #ccc;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
}

.avatar-preview:hover {
  border-color: #4a90e2;
  transform: scale(1.05);
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  padding: 1rem;
  text-align: center;
}

.avatar-placeholder svg {
  margin-bottom: 0.5rem;
}

.avatar-placeholder span {
  font-size: 0.875rem;
}

.upload-progress {
  width: 100%;
  max-width: 200px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #4a90e2;
  transition: width 0.3s ease;
}

.upload-progress span {
  font-size: 0.875rem;
  color: #666;
  min-width: 40px;
}

.error-message {
  color: #e74c3c;
  font-size: 0.875rem;
  text-align: center;
}
</style>