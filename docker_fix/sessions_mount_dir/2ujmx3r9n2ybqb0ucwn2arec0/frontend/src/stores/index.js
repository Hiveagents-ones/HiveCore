import { createPinia } from 'pinia';

// 导入所有store模块
import { useUserStore } from './user';
import { useMembershipStore } from './membership';

// 创建pinia实例
const pinia = createPinia();

// 注册所有store模块
export { useUserStore, useMembershipStore };

export default pinia;