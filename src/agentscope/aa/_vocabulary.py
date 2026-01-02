# -*- coding: utf-8 -*-
"""Controlled vocabulary and normalization for Agent capabilities.

This module provides:
1. Core domains (强制受控，~10个)
2. Canonical skills vocabulary with synonyms (半受控 + 规范化)
3. Normalization functions for consistent matching
"""
from __future__ import annotations

from typing import Iterable


# =============================================================================
# Layer 1: Core Domains (强制受控)
# =============================================================================
# These are the top-level categories that every Agent must belong to.
# Used as hard filter during matching.

CORE_DOMAINS: dict[str, str] = {
    "backend": "后端开发",
    "frontend": "前端开发",
    "design": "UI/UX设计",
    "qa": "质量保证/测试",
    "devops": "部署运维",
    "architecture": "系统架构",
    "product": "产品管理",
    "data": "数据/AI/机器学习",
    "security": "安全",
    "specialist": "领域专家",  # 兜底分类
}

# Domain hierarchy: sub-domains under each core domain
DOMAIN_HIERARCHY: dict[str, set[str]] = {
    "backend": {
        "api", "microservices", "blockchain", "payment",
        "distributed", "middleware", "serverless",
    },
    "frontend": {
        "web", "mobile", "desktop", "miniprogram", "h5",
        "responsive", "pwa",
    },
    "design": {
        "ui", "ux", "visual", "interaction", "prototype",
        "graphic", "motion",
    },
    "qa": {
        "testing", "automation", "performance", "security_testing",
        "e2e", "unit_test", "integration",
    },
    "devops": {
        "ci_cd", "kubernetes", "docker", "cloud", "monitoring",
        "infrastructure", "sre",
    },
    "architecture": {
        "system_design", "high_availability", "scalability",
        "microservices_arch", "event_driven",
    },
    "product": {
        "requirements", "user_research", "roadmap", "agile",
        "scrum", "stakeholder",
    },
    "data": {
        "ml", "deep_learning", "nlp", "cv", "analytics",
        "etl", "data_pipeline", "llm", "ai",
    },
    "security": {
        "penetration", "audit", "compliance", "encryption",
        "authentication", "authorization",
    },
    "specialist": set(),  # Open for any specialized domain
}

# Synonyms for core domains
DOMAIN_SYNONYMS: dict[str, set[str]] = {
    "backend": {"后端", "服务端", "server", "server-side", "服务器端"},
    "frontend": {"前端", "客户端", "client", "client-side", "web端"},
    "design": {"设计", "ui", "ux", "界面", "交互"},
    "qa": {"测试", "质量", "testing", "quality", "test"},
    "devops": {"运维", "部署", "ops", "运营"},
    "architecture": {"架构", "系统设计", "architect"},
    "product": {"产品", "pm", "产品经理", "需求"},
    "data": {"数据", "ai", "ml", "机器学习", "人工智能", "算法"},
    "security": {"安全", "sec", "信息安全", "网络安全"},
    "specialist": {"专家", "专业", "领域"},
}


# =============================================================================
# Layer 2: Canonical Skills (半受控 + 规范化)
# =============================================================================
# Common skills with their synonyms. New skills can be added,
# but will be normalized to canonical form when possible.

