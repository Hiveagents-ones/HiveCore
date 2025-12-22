#!/bin/bash

# 性能测试自动化脚本
# 用于测试会籍续费与支付系统的性能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
TEST_DURATION="60s"
CONCURRENT_USERS="50"
RAMP_UP_TIME="10s"
REPORT_DIR="./reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建报告目录
mkdir -p $REPORT_DIR

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖工具..."
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        print_error "curl 未安装，请先安装 curl"
        exit 1
    fi
    
    # 检查ab (Apache Bench)
    if ! command -v ab &> /dev/null; then
        print_warning "ab (Apache Bench) 未安装，将跳过负载测试"
        SKIP_AB=true
    fi
    
    # 检查hey
    if ! command -v hey &> /dev/null; then
        print_warning "hey 未安装，将跳过并发测试"
        SKIP_HEY=true
    fi
    
    # 检查jq
    if ! command -v jq &> /dev/null; then
        print_warning "jq 未安装，JSON解析功能受限"
        SKIP_JQ=true
    fi
}

# 健康检查
health_check() {
    print_info "执行健康检查..."
    
    # 检查后端健康状态
    if curl -f -s "$BACKEND_URL/health" > /dev/null; then
        print_info "后端服务健康检查通过"
    else
        print_error "后端服务健康检查失败"
        exit 1
    fi
    
    # 检查前端健康状态
    if curl -f -s "$FRONTEND_URL" > /dev/null; then
        print_info "前端服务健康检查通过"
    else
        print_warning "前端服务健康检查失败"
    fi
}

# API性能测试
test_api_performance() {
    print_info "开始API性能测试..."
    
    # 测试支付历史API
    print_info "测试支付历史API性能..."
    curl -w "@curl-format.txt" -o /dev/null -s "$BACKEND_URL/api/payments/history" > "$REPORT_DIR/api_payment_history_$TIMESTAMP.txt"
    
    # 测试会员信息API
    print_info "测试会员信息API性能..."
    curl -w "@curl-format.txt" -o /dev/null -s "$BACKEND_URL/api/members/info" > "$REPORT_DIR/api_member_info_$TIMESTAMP.txt"
    
    # 测试支付处理API
    print_info "测试支付处理API性能..."
    curl -X POST -w "@curl-format.txt" -o /dev/null -s "$BACKEND_URL/api/payments/process" -H "Content-Type: application/json" -d '{"amount": 100, "method": "online"}' > "$REPORT_DIR/api_payment_process_$TIMESTAMP.txt"
}

# 负载测试
run_load_test() {
    if [ "$SKIP_AB" = true ]; then
        print_warning "跳过负载测试 (ab未安装)"
        return
    fi
    
    print_info "开始负载测试..."
    
    # 测试支付历史接口
    ab -n 1000 -c 10 -t $TEST_DURATION "$BACKEND_URL/api/payments/history" > "$REPORT_DIR/load_payment_history_$TIMESTAMP.txt"
    
    # 测试会员信息接口
    ab -n 1000 -c 10 -t $TEST_DURATION "$BACKEND_URL/api/members/info" > "$REPORT_DIR/load_member_info_$TIMESTAMP.txt"
    
    # 测试支付处理接口
    ab -n 500 -c 5 -t $TEST_DURATION -p payment_data.json -T application/json "$BACKEND_URL/api/payments/process" > "$REPORT_DIR/load_payment_process_$TIMESTAMP.txt"
}

# 并发测试
run_concurrent_test() {
    if [ "$SKIP_HEY" = true ]; then
        print_warning "跳过并发测试 (hey未安装)"
        return
    fi
    
    print_info "开始并发测试..."
    
    # 测试支付历史接口
    hey -n 1000 -c $CONCURRENT_USERS -z $TEST_DURATION "$BACKEND_URL/api/payments/history" > "$REPORT_DIR/concurrent_payment_history_$TIMESTAMP.txt"
    
    # 测试会员信息接口
    hey -n 1000 -c $CONCURRENT_USERS -z $TEST_DURATION "$BACKEND_URL/api/members/info" > "$REPORT_DIR/concurrent_member_info_$TIMESTAMP.txt"
    
    # 测试支付处理接口
    hey -n 500 -c $CONCURRENT_USERS -z $TEST_DURATION -d '{"amount": 100, "method": "online"}' -T application/json -m POST "$BACKEND_URL/api/payments/process" > "$REPORT_DIR/concurrent_payment_process_$TIMESTAMP.txt"
}

