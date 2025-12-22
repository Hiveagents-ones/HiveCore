<template>
  <div class="tax-settings-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>税务设置</span>
        </div>
      </template>

      <el-form :model="taxForm" label-width="120px" :rules="rules" ref="taxForm">
        <el-form-item label="税率类型" prop="taxType">
          <el-select v-model="taxForm.taxType" placeholder="请选择税率类型">
            <el-option
              v-for="item in taxTypes"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            ></el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="税率(%)" prop="rate">
          <el-input-number
            v-model="taxForm.rate"
            :min="0"
            :max="100"
            :precision="2"
            :step="0.1"
          ></el-input-number>
        </el-form-item>

        <el-form-item label="生效日期" prop="effectiveDate">
          <el-date-picker
            v-model="taxForm.effectiveDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          ></el-date-picker>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="taxForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入税率描述"
          ></el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm">保存</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-divider></el-divider>

    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>当前税率</span>
        </div>
      </template>
      <el-table :data="currentTaxRates" style="width: 100%" border>
        <el-table-column prop="taxType" label="税率类型" width="180" />
        <el-table-column prop="rate" label="税率(%)" width="120" />
        <el-table-column prop="effectiveDate" label="生效日期" width="180" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(scope.row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from '@/api/axios';

export default {
  name: 'TaxSettings',
  setup() {
    const taxForm = reactive({
      taxType: '',
      rate: 0,
      effectiveDate: '',
      description: ''
    });

    const rules = reactive({
      taxType: [
        { required: true, message: '请选择税率类型', trigger: 'change' }
      ],
      rate: [
        { required: true, message: '请输入税率', trigger: 'blur' },
        { type: 'number', min: 0, max: 100, message: '税率必须在0-100之间', trigger: 'blur' }
      ],
      effectiveDate: [
        { required: true, message: '请选择生效日期', trigger: 'change' }
      ]
    });

    const taxTypes = ref([
      { value: 'VAT', label: '增值税' },
      { value: 'SALES_TAX', label: '销售税' },
      { value: 'INCOME_TAX', label: '所得税' },
      { value: 'OTHER', label: '其他' }
    ]);

    const currentTaxRates = ref([]);
    const taxFormRef = ref(null);

    const fetchTaxRates = async () => {
      try {
        const response = await axios.get('/api/v1/payments/tax-rates');
        currentTaxRates.value = response.data;
      } catch (error) {
        ElMessage.error('获取税率列表失败');
        console.error(error);
      }
    };

    const submitForm = () => {
      taxFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            await axios.post('/api/v1/payments/tax-rates', taxForm);
            ElMessage.success('税率设置成功');
            resetForm();
            fetchTaxRates();
          } catch (error) {
            ElMessage.error('税率设置失败');
            console.error(error);
          }
        } else {
          return false;
        }
      });
    };

    const resetForm = () => {
      taxFormRef.value.resetFields();
    };

    const handleDelete = (row) => {
      ElMessageBox.confirm('确定要删除该税率设置吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          await axios.delete(`/api/v1/payments/tax-rates/${row.id}`);
          ElMessage.success('删除成功');
          fetchTaxRates();
        } catch (error) {
          ElMessage.error('删除失败');
          console.error(error);
        }
      }).catch(() => {});
    };

    onMounted(() => {
      fetchTaxRates();
    });

    return {
      taxForm,
      rules,
      taxTypes,
      currentTaxRates,
      taxFormRef,
      submitForm,
      resetForm,
      handleDelete
    };
  }
};
</script>

<style scoped>
.tax-settings-container {
  padding: 20px;
}

.box-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.el-form {
  max-width: 600px;
}
</style>