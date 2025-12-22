<template>
  <div class="member-import-container">
    <h2>批量导入会员</h2>
    
    <div class="import-section">
      <div class="file-upload">
        <input 
          type="file" 
          ref="fileInput" 
          accept=".csv,.xlsx,.xls" 
          @change="handleFileChange"
          class="file-input"
        />
        <button 
          class="upload-btn" 
          @click="triggerFileInput"
        >
          选择文件
        </button>
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
      </div>
      
      <div class="template-section">
        <a 
          href="#" 
          @click.prevent="downloadTemplate"
          class="template-link"
        >
          下载导入模板
        </a>
      </div>
    </div>
    
    <div class="preview-section" v-if="previewData.length > 0">
      <h3>导入预览 ({{ previewData.length }}条记录)</h3>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th v-for="header in tableHeaders" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in previewData" :key="index">
              <td v-for="header in tableHeaders" :key="header">{{ row[header] || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="action-buttons">
        <button 
          class="cancel-btn" 
          @click="resetImport"
        >
          取消
        </button>
        <button 
          class="confirm-btn" 
          @click="confirmImport"
          :disabled="isImporting"
        >
          {{ isImporting ? '导入中...' : '确认导入' }}
        </button>
      </div>
    </div>
    
    <div class="status-message" v-if="statusMessage">
      <p :class="statusType">{{ statusMessage }}</p>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import * as XLSX from 'xlsx';
import membersApi from '@/api/members';

export default {
  name: 'MemberImport',
  setup() {
    const fileInput = ref(null);
    const selectedFile = ref(null);
    const previewData = ref([]);
    const tableHeaders = ref([]);
    const isImporting = ref(false);
    const statusMessage = ref('');
    const statusType = ref('');

    const triggerFileInput = () => {
      fileInput.value.click();
    };

    const handleFileChange = (event) => {
      const file = event.target.files[0];
      if (!file) return;
      
      selectedFile.value = file;
      parseFile(file);
    };

    const parseFile = (file) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        // 转换为JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet);
        
        if (jsonData.length > 0) {
          // 获取表头
          tableHeaders.value = Object.keys(jsonData[0]);
          previewData.value = jsonData.slice(0, 10); // 预览前10条
        }
      };
      
      reader.readAsArrayBuffer(file);
    };

    const downloadTemplate = () => {
      // 创建模板数据
      const templateData = [
        {
          '姓名': '',
          '手机号': '',
          '邮箱': '',
          '性别': '',
          '生日': '',
          '地址': '',
          '备注': ''
        }
      ];
      
      // 创建工作簿
      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.json_to_sheet(templateData);
      
      // 添加到工作簿
      XLSX.utils.book_append_sheet(wb, ws, '会员导入模板');
      
      // 导出文件
      XLSX.writeFile(wb, '会员导入模板.xlsx');
    };

    const resetImport = () => {
      selectedFile.value = null;
      previewData.value = [];
      tableHeaders.value = [];
      statusMessage.value = '';
      if (fileInput.value) {
        fileInput.value.value = '';
      }
    };

    const confirmImport = async () => {
      if (!selectedFile.value || previewData.value.length === 0) {
        showStatus('请先选择有效的文件', 'error');
        return;
      }
      
      isImporting.value = true;
      showStatus('开始导入会员数据...', 'info');
      
      try {
        // 读取完整文件数据
        const reader = new FileReader();
        
        reader.onload = async (e) => {
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          
          // 转换为JSON
          const jsonData = XLSX.utils.sheet_to_json(worksheet);
          
          // 转换为API需要的格式
          const membersToImport = jsonData.map(item => ({
            name: item['姓名'] || '',
            phone: item['手机号'] || '',
            email: item['邮箱'] || '',
            gender: item['性别'] || '',
            birthDate: item['生日'] || '',
            address: item['地址'] || '',
            notes: item['备注'] || ''
          }));
          
          // 批量导入
          const results = await Promise.all(
            membersToImport.map(member => 
              membersApi.createMember(member).catch(e => ({
                error: true,
                message: e.response?.data?.message || e.message,
                member
              }))
            )
          );
          
          // 统计结果
          const successCount = results.filter(r => !r.error).length;
          const errorCount = results.filter(r => r.error).length;
          
          if (errorCount === 0) {
            showStatus(`成功导入 ${successCount} 条会员记录`, 'success');
          } else {
            showStatus(
              `导入完成: ${successCount} 条成功, ${errorCount} 条失败. ` +
              '失败的记录请检查数据后重新导入',
              'warning'
            );
          }
          
          resetImport();
        };
        
        reader.readAsArrayBuffer(selectedFile.value);
      } catch (error) {
        console.error('导入失败:', error);
        showStatus(`导入失败: ${error.message}`, 'error');
      } finally {
        isImporting.value = false;
      }
    };

    const showStatus = (message, type) => {
      statusMessage.value = message;
      statusType.value = type;
      
      // 5秒后自动清除消息
      if (type !== 'info') {
        setTimeout(() => {
          statusMessage.value = '';
        }, 5000);
      }
    };

    return {
      fileInput,
      selectedFile,
      previewData,
      tableHeaders,
      isImporting,
      statusMessage,
      statusType,
      triggerFileInput,
      handleFileChange,
      downloadTemplate,
      resetImport,
      confirmImport
    };
  }
};
</script>

<style scoped>
.member-import-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h2 {
  color: #333;
  margin-bottom: 20px;
  text-align: center;
}

.import-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.file-upload {
  display: flex;
  align-items: center;
}

.file-input {
  display: none;
}

.upload-btn {
  padding: 8px 16px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.upload-btn:hover {
  background-color: #66b1ff;
}

.file-name {
  margin-left: 10px;
  color: #666;
}

.template-link {
  color: #409eff;
  text-decoration: none;
  transition: color 0.3s;
}

.template-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.preview-section {
  margin-top: 20px;
}

h3 {
  margin-bottom: 15px;
  color: #333;
}

.table-container {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background-color: #f5f7fa;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

th {
  font-weight: 600;
  color: #333;
}

tr:hover {
  background-color: #f5f7fa;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cancel-btn {
  padding: 10px 20px;
  background-color: #f56c6c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.cancel-btn:hover {
  background-color: #f78989;
}

.confirm-btn {
  padding: 10px 20px;
  background-color: #67c23a;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.confirm-btn:hover:not(:disabled) {
  background-color: #85ce61;
}

.confirm-btn:disabled {
  background-color: #b3e19d;
  cursor: not-allowed;
}

.status-message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 4px;
}

.status-message .success {
  color: #67c23a;
  background-color: #f0f9eb;
}

.status-message .error {
  color: #f56c6c;
  background-color: #fef0f0;
}

.status-message .warning {
  color: #e6a23c;
  background-color: #fdf6ec;
}

.status-message .info {
  color: #909399;
  background-color: #f4f4f5;
}
</style>