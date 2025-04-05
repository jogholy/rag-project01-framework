# Git配置备忘录

## 配置Git用户名和邮箱

### 配置用户名
```bash
git config --global user.name "Your Name"
```

### 配置邮箱
```bash
git config --global user.email "your.email@example.com"
```

### 查看配置信息
可以使用以下命令查看配置的用户名和邮箱：

1. 查看所有配置信息：
```bash
git config --global --list
```

2. 单独查看用户名：
```bash
git config --global user.name
```

3. 单独查看邮箱：
```bash
git config --global user.email
```

## 注意事项
- 使用 `--global` 参数表示全局配置，对所有仓库生效
- 如果只想对当前仓库配置，可以去掉 `--global` 参数
- 配置信息保存在用户目录下的 `.gitconfig` 文件中 