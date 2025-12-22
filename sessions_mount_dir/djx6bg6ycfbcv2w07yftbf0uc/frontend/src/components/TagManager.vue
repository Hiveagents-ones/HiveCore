<template>
  <div class="tag-manager">
    <div class="tag-header">
      <h3>标签管理</h3>
      <div class="tag-actions">
        <input
          v-model="newTag"
          placeholder="输入新标签"
          @keyup.enter="addTag"
          class="tag-input"
        />
        <button @click="addTag" class="btn btn-primary">添加标签</button>
      </div>
    </div>

    <div class="tag-list">
      <div v-if="tags.length === 0" class="empty-state">
        暂无标签，请添加新标签
      </div>
      <div v-else>
        <div class="batch-actions" v-if="selectedTags.length > 0">
          <span>已选择 {{ selectedTags.length }} 个标签</span>
          <button @click="deleteSelectedTags" class="btn btn-danger">
            批量删除
          </button>
        </div>
        <div class="tag-grid">
          <div
            v-for="tag in tags"
            :key="tag.id"
            class="tag-item"
            :class="{ selected: selectedTags.includes(tag.id) }"
          >
            <input
              type="checkbox"
              :value="tag.id"
              v-model="selectedTags"
              class="tag-checkbox"
            />
            <span class="tag-name">{{ tag.name }}</span>
            <button @click="deleteTag(tag.id)" class="btn btn-icon btn-danger">
              ×
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import axios from 'axios';

export default {
  name: 'TagManager',
  props: {
    memberId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const tags = ref([]);
    const selectedTags = ref([]);
    const newTag = ref('');

    const fetchTags = async () => {
      try {
        const response = await axios.get(`/api/members/${props.memberId}/tags`);
        tags.value = response.data;
      } catch (error) {
        console.error('获取标签失败:', error);
      }
    };

    const addTag = async () => {
      if (!newTag.value.trim()) return;

      try {
        const response = await axios.post(`/api/members/${props.memberId}/tags`, {
          name: newTag.value,
        });
        tags.value.push(response.data);
        newTag.value = '';
      } catch (error) {
        console.error('添加标签失败:', error);
      }
    };

    const deleteTag = async (tagId) => {
      try {
        await axios.delete(`/api/members/${props.memberId}/tags/${tagId}`);
        tags.value = tags.value.filter((tag) => tag.id !== tagId);
        selectedTags.value = selectedTags.value.filter((id) => id !== tagId);
      } catch (error) {
        console.error('删除标签失败:', error);
      }
    };

    const deleteSelectedTags = async () => {
      try {
        await Promise.all(
          selectedTags.value.map((tagId) =>
            axios.delete(`/api/members/${props.memberId}/tags/${tagId}`)
          )
        );
        tags.value = tags.value.filter(
          (tag) => !selectedTags.value.includes(tag.id)
        );
        selectedTags.value = [];
      } catch (error) {
        console.error('批量删除标签失败:', error);
      }
    };

    onMounted(fetchTags);

    return {
      tags,
      selectedTags,
      newTag,
      addTag,
      deleteTag,
      deleteSelectedTags,
    };
  },
};
</script>

<style scoped>
.tag-manager {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.tag-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tag-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.tag-actions {
  display: flex;
  gap: 10px;
}

.tag-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.btn-icon {
  padding: 4px 8px;
  font-size: 16px;
  line-height: 1;
}

.tag-list {
  min-height: 100px;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 20px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.tag-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.tag-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.tag-item.selected {
  background-color: #e9ecef;
}

.tag-checkbox {
  margin-right: 10px;
}

.tag-name {
  flex: 1;
  font-size: 14px;
  color: #333;
}
</style>