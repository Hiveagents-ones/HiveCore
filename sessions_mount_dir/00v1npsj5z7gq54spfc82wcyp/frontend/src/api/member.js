import axios from 'axios';
import i18n from '@/i18n';

const API_BASE_URL = '/api/v1';
const DEFAULT_ERROR_MESSAGE = i18n.t('api.defaultErrorMessage');
const NETWORK_ERROR = i18n.t('api.networkError');
const SERVER_ERROR = i18n.t('api.serverError');
const MEMBER_NOT_FOUND = i18n.t('api.memberNotFound');
const INVALID_MEMBER_DATA = i18n.t('api.invalidMemberData');
const DUPLICATE_MEMBER = i18n.t('api.duplicateMember');
const MEMBER_UPDATE_FAILED = i18n.t('api.memberUpdateFailed');
const MEMBER_DELETE_FAILED = i18n.t('api.memberDeleteFailed');

/**
 * 会员API客户端
 */
export default {
  /**
   * 获取所有会员列表
   * @returns {Promise} Axios promise
   */
  getAllMembers() {
    return axios.get(`${API_BASE_URL}/members`)
      .catch(error => {
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_update_failed') {
          errorMessage = MEMBER_UPDATE_FAILED;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        throw new Error(errorMessage);
      });
  },

  /**
   * 获取单个会员详情
   * @param {number} id 会员ID
   * @returns {Promise} Axios promise
   */
  getMember(id) {
    return axios.get(`${API_BASE_URL}/members/${id}`)
      .catch(error => {
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_delete_failed') {
          errorMessage = MEMBER_DELETE_FAILED;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        throw new Error(errorMessage);
      });
  },

  /**
   * 创建新会员
   * @param {Object} memberData 会员数据
   * @returns {Promise} Axios promise
   */
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/members`, memberData)
      .catch(error => {
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (errorCode === 'duplicate_member') {
          errorMessage = DUPLICATE_MEMBER;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });
  },

  /**
   * 更新会员信息
   * @param {number} id 会员ID
   * @param {Object} memberData 更新的会员数据
   * @returns {Promise} Axios promise
   */
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/members/${id}`, memberData)
      .catch(error => {
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });
  },

  /**
   * 删除会员
   * @param {number} id 会员ID
   * @returns {Promise} Axios promise
   */
  deleteMember(id) {
    return axios.delete(`${API_BASE_URL}/members/${id}`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });
  },

  /**
   * 搜索会员
   * @param {Object} searchParams 搜索参数
   * @returns {Promise} Axios promise
   */
  searchMembers(searchParams) {
    return axios.get(`${API_BASE_URL}/members/search`, { params: searchParams })
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;
        
        if (errorCode === 'invalid_search_params') {
          errorMessage = i18n.t('api.invalidSearchParams');
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });
  }
};

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
  getAllMembers() {
    return axios.get(`${API_BASE_URL}/members`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_update_failed') {
          errorMessage = MEMBER_UPDATE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  getMember(id) {
    return axios.get(`${API_BASE_URL}/members/${id}`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_delete_failed') {
          errorMessage = MEMBER_DELETE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/members`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (errorCode === 'duplicate_member') {
          errorMessage = DUPLICATE_MEMBER;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/members/${id}`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }
        
        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }
        
        throw new Error(errorMessage);
      });

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
  getAllMembers() {
    return axios.get(`${API_BASE_URL}/members`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_update_failed') {
          errorMessage = MEMBER_UPDATE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  getMember(id) {
    return axios.get(`${API_BASE_URL}/members/${id}`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_delete_failed') {
          errorMessage = MEMBER_DELETE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/members`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (errorCode === 'duplicate_member') {
          errorMessage = DUPLICATE_MEMBER;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/members/${id}`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
  getAllMembers() {
    return axios.get(`${API_BASE_URL}/members`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_update_failed') {
          errorMessage = MEMBER_UPDATE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  getMember(id) {
    return axios.get(`${API_BASE_URL}/members/${id}`)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'member_delete_failed') {
          errorMessage = MEMBER_DELETE_FAILED;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  createMember(memberData) {
    return axios.post(`${API_BASE_URL}/members`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (errorCode === 'duplicate_member') {
          errorMessage = DUPLICATE_MEMBER;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });

# [AUTO-APPENDED] Failed to replace, adding new code:
  updateMember(id, memberData) {
    return axios.put(`${API_BASE_URL}/members/${id}`, memberData)
      .catch(error => {
        if (!error.response) {
          throw new Error(NETWORK_ERROR);
        }

        const errorCode = error.response?.data?.code;
        let errorMessage = DEFAULT_ERROR_MESSAGE;

        if (errorCode === 'member_not_found') {
          errorMessage = MEMBER_NOT_FOUND;
        } else if (errorCode === 'invalid_member_data') {
          errorMessage = INVALID_MEMBER_DATA;
        } else if (error.response?.status >= 500) {
          errorMessage = SERVER_ERROR;
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message;
        }

        throw new Error(errorMessage);
      });