# 数据库性能测试
test_database_performance() {
    print_info "开始数据库性能测试..."
    
    # 使用Python脚本测试数据库性能
    if [ -f "backend/tests/test_performance.py" ]; then
        cd backend && python -m pytest tests/test_performance.py -v --tb=short > "../$REPORT_DIR/db_performance_$TIMESTAMP.txt" 2>&1 && cd ..
        print_info "数据库性能测试完成"
    else
        print_warning "数据库性能测试脚本不存在"
    fi
}

# 生成测试报告
generate_report() {
    print_info "生成测试报告..."
    
    REPORT_FILE="$REPORT_DIR/performance_report_$TIMESTAMP.html"
    
    cat > $REPORT_FILE << EOF
<!DOCTYPE html>
<html>
<head>
    <title>性能测试报告 - $TIMESTAMP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #ccc; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; }
        .test-section { margin: 20px 0; }
        pre { background: #f9f9f9; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>性能测试报告</h1>
    <div class="summary">
        <h2>测试概要</h2>
        <p>测试时间: $TIMESTAMP</p>
        <p>测试持续时间: $TEST_DURATION</p>
        <p>并发用户数: $CONCURRENT_USERS</p>
        <p>后端URL: $BACKEND_URL</p>
        <p>前端URL: $FRONTEND_URL</p>
    </div>
    
    <div class="test-section">
        <h2>API性能测试结果</h2>
EOF
    
    # 添加API测试结果
    for file in "$REPORT_DIR"/api_*_$TIMESTAMP.txt; do
        if [ -f "$file" ]; then
            echo "<h3>$(basename $file)</h3>" >> $REPORT_FILE
            echo "<pre>$(cat $file)</pre>" >> $REPORT_FILE
        fi
    done
    
    cat >> $REPORT_FILE << EOF
    </div>
    
    <div class="test-section">
        <h2>负载测试结果</h2>
EOF
    
    # 添加负载测试结果
    for file in "$REPORT_DIR"/load_*_$TIMESTAMP.txt; do
        if [ -f "$file" ]; then
            echo "<h3>$(basename $file)</h3>" >> $REPORT_FILE
            echo "<pre>$(cat $file)</pre>" >> $REPORT_FILE
        fi
    done
    
    cat >> $REPORT_FILE << EOF
    </div>
    
    <div class="test-section">
        <h2>并发测试结果</h2>
EOF
    
    # 添加并发测试结果
    for file in "$REPORT_DIR"/concurrent_*_$TIMESTAMP.txt; do
        if [ -f "$file" ]; then
            echo "<h3>$(basename $file)</h3>" >> $REPORT_FILE
            echo "<pre>$(cat $file)</pre>" >> $REPORT_FILE
        fi
    done
    
    cat >> $REPORT_FILE << EOF
    </div>
    
    <div class="test-section">
        <h2>数据库性能测试结果</h2>
EOF
    
    # 添加数据库测试结果
    if [ -f "$REPORT_DIR/db_performance_$TIMESTAMP.txt" ]; then
        echo "<pre>$(cat $REPORT_DIR/db_performance_$TIMESTAMP.txt)</pre>" >> $REPORT_FILE
    fi
    
    cat >> $REPORT_FILE << EOF
    </div>
</body>
</html>
EOF
    
    print_info "测试报告已生成: $REPORT_FILE"
}

# 清理临时文件
cleanup() {
    print_info "清理临时文件..."
    # 保留报告文件，清理其他临时文件
    # rm -f payment_data.json
}

# 主函数
main() {
    print_info "开始性能测试..."
    
    # 创建curl格式文件
    cat > curl-format.txt << EOF
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
    
    # 创建测试数据文件
    cat > payment_data.json << EOF
{"amount": 100, "method": "online", "member_id": "test_member_001"}
EOF
    
    # 执行测试步骤
    check_dependencies
    health_check
    test_api_performance
    run_load_test
    run_concurrent_test
    test_database_performance
    generate_report
    cleanup
    
    print_info "性能测试完成！"
}

# 执行主函数
main "$@"
