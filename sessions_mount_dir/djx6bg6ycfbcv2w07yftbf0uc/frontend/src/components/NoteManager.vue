<template>
  <div class="note-manager">
    <div class="note-header">
      <h3>备注管理</h3>
      <button @click="showHistory = !showHistory" class="history-btn">
        {{ showHistory ? '隐藏历史记录' : '查看历史记录' }}
      </button>
    </div>
    
    <div class="note-editor">
      <textarea
        v-model="currentNote"
        placeholder="请输入备注内容..."
        rows="4"
        class="note-textarea"
      ></textarea>
      <div class="note-actions">
        <button @click="saveNote" class="save-btn" :disabled="!hasChanges">
          保存备注
        </button>
        <button @click="cancelEdit" class="cancel-btn" v-if="hasChanges">
          取消
        </button>
      </div>
    </div>

    <div v-if="showHistory" class="note-history">
      <h4>历史记录</h4>
      <div v-if="history.length === 0" class="no-history">
        暂无历史记录
      </div>
      <div v-else class="history-list">
        <div
          v-for="(item, index) in history"
          :key="index"
          class="history-item"
        >
          <div class="history-content">{{ item.content }}</div>
          <div class="history-meta">
            <span class="history-time">{{ formatTime(item.created_at) }}</span>
            <span class="history-author">{{ item.author }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useMemberStore } from '@/stores/member'

const props = defineProps({
  memberId: {
    type: [String, Number],
    required: true
  },
  initialNote: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['note-updated'])

const memberStore = useMemberStore()
const currentNote = ref(props.initialNote)
const originalNote = ref(props.initialNote)
const showHistory = ref(false)
const history = ref([])

const hasChanges = computed(() => {
  return currentNote.value !== originalNote.value
})

const saveNote = async () => {
  try {
    await memberStore.updateMemberNote(props.memberId, currentNote.value)
    originalNote.value = currentNote.value
    emit('note-updated', currentNote.value)
    await fetchHistory()
  } catch (error) {
    console.error('保存备注失败:', error)
  }
}

const cancelEdit = () => {
  currentNote.value = originalNote.value
}

const fetchHistory = async () => {
  try {
    const response = await memberStore.getMemberNoteHistory(props.memberId)
    history.value = response.data || []
  } catch (error) {
    console.error('获取历史记录失败:', error)
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

watch(() => props.initialNote, (newVal) => {
  currentNote.value = newVal
  originalNote.value = newVal
})

watch(showHistory, (newVal) => {
  if (newVal) {
    fetchHistory()
  }
})
</script>

<style scoped>
.note-manager {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.note-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.note-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.history-btn {
  padding: 6px 12px;
  background: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
}

.history-btn:hover {
  background: #e0e0e0;
}

.note-editor {
  margin-bottom: 16px;
}

.note-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
}

.note-textarea:focus {
  outline: none;
  border-color: #409eff;
}

.note-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.save-btn, .cancel-btn {
  padding: 6px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.save-btn {
  background: #409eff;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #66b1ff;
}

.save-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.cancel-btn {
  background: #f0f0f0;
  color: #666;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

.note-history {
  border-top: 1px solid #eee;
  padding-top: 16px;
}

.note-history h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #666;
}

.no-history {
  color: #999;
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

.history-list {
  max-height: 300px;
  overflow-y: auto;
}

.history-item {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.history-item:last-child {
  border-bottom: none;
}

.history-content {
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

.history-time {
  color: #666;
}

.history-author {
  color: #999;
}
</style>