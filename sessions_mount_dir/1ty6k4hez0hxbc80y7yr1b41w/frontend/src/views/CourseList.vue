<template>
  <div class="course-list-container">
    <h1>{{ t('courseList.title') }}</h1>
    
    <div class="course-list-header">
      <LanguageSwitcher />
      <el-button type="primary" @click="showCreateDialog = true">
        {{ t('courseList.addCourse') }}
      </el-button>
    </div>
    
    <el-table :data="courses" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" :label="t('courseList.tableHeaders.id')" width="80" />
      <el-table-column prop="name" :label="t('courseList.tableHeaders.name')" />
      <el-table-column prop="schedule" :label="t('courseList.tableHeaders.schedule')" />
      <el-table-column prop="coach_id" :label="t('courseList.tableHeaders.coachId')" width="100" />
      <el-table-column prop="max_members" :label="t('courseList.tableHeaders.maxMembers')" width="100" />
      <el-table-column :label="t('courseList.tableHeaders.actions')" width="180">
        <template #default="scope">
          <el-button size="small" @click="viewCourseDetails(scope.row.id)">
            {{ t('courseList.details') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建课程对话框 -->
    <el-dialog v-model="showCreateDialog" :title="t('courseList.createDialog.title')" width="30%">
      <el-form :model="newCourse" label-width="100px">
        <el-form-item :label="t('courseList.createDialog.nameLabel')" required>
          <el-input v-model="newCourse.name" />
        </el-form-item>
        <el-form-item :label="t('courseList.createDialog.scheduleLabel')" required>
          <el-input v-model="newCourse.schedule" />
        </el-form-item>
        <el-form-item :label="t('courseList.createDialog.coachIdLabel')" required>
          <el-input v-model.number="newCourse.coach_id" type="number" />
        </el-form-item>
        <el-form-item :label="t('courseList.createDialog.maxMembersLabel')" required>
          <el-input v-model.number="newCourse.max_members" type="number" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleCreateCourse">
          {{ t('common.confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 课程详情对话框 -->
    <el-dialog v-model="showDetailsDialog" :title="t('courseList.detailsDialog.title')" width="30%">
      <div v-if="currentCourse">
        <p><strong>{{ t('courseList.detailsDialog.id') }}:</strong> {{ currentCourse.id }}</p>
        <p><strong>{{ t('courseList.detailsDialog.name') }}:</strong> {{ currentCourse.name }}</p>
        <p><strong>{{ t('courseList.detailsDialog.schedule') }}:</strong> {{ currentCourse.schedule }}</p>
        <p><strong>{{ t('courseList.detailsDialog.coachId') }}:</strong> {{ currentCourse.coach_id }}</p>
        <p><strong>{{ t('courseList.detailsDialog.maxMembers') }}:</strong> {{ currentCourse.max_members }}</p>
      </div>
      <template #footer>
        <el-button @click="showDetailsDialog = false">{{ t('common.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { getCourses, createCourse, getCourseById } from '../api/courses';
import LanguageSwitcher from '../components/LanguageSwitcher.vue';

const courses = ref([]);
const loading = ref(false);
const showCreateDialog = ref(false);
const showDetailsDialog = ref(false);
const currentCourse = ref(null);

const newCourse = ref({
const { t } = useI18n();
  name: '',
  schedule: '',
  coach_id: null,
  max_members: null
});

const fetchCourses = async () => {
  try {
    loading.value = true;
    const data = await getCourses();
    courses.value = data;
  } catch (error) {
    console.error('Failed to fetch courses:', error);
  } finally {
    loading.value = false;
  }
};

const handleCreateCourse = async () => {
  try {
    await createCourse({
      name: newCourse.value.name,
      schedule: newCourse.value.schedule,
      coach_id: newCourse.value.coach_id,
      max_members: newCourse.value.max_members
    });
    showCreateDialog.value = false;
    newCourse.value = { name: '', schedule: '', coach_id: null, max_members: null };
    await fetchCourses();
  } catch (error) {
    console.error('Failed to create course:', error);
  }
};

const viewCourseDetails = async (courseId) => {
  try {
    currentCourse.value = await getCourseById(courseId);
    showDetailsDialog.value = true;
  } catch (error) {
    console.error('Failed to fetch course details:', error);
  }
};

onMounted(() => {
  fetchCourses();
});
</script>

<style scoped>
.course-list-container {
  padding: 20px;
}

.course-list-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>