#!/bin/bash
# 健身房会员系统测试 - 六阶段实时监控器

LOG_FILE="/Users/prayer/yiju/agentscope/docker_fix/gym_test_output.log"
REPORT_DIR="/Users/prayer/yiju/agentscope/docker_fix/stage_reports"
mkdir -p "$REPORT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  健身房会员系统测试 - 实时阶段监控器"
echo "=========================================="
echo ""

# 监控函数
monitor_stages() {
    tail -f "$LOG_FILE" 2>/dev/null | while read -r line; do
        timestamp=$(date '+%H:%M:%S')

        # 阶段1: 需求分析完成
        if echo "$line" | grep -q "当前需求列表"; then
            echo -e "${CYAN}[$timestamp] [阶段1-需求分析]${NC} 需求列表已生成"
            echo "[$timestamp] 需求分析完成" >> "$REPORT_DIR/stage1_requirements.log"
        fi

        if echo "$line" | grep -qE "^- R[0-9]+:"; then
            req=$(echo "$line" | sed 's/^- //')
            echo -e "${CYAN}  -> $req${NC}"
            echo "  $req" >> "$REPORT_DIR/stage1_requirements.log"
        fi

        # 阶段2: 验收标准生成
        if echo "$line" | grep -qE "\([0-9]+/[0-9]+\) 生成 R[0-9]+ 验收标准"; then
            progress=$(echo "$line" | grep -oE "\([0-9]+/[0-9]+\)")
            req_id=$(echo "$line" | grep -oE "R[0-9]+")
            echo -e "${YELLOW}[$timestamp] [阶段2-验收标准]${NC} $progress $req_id 生成中..."
        fi

        if echo "$line" | grep -qE "R[0-9]+ 生成完成，共 [0-9]+ 条标准"; then
            count=$(echo "$line" | grep -oE "[0-9]+ 条标准")
            req_id=$(echo "$line" | grep -oE "R[0-9]+")
            echo -e "${YELLOW}[$timestamp] [阶段2-验收标准]${NC} $req_id 完成: $count"
            echo "[$timestamp] $req_id: $count" >> "$REPORT_DIR/stage2_acceptance.log"
        fi

        # 阶段3: 代码生成
        if echo "$line" | grep -qE "^\[R[0-9]+\] 开始实现"; then
            req_id=$(echo "$line" | grep -oE "R[0-9]+")
            echo -e "${GREEN}[$timestamp] [阶段3-代码生成]${NC} $req_id 开始实现..."
            echo "" >> "$REPORT_DIR/stage3_codegen.log"
            echo "[$timestamp] === $req_id 开始实现 ===" >> "$REPORT_DIR/stage3_codegen.log"
        fi

        if echo "$line" | grep -qE "^\[STEPWISE\] \([0-9]+/[0-9]+\) 生成文件"; then
            progress=$(echo "$line" | grep -oE "\([0-9]+/[0-9]+\)")
            file=$(echo "$line" | sed 's/.*生成文件: //')
            echo -e "${GREEN}[$timestamp] [阶段3-代码生成]${NC} $progress $file"
            echo "  $progress $file" >> "$REPORT_DIR/stage3_codegen.log"
        fi

        if echo "$line" | grep -qE "^\[DEBUG\] Generated .* chars$"; then
            file=$(echo "$line" | sed 's/\[DEBUG\] Generated //' | sed 's/: [0-9]* chars//')
            chars=$(echo "$line" | grep -oE "[0-9]+ chars")
            # 检测是 DIFF 还是 FULL 模式
            if echo "$line" | grep -q "\[DIFF\]"; then
                echo -e "${GREEN}  -> 完成: $file ($chars) [DIFF增量]${NC}"
            elif echo "$line" | grep -q "\[FULL\]"; then
                echo -e "${GREEN}  -> 完成: $file ($chars) [FULL完整]${NC}"
            else
                echo -e "${GREEN}  -> 完成: $file ($chars)${NC}"
            fi
        fi

        # DIFF 模式相关日志
        if echo "$line" | grep -qE "^\[DIFF\] 使用 diff-based 模式修改"; then
            file=$(echo "$line" | grep -oE ": .* \(" | sed 's/: //' | sed 's/ (//')
            chars=$(echo "$line" | grep -oE "[0-9]+ chars")
            echo -e "${CYAN}[$timestamp] [DIFF模式]${NC} 开始增量修改: $file (原 $chars)"
        fi

        if echo "$line" | grep -qE "^\[DIFF\] 收到 [0-9]+ 个编辑指令"; then
            count=$(echo "$line" | grep -oE "[0-9]+ 个编辑指令")
            echo -e "${CYAN}  -> 收到 $count${NC}"
        fi

        if echo "$line" | grep -qE "^\[EDIT\] #[0-9]+"; then
            edit_info=$(echo "$line" | sed 's/\[EDIT\] //')
            if echo "$line" | grep -q "成功"; then
                echo -e "${GREEN}  -> $edit_info${NC}"
            else
                echo -e "${YELLOW}  -> $edit_info${NC}"
            fi
        fi

        if echo "$line" | grep -qE "^\[DIFF\] 编辑完成"; then
            info=$(echo "$line" | sed 's/\[DIFF\] //')
            echo -e "${CYAN}  -> $info${NC}"
        fi

        # DIFF 重试机制
        if echo "$line" | grep -qE "^\[DIFF\] 重试"; then
            retry_info=$(echo "$line" | sed 's/\[DIFF\] //')
            echo -e "${YELLOW}[$timestamp] [DIFF重试]${NC} $retry_info"
        fi

        if echo "$line" | grep -qE "^\[DIFF\] 部分编辑成功"; then
            info=$(echo "$line" | sed 's/\[DIFF\] //')
            echo -e "${YELLOW}  -> $info${NC}"
        fi

        if echo "$line" | grep -qE "^\[DIFF\] 重试.*次后仍失败"; then
            echo -e "${RED}[$timestamp] [DIFF失败]${NC} 回退到 FULL 模式"
        fi

        if echo "$line" | grep -qE "^\[STEPWISE\] 文件计划:"; then
            plan_info=$(echo "$line" | sed 's/\[STEPWISE\] //')
            echo -e "${GREEN}[$timestamp] [文件计划]${NC} $plan_info"
        fi

        # 阶段4: 代码验证
        if echo "$line" | grep -q "^\[VALIDATE\]"; then
            layer=$(echo "$line" | sed 's/\[VALIDATE\] //')
            echo -e "${BLUE}[$timestamp] [阶段4-代码验证]${NC} $layer"
            echo "[$timestamp] $layer" >> "$REPORT_DIR/stage4_validation.log"
        fi

        if echo "$line" | grep -qE "^\[STATIC\]|^\[IMPORT\]"; then
            result=$(echo "$line" | sed 's/^\[.*\] //')
            echo -e "${BLUE}  -> $result${NC}"
            echo "  $result" >> "$REPORT_DIR/stage4_validation.log"
        fi

        if echo "$line" | grep -qE "代码验证.*score"; then
            score=$(echo "$line" | grep -oE "score=[0-9]+%")
            req_id=$(echo "$line" | grep -oE "^\[R[0-9]+\]")
            if echo "$line" | grep -q "未通过"; then
                echo -e "${RED}[$timestamp] [阶段4-代码验证]${NC} $req_id 未通过 ($score)"
            else
                echo -e "${GREEN}[$timestamp] [阶段4-代码验证]${NC} $req_id 通过 ($score)"
            fi
            echo "[$timestamp] $req_id $score" >> "$REPORT_DIR/stage4_validation.log"
        fi

        # 阶段5: QA验收
        if echo "$line" | grep -qE "^\[R[0-9]+\] 开始 QA 验收"; then
            req_id=$(echo "$line" | grep -oE "R[0-9]+")
            echo -e "${PURPLE}[$timestamp] [阶段5-QA验收]${NC} $req_id 开始验收..."
            echo "" >> "$REPORT_DIR/stage5_qa.log"
            echo "[$timestamp] === $req_id QA验收 ===" >> "$REPORT_DIR/stage5_qa.log"
        fi

        if echo "$line" | grep -qE "Validation.*: (PASSED|FAILED)"; then
            name=$(echo "$line" | sed "s/.*Validation '//" | sed "s/':.*//")
            if echo "$line" | grep -q "PASSED"; then
                echo -e "${GREEN}[$timestamp] [阶段5-QA验收]${NC} ✓ $name"
                echo "  ✓ $name" >> "$REPORT_DIR/stage5_qa.log"
            else
                echo -e "${RED}[$timestamp] [阶段5-QA验收]${NC} ✗ $name"
                echo "  ✗ $name" >> "$REPORT_DIR/stage5_qa.log"
            fi
        fi

        # 阶段6: 轮次汇总
        if echo "$line" | grep -qE "Round [0-9]+ 完成|轮次.*完成|=== 第.*轮"; then
            echo -e "${PURPLE}[$timestamp] [阶段6-轮次汇总]${NC} $line"
            echo "[$timestamp] $line" >> "$REPORT_DIR/stage6_summary.log"
        fi

        # 错误检测
        if echo "$line" | grep -qE "Connection timeout|unhealthy|Max restart"; then
            echo -e "${RED}[$timestamp] [错误警告]${NC} $line"
            echo "[$timestamp] ERROR: $line" >> "$REPORT_DIR/errors.log"
        fi

        # 发现错误
        if echo "$line" | grep -qE "发现 [0-9]+ 个错误"; then
            errors=$(echo "$line" | grep -oE "[0-9]+ 个错误")
            req_id=$(echo "$line" | grep -oE "^\[R[0-9]+\]")
            echo -e "${YELLOW}[$timestamp] [问题汇总]${NC} $req_id $errors"
        fi

    done
}

# 启动监控
echo "开始监控日志: $LOG_FILE"
echo "报告输出目录: $REPORT_DIR"
echo ""
echo "按 Ctrl+C 停止监控"
echo "------------------------------------------"
echo ""

monitor_stages