CANONICAL_SKILLS: dict[str, set[str]] = {
    # Programming Languages
    "python": {"py", "python3", "Python", "蟒蛇"},
    "javascript": {"js", "JS", "Javascript", "JavaScript"},
    "typescript": {"ts", "TS", "Typescript", "TypeScript"},
    "java": {"Java", "jdk", "JDK"},
    "go": {"golang", "Golang", "Go"},
    "rust": {"Rust", "rs"},
    "cpp": {"c++", "C++", "cplusplus"},
    "csharp": {"c#", "C#", "dotnet", ".net"},
    "php": {"PHP", "php7", "php8"},
    "ruby": {"Ruby", "rb"},
    "swift": {"Swift", "ios_swift"},
    "kotlin": {"Kotlin", "kt"},
    "scala": {"Scala"},
    "sql": {"SQL", "数据库查询"},
    "shell": {"bash", "sh", "Bash", "Shell", "脚本"},
    "solidity": {"Solidity", "sol", "智能合约语言"},

    # Frontend Frameworks
    "react": {"reactjs", "React.js", "React", "ReactJS"},
    "vue": {"vuejs", "Vue.js", "Vue", "VueJS", "vue2", "vue3"},
    "angular": {"Angular", "angularjs", "AngularJS"},
    "svelte": {"Svelte", "sveltejs"},
    "nextjs": {"next.js", "Next.js", "next", "Next"},
    "nuxt": {"nuxtjs", "Nuxt.js", "Nuxt"},

    # Backend Frameworks
    "django": {"Django"},
    "flask": {"Flask"},
    "fastapi": {"FastAPI", "fast-api"},
    "spring": {"Spring", "springboot", "Spring Boot"},
    "express": {"expressjs", "Express.js", "Express"},
    "nestjs": {"NestJS", "nest.js", "Nest"},
    "gin": {"Gin"},
    "rails": {"ruby on rails", "Ruby on Rails", "ror", "RoR"},
    "laravel": {"Laravel"},

    # Databases
    "mysql": {"MySQL", "mariadb", "MariaDB"},
    "postgresql": {"postgres", "Postgres", "PostgreSQL", "pg", "PG"},
    "mongodb": {"mongo", "Mongo", "MongoDB"},
    "redis": {"Redis"},
    "elasticsearch": {"es", "ES", "Elasticsearch", "elastic"},
    "sqlite": {"SQLite", "sqlite3"},
    "oracle": {"Oracle", "oracle_db"},
    "sqlserver": {"sql server", "SQL Server", "mssql", "MSSQL"},

    # Cloud & DevOps
    "docker": {"Docker", "容器"},
    "kubernetes": {"k8s", "K8s", "Kubernetes", "k8"},
    "aws": {"AWS", "amazon", "Amazon Web Services"},
    "gcp": {"GCP", "google cloud", "Google Cloud"},
    "azure": {"Azure", "Microsoft Azure"},
    "aliyun": {"阿里云", "alibaba cloud", "Alibaba Cloud"},
    "tencent_cloud": {"腾讯云", "Tencent Cloud"},
    "nginx": {"Nginx", "NGINX"},
    "jenkins": {"Jenkins"},
    "gitlab_ci": {"gitlab ci", "GitLab CI"},
    "github_actions": {"github actions", "GitHub Actions"},
    "terraform": {"Terraform", "tf"},
    "ansible": {"Ansible"},

    # AI/ML
    "pytorch": {"PyTorch", "torch"},
    "tensorflow": {"TensorFlow", "tf_ml"},
    "scikit_learn": {"sklearn", "scikit-learn", "Scikit-learn"},
    "pandas": {"Pandas", "pd"},
    "numpy": {"NumPy", "np"},
    "llm": {"LLM", "大语言模型", "大模型", "语言模型"},
    "nlp": {"NLP", "自然语言处理", "文本处理"},
    "cv": {"CV", "计算机视觉", "图像处理", "computer vision"},
    "deep_learning": {"深度学习", "DL", "神经网络"},
    "machine_learning": {"机器学习", "ML"},

    # Concepts & Skills
    "api": {"API", "接口", "restful", "REST", "RESTful"},
    "graphql": {"GraphQL"},
    "grpc": {"gRPC", "GRPC"},
    "websocket": {"WebSocket", "ws", "实时通信"},
    "microservices": {"微服务", "micro-services"},
    "distributed": {"分布式", "distributed system"},
    "high_availability": {"高可用", "HA", "高可用性"},
    "high_concurrency": {"高并发", "并发"},
    "cache": {"缓存", "caching"},
    "mq": {"消息队列", "message queue", "MQ", "kafka", "rabbitmq"},
    "testing": {"测试", "test", "单元测试", "unit test"},
    "ci_cd": {"CI/CD", "持续集成", "持续部署", "CICD"},
    "agile": {"敏捷", "scrum", "Scrum", "看板"},
    "code_review": {"代码审查", "CR", "review"},

    # Blockchain
    "blockchain": {"区块链", "链", "Blockchain"},
    "smart_contract": {"智能合约", "合约"},
    "web3": {"Web3", "web3.js"},
    "ethereum": {"以太坊", "ETH", "eth"},
    "defi": {"DeFi", "去中心化金融"},

    # Security
    "security": {"安全", "信息安全", "网络安全"},
    "encryption": {"加密", "密码学", "cryptography"},
    "authentication": {"认证", "auth", "身份验证"},
    "authorization": {"授权", "权限"},
    "penetration": {"渗透测试", "渗透", "pentest"},

    # Mobile
    "ios": {"iOS", "苹果", "iPhone"},
    "android": {"Android", "安卓"},
    "flutter": {"Flutter"},
    "react_native": {"react native", "React Native", "RN"},
    "miniprogram": {"小程序", "微信小程序", "mini program"},

    # Design
    "figma": {"Figma"},
    "sketch": {"Sketch"},
    "photoshop": {"PS", "Photoshop", "ps"},
    "ui_design": {"UI设计", "界面设计", "视觉设计"},
    "ux_design": {"UX设计", "用户体验", "交互设计"},
    "prototype": {"原型", "原型设计", "wireframe"},
}


