<template>
  <div class="profile-view">
    <div class="profile-container">
      <h2>个人中心</h2>
      
      <div class="profile-section">
        <div class="avatar-section">
          <div class="avatar-container">
            <img :src="profile.avatar || '/default-avatar.png'" alt="头像" class="avatar">
            <button @click="showAvatarUpload = true" class="avatar-edit-btn">
              <i class="fas fa-camera"></i>
            </button>
          </div>
        </div>
        
        <form @submit.prevent="handleSubmit" class="profile-form">
          <div class="form-group">
            <label for="nickname">昵称</label>
            <input 
              type="text" 
              id="nickname" 
              v-model="profile.nickname" 
              :disabled="!isEditing"
              class="form-input"
            >
          </div>
          
          <div class="form-group">
            <label for="email">邮箱</label>
            <input 
              type="email" 
              id="email" 
              v-model="profile.email" 
              :disabled="!isEditing"
              class="form-input"
            >
          </div>
          
          <div class="form-group">
            <label for="phone">手机号</label>
            <input 
              type="tel" 
              id="phone" 
              v-model="profile.phone" 
              :disabled="!isEditing"
              class="form-input"
            >
          </div>
          
          <div class="form-group">
            <label for="bio">个人简介</label>
            <textarea 
              id="bio" 
              v-model="profile.bio" 
              :disabled="!isEditing"
              class="form-textarea"
              rows="4"
            ></textarea>
          </div>
          
          <div class="form-actions">
            <button 
              v-if="!isEditing" 
              @click="isEditing = true" 
              type="button" 
              class="btn btn-primary"
            >
              编辑资料
            </button>
            <template v-else>
              <button type="submit" class="btn btn-success">保存</button>
              <button @click="cancelEdit" type="button" class="btn btn-secondary">取消</button>
            </template>
          </div>
        </form>
      </div>
      
      <!-- 头像上传模态框 -->
      <div v-if="showAvatarUpload" class="modal-overlay" @click="showAvatarUpload = false">
        <div class="modal-content" @click.stop>
          <h3>更换头像</h3>
          <input 
            type="file" 
            ref="avatarInput" 
            @change="handleAvatarChange" 
            accept="image/*"
            class="hidden"
          >
          <div class="avatar-upload-area" @click="$refs.avatarInput.click()">
            <i class="fas fa-cloud-upload-alt"></i>
            <p>点击上传新头像</p>
          </div>
          <div class="modal-actions">
            <button @click="showAvatarUpload = false" class="btn btn-secondary">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const isEditing = ref(false)
const showAvatarUpload = ref(false)
const avatarInput = ref(null)

const profile = reactive({
  nickname: '',
  email: '',
  phone: '',
  bio: '',
  avatar: ''
})

const originalProfile = reactive({})

onMounted(async () => {
  await fetchProfile()
})

const fetchProfile = async () => {
  try {
    const response = await userStore.getProfile()
    Object.assign(profile, response)
    Object.assign(originalProfile, response)
  } catch (error) {
    ElMessage.error('获取个人信息失败')
  }
}

const handleSubmit = async () => {
  try {
    await userStore.updateProfile(profile)
    Object.assign(originalProfile, profile)
    isEditing.value = false
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const cancelEdit = () => {
  Object.assign(profile, originalProfile)
  isEditing.value = false
}

const handleAvatarChange = async (event) => {
  const file = event.target.files[0]
  if (file) {
    try {
      const formData = new FormData()
      formData.append('avatar', file)
      
      const response = await userStore.uploadAvatar(formData)
      profile.avatar = response.url
      showAvatarUpload.value = false
      ElMessage.success('头像上传成功')
    } catch (error) {
      ElMessage.error('头像上传失败')
    }
  }
}
</script>

<style scoped>
.profile-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.profile-container {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-bottom: 30px;
  color: #333;
  text-align: center;
}

.profile-section {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.avatar-section {
  display: flex;
  justify-content: center;
}

.avatar-container {
  position: relative;
  width: 120px;
  height: 120px;
}

.avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #f0f0f0;
}

.avatar-edit-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #409eff;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.avatar-edit-btn:hover {
  background: #66b1ff;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 500;
  color: #606266;
}

.form-input,
.form-textarea {
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #409eff;
}

.form-input:disabled,
.form-textarea:disabled {
  background-color: #f5f7fa;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary {
  background: #409eff;
  color: white;
}

.btn-primary:hover {
  background: #66b1ff;
}

.btn-success {
  background: #67c23a;
  color: white;
}

.btn-success:hover {
  background: #85ce61;
}

.btn-secondary {
  background: #909399;
  color: white;
}

.btn-secondary:hover {
  background: #a6a9ad;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 30px;
  width: 90%;
  max-width: 400px;
}

.modal-content h3 {
  margin-bottom: 20px;
  color: #333;
}

.avatar-upload-area {
  border: 2px dashed #dcdfe6;
  border-radius: 4px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s;
}

.avatar-upload-area:hover {
  border-color: #409eff;
}

.avatar-upload-area i {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 10px;
}

.avatar-upload-area p {
  color: #606266;
  margin: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.hidden {
  display: none;
}

@media (max-width: 768px) {
  .profile-view {
    padding: 10px;
  }
  
  .profile-container {
    padding: 20px;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>