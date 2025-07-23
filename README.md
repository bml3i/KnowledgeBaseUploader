# KnowledgeBaseUploader

## 项目简介

这是一个基于Python3的知识库上传工具，用于从文件中提取特定格式的知识库内容并上传到PostgreSQL数据库。

## 功能特点

- 遍历指定目录下的所有文件（可按扩展名筛选）
- 提取以`<<<<.<<<<.<<<<`开始，以`>>>>.>>>>.>>>>`结束的代码块作为知识库元数据
- 提取`>>>>.>>>>.>>>>`后到最近的`----------`之间的内容作为知识库正文
- 支持知识库记录的插入和更新
- 支持标签管理和资源关联

## 安装要求

```bash
pip install -r requirements.txt
```

## 配置说明

首次使用时，需要从示例配置创建配置文件：

```bash
cp .config.ini.sample .config.ini
```

然后编辑`.config.ini`文件：

```ini
[common]
root_path = /path/to/your/files  # 要扫描的根目录
file_extension = txt,md          # 要处理的文件扩展名，用逗号分隔，使用*表示所有文件

[postgres]
server = localhost               # PostgreSQL服务器地址
port = 5432                      # 端口
db = postgres                    # 数据库名
user = your_username             # 用户名
password = your_password         # 密码
```

注意：`.config.ini`文件已添加到`.gitignore`中，不会被提交到代码仓库，这样可以避免敏感信息泄露，同时允许开发人员使用自己的配置进行测试。

## 数据格式

知识库元数据必须是有效的JSON格式，包含以下字段：

```json
{
  "echoToken": "唯一标识符",
  "summary": "摘要信息",
  "tags": ["标签1", "标签2"],
  "resources": ["资源1", "资源2"],
  "isActive": true
}
```

## 使用方法

```bash
python KnowledgeBaseUploader.py
```

## 数据库初始化

首次使用前，请在PostgreSQL中执行`Postgres DB Schema.sql`文件中的SQL语句，创建必要的表和视图。