# =============================================================================
# Normalization Functions
# =============================================================================

def normalize_domain(domain: str) -> str:
    """Normalize a domain to its canonical core domain form.

    Args:
        domain: Domain string to normalize.

    Returns:
        Canonical domain name, or 'specialist' if not recognized.
    """
    domain_lower = domain.lower().strip()

    # Direct match
    if domain_lower in CORE_DOMAINS:
        return domain_lower

    # Synonym match
    for canonical, synonyms in DOMAIN_SYNONYMS.items():
        if domain_lower in {s.lower() for s in synonyms}:
            return canonical

    # Sub-domain match
    for parent, children in DOMAIN_HIERARCHY.items():
        if domain_lower in {c.lower() for c in children}:
            return parent

    # Default to specialist
    return "specialist"


def normalize_skill(skill: str) -> str:
    """Normalize a skill to its canonical form.

    Args:
        skill: Skill string to normalize.

    Returns:
        Canonical skill name, or original (lowercased) if not in vocabulary.
    """
    skill_lower = skill.lower().strip()

    # Direct match
    if skill_lower in CANONICAL_SKILLS:
        return skill_lower

    # Synonym match
    for canonical, synonyms in CANONICAL_SKILLS.items():
        if skill_lower in {s.lower() for s in synonyms}:
            return canonical

    # No match - return original lowercased
    return skill_lower


def normalize_skills(skills: Iterable[str]) -> set[str]:
    """Normalize a collection of skills.

    Args:
        skills: Iterable of skill strings.

    Returns:
        Set of normalized skill names.
    """
    return {normalize_skill(s) for s in skills if s}


def normalize_domains(domains: Iterable[str]) -> set[str]:
    """Normalize a collection of domains.

    Args:
        domains: Iterable of domain strings.

    Returns:
        Set of normalized domain names.
    """
    return {normalize_domain(d) for d in domains if d}


def get_primary_domain(domains: Iterable[str]) -> str:
    """Get the primary (first non-specialist) domain from a collection.

    Args:
        domains: Iterable of domain strings.

    Returns:
        Primary domain name.
    """
    normalized = normalize_domains(domains)

    # Prefer non-specialist domains
    for d in normalized:
        if d != "specialist":
            return d

    return "specialist"


def is_core_domain(domain: str) -> bool:
    """Check if a domain is a recognized core domain.

    Args:
        domain: Domain string to check.

    Returns:
        True if it's a core domain or synonym.
    """
    return normalize_domain(domain) in CORE_DOMAINS


def expand_skill_synonyms(skill: str) -> set[str]:
    """Get all synonyms for a skill (for fuzzy matching).

    Args:
        skill: Skill to expand.

    Returns:
        Set containing the skill and all its synonyms.
    """
    canonical = normalize_skill(skill)

    if canonical in CANONICAL_SKILLS:
        return {canonical} | CANONICAL_SKILLS[canonical]

    return {skill}


def skill_match_score(
    required_skills: Iterable[str],
    agent_skills: Iterable[str],
) -> float:
    """Calculate skill match score with normalization.

    Args:
        required_skills: Skills required by the task.
        agent_skills: Skills the agent has.

    Returns:
        Float between 0.0 and 1.0 indicating match degree.
    """
    req_normalized = normalize_skills(required_skills)
    agent_normalized = normalize_skills(agent_skills)

    if not req_normalized:
        return 1.0  # No requirements = full match

    matched = req_normalized & agent_normalized
    return len(matched) / len(req_normalized)


def domain_match_score(
    required_domains: Iterable[str],
    agent_domains: Iterable[str],
) -> float:
    """Calculate domain match score with normalization.

    Args:
        required_domains: Domains required by the task.
        agent_domains: Domains the agent covers.

    Returns:
        Float between 0.0 and 1.0 indicating match degree.
    """
    req_normalized = normalize_domains(required_domains)
    agent_normalized = normalize_domains(agent_domains)

    if not req_normalized:
        return 1.0  # No requirements = full match

    matched = req_normalized & agent_normalized
    return len(matched) / len(req_normalized)
