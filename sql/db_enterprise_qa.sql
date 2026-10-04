-- =============================================================================
-- 企业知识库问答系统（RAG）数据库初始化脚本
-- 数据库：db_enterprise_qa    端口：3308    MySQL 版本：8.0+
-- 说明：脚本包含 建库 -> 建表 -> 初始化测试数据 三部分，可直接整体执行
-- 注意：所有用户密码均为 123456，采用 MD5 加密后存储
--       MD5('123456') = e10adc3949ba59abbe56e057f20f883e
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 一、创建数据库
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `db_enterprise_qa`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE `db_enterprise_qa`;

-- -----------------------------------------------------------------------------
-- 二、创建数据表（先删除后创建，方便反复执行脚本）
-- -----------------------------------------------------------------------------

-- ----------------------------
-- 1、用户表 sys_user
-- ----------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user`
(
    `id`              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `username`        VARCHAR(50)  NOT NULL COMMENT '登录账号',
    `password`        VARCHAR(64)  NOT NULL COMMENT '登录密码（MD5 加密后的 32 位字符串）',
    `nickname`        VARCHAR(50)  DEFAULT NULL COMMENT '用户昵称',
    `email`           VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    `phone`           VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
    `avatar`          VARCHAR(255) DEFAULT NULL COMMENT '头像地址',
    `role`            VARCHAR(20)  NOT NULL DEFAULT 'user' COMMENT '角色：admin=管理员，user=普通用户',
    `department`      VARCHAR(50)  DEFAULT NULL COMMENT '所属部门',
    `status`          TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1=正常，0=禁用',
    `last_login_time` DATETIME     DEFAULT NULL COMMENT '最近登录时间',
    `create_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_role` (`role`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='系统用户表';

-- ----------------------------
-- 2、知识库表 kb_knowledge_base
-- ----------------------------
DROP TABLE IF EXISTS `kb_knowledge_base`;
CREATE TABLE `kb_knowledge_base`
(
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `name`        VARCHAR(100) NOT NULL COMMENT '知识库名称',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '知识库描述',
    `category`    VARCHAR(50)  DEFAULT '通用' COMMENT '知识库分类：如 人事制度/技术文档/产品手册 等',
    `cover_color` VARCHAR(20)  DEFAULT '#409EFF' COMMENT '前端卡片主题色',
    `creator_id`  BIGINT       NOT NULL COMMENT '创建人ID（关联 sys_user.id）',
    `status`      TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1=启用，0=停用',
    `del_flag`    TINYINT      NOT NULL DEFAULT 0 COMMENT '删除标记：0=正常，1=已删除',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_creator` (`creator_id`),
    KEY `idx_category` (`category`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='知识库表';

-- ----------------------------
-- 3、知识库文档表 kb_document
-- ----------------------------
DROP TABLE IF EXISTS `kb_document`;
CREATE TABLE `kb_document`
(
    `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `kb_id`        BIGINT       NOT NULL COMMENT '所属知识库ID（关联 kb_knowledge_base.id）',
    `file_name`    VARCHAR(255) NOT NULL COMMENT '原始文件名',
    `file_path`    VARCHAR(500) DEFAULT NULL COMMENT '服务器本地存储路径',
    `file_type`    VARCHAR(20)  DEFAULT NULL COMMENT '文件类型：pdf/docx/txt/md/csv',
    `file_size`    BIGINT       DEFAULT 0 COMMENT '文件大小（字节）',
    `chunk_count`  INT          DEFAULT 0 COMMENT '切分后的文本块数量',
    `char_count`   INT          DEFAULT 0 COMMENT '文档总字符数',
    `status`       TINYINT      NOT NULL DEFAULT 0 COMMENT '处理状态：0=待处理，1=向量化中，2=已完成，3=失败',
    `error_msg`    VARCHAR(500) DEFAULT NULL COMMENT '失败原因',
    `uploader_id`  BIGINT       NOT NULL COMMENT '上传人ID（关联 sys_user.id）',
    `del_flag`     TINYINT      NOT NULL DEFAULT 0 COMMENT '删除标记：0=正常，1=已删除',
    `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_kb_id` (`kb_id`),
    KEY `idx_status` (`status`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='知识库文档表';

-- ----------------------------
-- 4、问答会话表 chat_session
-- ----------------------------
DROP TABLE IF EXISTS `chat_session`;
CREATE TABLE `chat_session`
(
    `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`       BIGINT       NOT NULL COMMENT '所属用户ID（关联 sys_user.id）',
    `kb_id`         BIGINT       DEFAULT NULL COMMENT '关联知识库ID，为空表示全部知识库',
    `title`         VARCHAR(200) DEFAULT '新的对话' COMMENT '会话标题（取首个问题前 30 个字符）',
    `message_count` INT          NOT NULL DEFAULT 0 COMMENT '会话消息条数',
    `del_flag`      TINYINT      NOT NULL DEFAULT 0 COMMENT '删除标记：0=正常，1=已删除',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_update_time` (`update_time`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='问答会话表';

-- ----------------------------
-- 5、问答消息表 chat_message
-- ----------------------------
DROP TABLE IF EXISTS `chat_message`;
CREATE TABLE `chat_message`
(
    `id`            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `session_id`    BIGINT      NOT NULL COMMENT '所属会话ID（关联 chat_session.id）',
    `user_id`       BIGINT      NOT NULL COMMENT '提问用户ID（关联 sys_user.id）',
    `kb_id`         BIGINT      DEFAULT NULL COMMENT '命中的知识库ID',
    `role`          VARCHAR(20) NOT NULL COMMENT '消息角色：user=用户提问，assistant=AI 回答',
    `content`       TEXT COMMENT '消息内容',
    `sources`       TEXT COMMENT '引用的知识来源（JSON 字符串数组）',
    `response_time` INT         DEFAULT 0 COMMENT 'AI 回答耗时（毫秒）',
    `create_time`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_session_id` (`session_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_create_time` (`create_time`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='问答消息表';

-- -----------------------------------------------------------------------------
-- 三、初始化测试数据
-- -----------------------------------------------------------------------------

-- ----------------------------
-- 用户数据（密码统一为 123456，此处为 MD5 密文）
-- ----------------------------
INSERT INTO `sys_user` (`id`, `username`, `password`, `nickname`, `email`, `phone`, `role`, `department`, `status`,
                        `last_login_time`, `create_time`)
VALUES (1, 'admin', 'e10adc3949ba59abbe56e057f20f883e', '超级管理员', 'admin@enterprise.com', '13800000001', 'admin',
        '信息技术部', 1, DATE_SUB(NOW(), INTERVAL 1 HOUR), DATE_SUB(NOW(), INTERVAL 60 DAY)),
       (2, 'manager', 'e10adc3949ba59abbe56e057f20f883e', '知识库管理员', 'manager@enterprise.com', '13800000002', 'admin',
        '综合管理部', 1, DATE_SUB(NOW(), INTERVAL 5 HOUR), DATE_SUB(NOW(), INTERVAL 55 DAY)),
       (3, 'zhangsan', 'e10adc3949ba59abbe56e057f20f883e', '张三', 'zhangsan@enterprise.com', '13800000003', 'user',
        '研发中心', 1, DATE_SUB(NOW(), INTERVAL 3 HOUR), DATE_SUB(NOW(), INTERVAL 50 DAY)),
       (4, 'lisi', 'e10adc3949ba59abbe56e057f20f883e', '李四', 'lisi@enterprise.com', '13800000004', 'user',
        '市场营销部', 1, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 45 DAY)),
       (5, 'wangwu', 'e10adc3949ba59abbe56e057f20f883e', '王五', 'wangwu@enterprise.com', '13800000005', 'user',
        '人力资源部', 1, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 40 DAY)),
       (6, 'zhaoliu', 'e10adc3949ba59abbe56e057f20f883e', '赵六', 'zhaoliu@enterprise.com', '13800000006', 'user',
        '财务部', 1, DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 30 DAY)),
       (7, 'sunqi', 'e10adc3949ba59abbe56e057f20f883e', '孙七', 'sunqi@enterprise.com', '13800000007', 'user',
        '研发中心', 0, DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_SUB(NOW(), INTERVAL 25 DAY)),
       (8, 'zhouba', 'e10adc3949ba59abbe56e057f20f883e', '周八', 'zhouba@enterprise.com', '13800000008', 'user',
        '客户服务部', 1, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 15 DAY));

-- ----------------------------
-- 知识库数据
-- ----------------------------
INSERT INTO `kb_knowledge_base` (`id`, `name`, `description`, `category`, `cover_color`, `creator_id`, `status`,
                                 `create_time`)
VALUES (1, '人事管理制度', '公司员工手册、考勤制度、休假规定、薪酬福利等 HR 相关制度文档', '人事制度', '#409EFF', 1, 1,
        DATE_SUB(NOW(), INTERVAL 45 DAY)),
       (2, '技术开发规范', '后端编码规范、前端开发约定、Git 分支管理、接口设计规范等技术文档', '技术文档', '#67C23A', 1, 1,
        DATE_SUB(NOW(), INTERVAL 40 DAY)),
       (3, '产品使用手册', '公司各产品线的功能说明、操作指引、常见问题解答', '产品手册', '#E6A23C', 2, 1,
        DATE_SUB(NOW(), INTERVAL 35 DAY)),
       (4, '财务报销流程', '差旅报销标准、发票要求、审批流程、费用申请说明', '财务制度', '#F56C6C', 1, 1,
        DATE_SUB(NOW(), INTERVAL 28 DAY)),
       (5, '新员工入职指南', '入职办理流程、办公环境介绍、账号权限申请、试用期考核说明', '人事制度', '#909399', 2, 1,
        DATE_SUB(NOW(), INTERVAL 20 DAY));

-- ----------------------------
-- 文档数据（状态 2=向量化完成）
-- ----------------------------
INSERT INTO `kb_document` (`id`, `kb_id`, `file_name`, `file_path`, `file_type`, `file_size`, `chunk_count`, `char_count`,
                           `status`, `uploader_id`, `create_time`)
VALUES (1, 1, '员工考勤管理制度.pdf', 'uploads/1/员工考勤管理制度.pdf', 'pdf', 524288, 42, 18600, 2, 1,
        DATE_SUB(NOW(), INTERVAL 44 DAY)),
       (2, 1, '员工休假管理规定.docx', 'uploads/1/员工休假管理规定.docx', 'docx', 131072, 28, 11200, 2, 2,
        DATE_SUB(NOW(), INTERVAL 42 DAY)),
       (3, 1, '薪酬福利说明.md', 'uploads/1/薪酬福利说明.md', 'md', 20480, 15, 6300, 2, 2,
        DATE_SUB(NOW(), INTERVAL 38 DAY)),
       (4, 2, 'Java后端编码规范.pdf', 'uploads/2/Java后端编码规范.pdf', 'pdf', 786432, 65, 29000, 2, 1,
        DATE_SUB(NOW(), INTERVAL 36 DAY)),
       (5, 2, '前端开发规范.docx', 'uploads/2/前端开发规范.docx', 'docx', 262144, 33, 14500, 2, 1,
        DATE_SUB(NOW(), INTERVAL 30 DAY)),
       (6, 2, 'Git分支管理规范.md', 'uploads/2/Git分支管理规范.md', 'md', 15360, 12, 5200, 2, 2,
        DATE_SUB(NOW(), INTERVAL 26 DAY)),
       (7, 2, '接口设计规范V2.pdf', 'uploads/2/接口设计规范V2.pdf', 'pdf', 419430, 38, 16800, 2, 1,
        DATE_SUB(NOW(), INTERVAL 18 DAY)),
       (8, 3, '智能客服产品操作手册.pdf', 'uploads/3/智能客服产品操作手册.pdf', 'pdf', 1048576, 88, 39000, 2, 2,
        DATE_SUB(NOW(), INTERVAL 24 DAY)),
       (9, 3, '数据分析平台使用说明.docx', 'uploads/3/数据分析平台使用说明.docx', 'docx', 524288, 46, 21000, 2, 2,
        DATE_SUB(NOW(), INTERVAL 16 DAY)),
       (10, 3, '常见问题FAQ.txt', 'uploads/3/常见问题FAQ.txt', 'txt', 30720, 20, 8800, 2, 1,
        DATE_SUB(NOW(), INTERVAL 12 DAY)),
       (11, 4, '差旅费报销标准.pdf', 'uploads/4/差旅费报销标准.pdf', 'pdf', 245760, 25, 10500, 2, 1,
        DATE_SUB(NOW(), INTERVAL 20 DAY)),
       (12, 4, '发票开具与要求.docx', 'uploads/4/发票开具与要求.docx', 'docx', 98304, 14, 5900, 2, 2,
        DATE_SUB(NOW(), INTERVAL 10 DAY)),
       (13, 5, '新员工入职办理流程.pdf', 'uploads/5/新员工入职办理流程.pdf', 'pdf', 327680, 30, 12600, 2, 2,
        DATE_SUB(NOW(), INTERVAL 15 DAY)),
       (14, 5, '办公账号权限申请表.docx', 'uploads/5/办公账号权限申请表.docx', 'docx', 65536, 8, 3200, 3, 2,
        DATE_SUB(NOW(), INTERVAL 8 DAY)),
       (15, 5, '试用期考核说明.md', 'uploads/5/试用期考核说明.md', 'md', 12288, 10, 4100, 2, 2,
        DATE_SUB(NOW(), INTERVAL 5 DAY));

-- ----------------------------
-- 会话数据（分布在最近 14 天，用于首页趋势图展示）
-- ----------------------------
INSERT INTO `chat_session` (`id`, `user_id`, `kb_id`, `title`, `message_count`, `create_time`, `update_time`)
VALUES (1, 3, 1, '年假有多少天，怎么申请？', 4, DATE_SUB(NOW(), INTERVAL 13 DAY), DATE_SUB(NOW(), INTERVAL 13 DAY)),
       (2, 3, 2, 'Java 方法命名的规范是什么？', 2, DATE_SUB(NOW(), INTERVAL 11 DAY), DATE_SUB(NOW(), INTERVAL 11 DAY)),
       (3, 4, 3, '智能客服怎么配置知识库？', 6, DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_SUB(NOW(), INTERVAL 10 DAY)),
       (4, 5, 1, '迟到会怎么扣钱？', 2, DATE_SUB(NOW(), INTERVAL 9 DAY), DATE_SUB(NOW(), INTERVAL 9 DAY)),
       (5, 6, 4, '出差住宿费的标准是多少？', 4, DATE_SUB(NOW(), INTERVAL 8 DAY), DATE_SUB(NOW(), INTERVAL 8 DAY)),
       (6, 3, 2, 'Git 分支应该怎么命名？', 2, DATE_SUB(NOW(), INTERVAL 7 DAY), DATE_SUB(NOW(), INTERVAL 7 DAY)),
       (7, 4, 5, '新员工第一天需要做什么？', 2, DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY)),
       (8, 5, 4, '发票抬头写错了怎么办？', 4, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY)),
       (9, 6, 3, '数据分析平台怎么导出报表？', 2, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
       (10, 3, 1, '婚假和产假分别多少天？', 4, DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
       (11, 4, 2, '接口返回值格式有什么要求？', 2, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (12, 5, 5, '试用期考核不通过会怎样？', 2, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (13, 3, 3, 'FAQ 文档怎么维护更新？', 4, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (14, 6, 2, '代码提交前需要做哪些检查？', 2, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (15, 4, 4, '报销单多久能审批完成？', 2, NOW(), NOW());

-- ----------------------------
-- 消息数据（user=提问，assistant=回答）
-- ----------------------------
INSERT INTO `chat_message` (`session_id`, `user_id`, `kb_id`, `role`, `content`, `sources`, `response_time`,
                            `create_time`)
VALUES (1, 3, 1, 'user', '年假有多少天，怎么申请？', NULL, 0, DATE_SUB(NOW(), INTERVAL 13 DAY)),
       (1, 3, 1, 'assistant',
        '根据《员工休假管理规定》：入职满 1 年不满 3 年的员工，每年享有 5 天带薪年假；满 3 年不满 5 年为 10 天；满 5 年以上为 15 天。申请方式：登录 OA 系统 → 休假申请 → 选择"年假"类型 → 填写起止日期并提交直属上级审批，审批通过后即可休假。',
        '[{"file_name":"员工休假管理规定.docx","kb_name":"人事管理制度","score":0.89}]', 3200,
        DATE_SUB(NOW(), INTERVAL 13 DAY)),
       (2, 3, 2, 'user', 'Java 方法命名的规范是什么？', NULL, 0, DATE_SUB(NOW(), INTERVAL 11 DAY)),
       (2, 3, 2, 'assistant',
        '根据《Java后端编码规范》：方法名统一使用小驼峰命名法（lowerCamelCase），首字母小写，禁止使用下划线或美元符号；方法名应为动词或动词短语，如 getUserById、saveOrder；布尔类型的 getter 建议以 is/has/can 开头，如 isDeleted。',
        '[{"file_name":"Java后端编码规范.pdf","kb_name":"技术开发规范","score":0.92}]', 2800,
        DATE_SUB(NOW(), INTERVAL 11 DAY)),
       (3, 4, 3, 'user', '智能客服怎么配置知识库？', NULL, 0, DATE_SUB(NOW(), INTERVAL 10 DAY)),
       (3, 4, 3, 'assistant',
        '在《智能客服产品操作手册》中，配置知识库的步骤如下：1）进入"知识管理"菜单，点击"新建知识库"；2）填写知识库名称与分类；3）上传文档（支持 PDF、Word、TXT 格式）；4）等待系统自动切分与向量化，状态变为"已完成"即生效；5）在"机器人设置"中绑定该知识库并发布。',
        '[{"file_name":"智能客服产品操作手册.pdf","kb_name":"产品使用手册","score":0.95}]', 4100,
        DATE_SUB(NOW(), INTERVAL 10 DAY)),
       (4, 5, 1, 'user', '迟到会怎么扣钱？', NULL, 0, DATE_SUB(NOW(), INTERVAL 9 DAY)),
       (4, 5, 1, 'assistant',
        '根据《员工考勤管理制度》：每月累计迟到 3 次以内（含）且单次不超过 30 分钟的，予以口头提醒不扣款；超过 3 次的，从第 4 次起每次扣款 50 元；单次迟到超过 60 分钟按事假半天处理。',
        '[{"file_name":"员工考勤管理制度.pdf","kb_name":"人事管理制度","score":0.87}]', 2600,
        DATE_SUB(NOW(), INTERVAL 9 DAY)),
       (5, 6, 4, 'user', '出差住宿费的标准是多少？', NULL, 0, DATE_SUB(NOW(), INTERVAL 8 DAY)),
       (5, 6, 4, 'assistant',
        '根据《差旅费报销标准》：一线城市（北上广深）住宿标准为每晚 500 元，省会城市为 400 元，其他城市为 300 元。超标部分需自行承担，如因特殊情况超标需提前提交说明并经部门负责人审批。',
        '[{"file_name":"差旅费报销标准.pdf","kb_name":"财务报销流程","score":0.93}]', 3000,
        DATE_SUB(NOW(), INTERVAL 8 DAY)),
       (6, 3, 2, 'user', 'Git 分支应该怎么命名？', NULL, 0, DATE_SUB(NOW(), INTERVAL 7 DAY)),
       (6, 3, 2, 'assistant',
        '根据《Git分支管理规范》：主干分支为 main（生产）与 develop（开发）；功能分支命名为 feature/功能名，如 feature/user-login；修复分支命名为 hotfix/问题描述。分支名统一使用小写字母与中划线，禁止使用中文和空格。',
        '[{"file_name":"Git分支管理规范.md","kb_name":"技术开发规范","score":0.91}]', 2400,
        DATE_SUB(NOW(), INTERVAL 7 DAY)),
       (7, 4, 5, 'user', '新员工第一天需要做什么？', NULL, 0, DATE_SUB(NOW(), INTERVAL 6 DAY)),
       (7, 4, 5, 'assistant',
        '根据《新员工入职办理流程》：第一天需要 1）到前台办理入职登记并领取工牌；2）提交身份证、学历证书等材料的复印件；3）签署劳动合同与保密协议；4）由 HR 带领熟悉办公环境；5）领取办公电脑并申请系统账号权限。',
        '[{"file_name":"新员工入职办理流程.pdf","kb_name":"新员工入职指南","score":0.9}]', 3500,
        DATE_SUB(NOW(), INTERVAL 6 DAY)),
       (8, 5, 4, 'user', '发票抬头写错了怎么办？', NULL, 0, DATE_SUB(NOW(), INTERVAL 5 DAY)),
       (8, 5, 4, 'assistant',
        '根据《发票开具与要求》：发票抬头必须与公司全称一致，如填写错误需联系开票方作废原发票并重新开具，作废发票需一并交回财务部。增值税专用发票还需保证税号、开户行及账号信息完整无误。',
        '[{"file_name":"发票开具与要求.docx","kb_name":"财务报销流程","score":0.88}]', 2700,
        DATE_SUB(NOW(), INTERVAL 5 DAY)),
       (9, 6, 3, 'user', '数据分析平台怎么导出报表？', NULL, 0, DATE_SUB(NOW(), INTERVAL 4 DAY)),
       (9, 6, 3, 'assistant',
        '根据《数据分析平台使用说明》：进入报表页面后，点击右上角"导出"按钮，可选择导出为 Excel 或 PDF 格式；若报表数据量较大，建议选择"异步导出"，系统生成完成后会在消息中心推送下载链接。',
        '[{"file_name":"数据分析平台使用说明.docx","kb_name":"产品使用手册","score":0.86}]', 2900,
        DATE_SUB(NOW(), INTERVAL 4 DAY)),
       (10, 3, 1, 'user', '婚假和产假分别多少天？', NULL, 0, DATE_SUB(NOW(), INTERVAL 3 DAY)),
       (10, 3, 1, 'assistant',
        '根据《员工休假管理规定》：婚假为 10 天（含法定 3 天，公司额外给予 7 天）；产假为 158 天（含法定 98 天及地方奖励假 60 天），男方陪产假为 15 天。以上假期均为带薪假期，需提前 15 个工作日在 OA 提交申请。',
        '[{"file_name":"员工休假管理规定.docx","kb_name":"人事管理制度","score":0.94}]', 3300,
        DATE_SUB(NOW(), INTERVAL 3 DAY)),
       (11, 4, 2, 'user', '接口返回值格式有什么要求？', NULL, 0, DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (11, 4, 2, 'assistant',
        '根据《接口设计规范V2》：所有接口统一返回 JSON 格式，结构为 {code, message, data}。code 为 200 表示成功，非 200 表示业务异常；message 用于返回提示信息；data 为业务数据，列表查询需返回 {list, total, page, size} 结构。',
        '[{"file_name":"接口设计规范V2.pdf","kb_name":"技术开发规范","score":0.96}]', 3100,
        DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (12, 5, 5, 'user', '试用期考核不通过会怎样？', NULL, 0, DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (12, 5, 5, 'assistant',
        '根据《试用期考核说明》：试用期一般为 3 个月，考核在到期前 10 个工作日进行。首次考核不通过的可延长试用期 1 个月并制定改进计划；延长后仍不通过的，公司有权依法解除劳动合同。',
        '[{"file_name":"试用期考核说明.md","kb_name":"新员工入职指南","score":0.89}]', 2500,
        DATE_SUB(NOW(), INTERVAL 2 DAY)),
       (13, 3, 3, 'user', 'FAQ 文档怎么维护更新？', NULL, 0, DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (13, 3, 3, 'assistant',
        '根据《常见问题FAQ》：FAQ 文档由各业务线负责人每月更新一次，新增问题需先在知识库中上传新版文档，系统会自动重新切分并覆盖旧的向量数据，无需手动删除历史记录。',
        '[{"file_name":"常见问题FAQ.txt","kb_name":"产品使用手册","score":0.85}]', 2300,
        DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (14, 6, 2, 'user', '代码提交前需要做哪些检查？', NULL, 0, DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (14, 6, 2, 'assistant',
        '根据《Java后端编码规范》：代码提交前需完成 1）本地编译通过且无警告；2）单元测试覆盖率不低于 60%；3）执行代码格式化与静态检查（SonarQube 无阻断问题）；4）提交信息按照 feat/fix/docs 前缀规范填写。',
        '[{"file_name":"Java后端编码规范.pdf","kb_name":"技术开发规范","score":0.9}]', 3400,
        DATE_SUB(NOW(), INTERVAL 1 DAY)),
       (15, 4, 4, 'user', '报销单多久能审批完成？', NULL, 0, NOW()),
       (15, 4, 4, 'assistant',
        '根据《差旅费报销标准》：报销单提交后，直属上级审批一般在 1 个工作日内完成，财务复核在 3 个工作日内完成，审批通过后款项将在 5 个工作日内打至工资卡。',
        '[{"file_name":"差旅费报销标准.pdf","kb_name":"财务报销流程","score":0.87}]', 2800, NOW());

-- -----------------------------------------------------------------------------
-- 四、执行结果校验
-- -----------------------------------------------------------------------------
SELECT '用户数量' AS 统计项, COUNT(*) AS 数量 FROM `sys_user`
UNION ALL
SELECT '知识库数量', COUNT(*) FROM `kb_knowledge_base`
UNION ALL
SELECT '文档数量', COUNT(*) FROM `kb_document`
UNION ALL
SELECT '会话数量', COUNT(*) FROM `chat_session`
UNION ALL
SELECT '消息数量', COUNT(*) FROM `chat_message`;

-- =============================================================================
-- 脚本执行完毕。默认账号：
--   管理员：admin / 123456      manager / 123456
--   普通用户：zhangsan / 123456  lisi / 123456  wangwu / 123456
-- =============================================================================
