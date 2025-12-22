import axios from 'axios';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '../stores/auth';

// 创建axios实例
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const authStore = useAuthStore();
    
    if (error.response) {
      const { status, data } = error.response;
      
      // 处理401未授权错误
      if (status === 401) {
        // 尝试刷新token
        const refreshSuccess = await authStore.refreshToken();
        if (refreshSuccess) {
          // 重新发送原始请求
          return service(error.config);
        } else {
          // 刷新失败，跳转到登录页
          authStore.logout();
          return Promise.reject(error);
        }
      }
      
      // 处理403禁止访问错误
      if (status === 403) {
        ElMessage.error('没有权限访问该资源');
        return Promise.reject(error);
      }
      
      // 处理404未找到错误
      if (status === 404) {
        ElMessage.error('请求的资源不存在');
        return Promise.reject(error);
      }
      
      // 处理500服务器错误
      if (status >= 500) {
        ElMessage.error('服务器内部错误，请稍后重试');
        return Promise.reject(error);
      }
      
      // 处理其他错误
      const message = data?.message || '请求失败';
      ElMessage.error(message);
    } else if (error.request) {
      // 请求已发出但没有收到响应
      ElMessage.error('网络错误，请检查网络连接');
    } else {
      // 请求配置错误
      ElMessage.error('请求配置错误');
    }
    
    return Promise.reject(error);
  }
);

// API方法封装
export const api = {
  // GET请求
  get(url, params = {}) {
    return service.get(url, { params });
  },
  
  // POST请求
  post(url, data = {}) {
    return service.post(url, data);
  },
  
  // PUT请求
  put(url, data = {}) {
    return service.put(url, data);
  },
  
  // DELETE请求
  delete(url) {
    return service.delete(url);
  },
  
  // PATCH请求
  patch(url, data = {}) {
    return service.patch(url, data);
  },
  
  // 文件上传
  upload(url, formData) {
    return service.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  // 文件下载
  download(url, params = {}) {
    return service.get(url, {
      params,
      responseType: 'blob'
    });
  },

  // 支付相关API
  payment: {
    // 发起支付
    initiate(data) {
      return service.post('/payments', data);
    },

    // 确认支付
    confirm(paymentIntentId) {
      return service.post('/payments/confirm', { payment_intent_id: paymentIntentId });
    },

    // 获取支付历史
    getHistory(params = {}) {
      return service.get('/payments', { params });
    },

    // 获取支付详情
    getDetail(id) {
      return service.get(`/payments/${id}`);
    }
  },

  // 套餐相关API
  plan: {
    // 获取套餐列表
    getList() {
      return service.get('/plans');
    },

    // 获取套餐详情
    getDetail(id) {
      return service.get(`/plans/${id}`);
    }
  },

  // 会员相关API
  member: {
    // 获取会员信息
    getProfile() {
      return service.get('/members/me');
    },

    // 更新会员信息
    updateProfile(data) {
      return service.put('/members/me', data);
    },

    // 获取会员到期时间
    getExpiry() {
      return service.get('/members/me/expiry');
    }
  }
};

export default service;

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,

  // 课程相关API
  course: {
    // 获取课程列表
    getList(params = {}) {
      // 支持分页参数：skip 和 limit
      const { skip = 0, limit = 100, ...otherParams } = params;
      return service.get('/courses', { 
        params: {
          skip,
          limit,
          ...otherParams
        }
      });
    },
    
    // 获取课程详情
    getDetail(id) {
      return service.get(`/courses/${id}`);
    },
    
    // 创建课程
    create(data) {
      return service.post('/courses', data);
    },
    
    // 更新课程
    update(id, data) {
      return service.put(`/courses/${id}`, data);
    },
    
    // 删除课程
    delete(id) {
      return service.delete(`/courses/${id}`);
    }
  }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,

  // 课程相关API
  course: {
    // 获取课程列表
    getList(params = {}) {
      // 支持分页参数：skip 和 limit
      const { skip = 0, limit = 100, ...otherParams } = params;
      return service.get('/courses', { 
        params: {
          skip,
          limit,
          ...otherParams
        }
      });
    },

    // 获取课程详情
    getDetail(id) {
      return service.get(`/courses/${id}`);
    },

    // 创建课程
    create(data) {
      return service.post('/courses', data);
    },

    // 更新课程
    update(id, data) {
      return service.put(`/courses/${id}`, data);
    },

    // 删除课程
    delete(id) {
      return service.delete(`/courses/${id}`);
    }
  }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to insert:
,

  // 课程相关API
  course: {
    // 获取课程列表
    getList(params = {}) {
      // 支持分页参数：skip 和 limit
      const { skip = 0, limit = 100, ...otherParams } = params;
      return service.get('/courses', { 
        params: {
          skip,
          limit,
          ...otherParams
        }
      });
    },

    // 获取课程详情
    getDetail(id) {
      return service.get(`/courses/${id}`);
    },

    // 创建课程
    create(data) {
      return service.post('/courses', data);
    },

    // 更新课程
    update(id, data) {
      return service.put(`/courses/${id}`, data);
    },

    // 删除课程
    delete(id) {
      return service.delete(`/courses/${id}`);
    }
  }
,

  // 课程相关API
  course: {
    // 获取课程列表
    getList(params = {}) {
      // 支持分页参数：skip 和 limit
      const { skip = 0, limit = 100, ...otherParams } = params;
      return service.get('/courses', { 
        params: {
          skip,
          limit,
          ...otherParams
        }
      });
    },

    // 获取课程详情
    getDetail(id) {
      return service.get(`/courses/${id}`);
    },

    // 创建课程
    create(data) {
      return service.post('/courses', data);
    },

    // 更新课程
    update(id, data) {
      return service.put(`/courses/${id}`, data);
    },

    // 删除课程
    delete(id) {
      return service.delete(`/courses/${id}`);
    }
  }

  // 课程相关API
  course: {
    // 获取课程列表
    getList(params = {}) {
      // 支持分页参数：skip 和 limit
      const { skip = 0, limit = 100, ...otherParams } = params;
      return service.get('/courses', { 
        params: {
          skip,
          limit,
          ...otherParams
        }
      });
    },

    // 获取课程详情
    getDetail(id) {
      return service.get(`/courses/${id}`);
    },

    // 创建课程
    create(data) {
      return service.post('/courses', data);
    },

    // 更新课程
    update(id, data) {
      return service.put(`/courses/${id}`, data);
    },

    // 删除课程
    delete(id) {
      return service.delete(`/courses/${id}`);
    }
  }
};