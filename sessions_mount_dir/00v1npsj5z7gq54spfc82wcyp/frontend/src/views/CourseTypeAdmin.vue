<template>
  <v-container>
    <v-row class="mb-4">
      <v-col cols="12">
        <h1 class="text-h4">课程类型管理</h1>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>添加新课程类型</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="addCourseType">
              <v-text-field
            <v-switch
              v-model="editedItem.is_active"
              label="启用状态"
              class="mb-4"
            ></v-switch>
                v-model="newCourseType.name"
                label="课程类型名称"
                required
                outlined
                class="mb-4"
              ></v-text-field>
              <v-text-field
                v-model="newCourseType.description"
                label="课程描述"
                outlined
                class="mb-4"
              ></v-text-field>
              <v-btn
                type="submit"
                color="primary"
                :loading="isAdding"
              >
                添加
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>课程类型列表</v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="courseTypes"
              :sort-by="[{ key: 'is_active', order: 'desc' }, { key: 'name', order: 'asc' }]"
              :loading="isLoading"
              class="elevation-1"
            >
              <template v-slot:item.actions="{ item }">
              <v-icon
                small
                class="mr-2"
                :color="item.is_active ? 'success' : 'grey'"
                @click="toggleActive(item)"
              >
                {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
              </v-icon>
                <v-icon
                  small
                  class="mr-2"
                  @click="editItem(item)"
                >
                  mdi-pencil
                </v-icon>
                <v-icon
                  small
                  @click="deleteItem(item)"
                >
                  mdi-delete
                </v-icon>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="editDialog" max-width="500px">
      <v-card>
        <v-card-title>编辑课程类型</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEdit">
            <v-text-field
              v-model="editedItem.name"
              label="课程类型名称"
              required
              outlined
              class="mb-4"
            ></v-text-field>
            <v-text-field
              v-model="editedItem.description"
              label="课程描述"
              outlined
              class="mb-4"
            ></v-text-field>
            <v-btn
              type="submit"
              color="primary"
              :loading="isSaving"
            >
              保存
            </v-btn>
            <v-btn
              text
              @click="editDialog = false"
              class="ml-2"
            >
              取消
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="500px">
      <v-card>
        <v-card-title>确认删除</v-card-title>
        <v-card-text>
          确定要删除这个课程类型吗？
        </v-card-text>
        <v-card-actions>
          <v-btn color="error" @click="confirmDelete" :loading="isDeleting">
,
      toggleActive
            删除
          </v-btn>
          <v-btn text @click="deleteDialog = false">取消</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useSnackbar } from '@/composables/snackbar';
import { fetchCourseTypes, createCourseType, updateCourseType, deleteCourseType } from '@/api/courseTypes';

export default {
  name: 'CourseTypeAdmin',
  setup() {
    const { showSnackbar } = useSnackbar();
    
    const courseTypes = ref([]);
    const isLoading = ref(false);
    const isAdding = ref(false);
    const isSaving = ref(false);
    const isDeleting = ref(false);
    
    const newCourseType = ref({
      name: '',
      description: ''
,
      is_active: true
,
      is_active: true
    });
    
    const editedItem = ref({
      id: null,
      name: '',
      description: ''
    });
    
    const editDialog = ref(false);
    const deleteDialog = ref(false);
    const itemToDelete = ref(null);
    
    const headers = [
      { text: '状态', value: 'is_active', sortable: true },
      { text: 'ID', value: 'id' },
      { text: '课程类型名称', value: 'name' },
      { text: '描述', value: 'description' },
      { text: '操作', value: 'actions', sortable: false }
    ];
    
    const loadCourseTypes = async () => {
      try {
        isLoading.value = true;
        const response = await fetchCourseTypes();
        courseTypes.value = response.data;
      } catch (error) {
        showSnackbar('加载课程类型失败: ' + error.message, 'error');
      } finally {
        isLoading.value = false;
      }
    };
    
    const addCourseType = async () => {
  if (!newCourseType.value.is_active) {
    newCourseType.value.is_active = true;
  }
      try {
        isAdding.value = true;
        await createCourseType(newCourseType.value);
        showSnackbar('课程类型添加成功', 'success');
        newCourseType.value = { name: '', description: '' };
        await loadCourseTypes();
      } catch (error) {
        showSnackbar('添加课程类型失败: ' + error.message, 'error');
      } finally {
        isAdding.value = false;
      }
    };
    
    const editItem = (item) => {
  editedItem.value.is_active = item.is_active;
      editedItem.value = { ...item };
      editDialog.value = true;
    };
    
    const saveEdit = async () => {
      try {
        isSaving.value = true;
        await updateCourseType(editedItem.value.id, editedItem.value);
        showSnackbar('课程类型更新成功', 'success');
        editDialog.value = false;
        await loadCourseTypes();
      } catch (error) {
        showSnackbar('更新课程类型失败: ' + error.message, 'error');
      } finally {
        isSaving.value = false;
      }
    };
    
    const deleteItem = (item) => {
      itemToDelete.value = item.id;
      deleteDialog.value = true;
    };
    
    const confirmDelete = async () => {
    const toggleActive = async (item) => {
      try {
        const updatedItem = { ...item, is_active: !item.is_active };
        await updateCourseType(item.id, updatedItem);
        showSnackbar(`课程类型已${updatedItem.is_active ? '启用' : '禁用'}`, 'success');
        await loadCourseTypes();
      } catch (error) {
        showSnackbar('状态切换失败: ' + error.message, 'error');
      }
    };
      try {
        isDeleting.value = true;
        await deleteCourseType(itemToDelete.value);
        showSnackbar('课程类型删除成功', 'success');
        deleteDialog.value = false;
        await loadCourseTypes();
      } catch (error) {
        showSnackbar('删除课程类型失败: ' + error.message, 'error');
      } finally {
        isDeleting.value = false;
      }
    };
    
    onMounted(() => {
      loadCourseTypes();
    });
    
    return {
      courseTypes,
      isLoading,
      isAdding,
      isSaving,
      isDeleting,
      newCourseType,
      editedItem,
      editDialog,
      deleteDialog,
      headers,
      addCourseType,
      editItem,
      saveEdit,
      deleteItem,
      confirmDelete
    };
  }
};
</script>

<style scoped>
.v-card {
  margin-bottom: 20px;
}
</style>