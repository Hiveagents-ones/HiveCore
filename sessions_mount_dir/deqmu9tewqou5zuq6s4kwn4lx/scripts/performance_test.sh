#!/bin/bash

# 性能测试脚本
# 用于测试健身房课程预约系统的性能

# 设置工作区路径
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "工作区路径: $WORKSPACE_DIR"

# 检查必要的服务是否运行
check_services() {
    echo "检查服务状态..."
    
    # 检查后端服务
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "错误: 后端服务未运行，请先启动服务"
        exit 1
    fi
    
    # 检查数据库连接
    if ! docker exec $(docker-compose ps -q postgres) pg_isready -U postgres > /dev/null 2>&1; then
        echo "错误: 数据库连接失败"
        exit 1
    fi
    
    echo "所有服务运行正常"
}

# 运行负载测试
run_load_test() {
    echo "开始负载测试..."
    
    # 使用Apache Bench进行测试
    ab -n 1000 -c 10 http://localhost:8000/api/courses/
    
    # 测试预约接口
    ab -n 500 -c 5 -p $WORKSPACE_DIR/scripts/test_data.json -T application/json http://localhost:8000/api/bookings/
}

# 生成测试报告
generate_report() {
    echo "生成性能测试报告..."
    
    REPORT_DIR="$WORKSPACE_DIR/reports"
    mkdir -p $REPORT_DIR
    
    # 记录测试结果
    echo "性能测试报告 - $(date)" > $REPORT_DIR/performance_test_$(date +%Y%m%d_%H%M%S).txt
    echo "测试完成，报告保存在 $REPORT_DIR 目录"
}

# 主函数
main() {
    echo "=== 健身房课程预约系统性能测试 ==="
    
    check_services
    run_load_test
    generate_report
    
    echo "性能测试完成"
}

# 执行主函数
main "$@"