# BGE中文模型实现备忘录

## 需求背景
在文档向量化页面中，需要增加对 BAAI/bge-base-zh-v1.5 中文模型的支持，使前端可以选择并使用该模型进行文档向量化。

## 实现过程

### 1. 前端修改
在 `frontend/src/pages/EmbeddingFile.jsx` 中的 `modelOptions` 对象中添加新的模型选项：

```javascript
const modelOptions = {
  // ... 其他提供商配置 ...
  huggingface: [
    { value: 'sentence-transformers/all-mpnet-base-v2', label: 'all-mpnet-base-v2' },
    { value: 'all-MiniLM-L6-v2', label: 'all-MiniLM-L6-v2' },
    { value: 'google-bert/bert-base-uncased', label: 'bert-base-uncased' },
    { value: 'BAAI/bge-base-zh-v1.5', label: 'bge-base-zh-v1.5' }  // 新增中文模型选项
  ]
};
```

### 2. 后端修改
在 `backend/services/embedding_service.py` 中修改 `EmbeddingFactory` 类，以支持 BGE 模型：

#### 2.1 修改前的问题代码
```python
elif config.provider == EmbeddingProvider.HUGGINGFACE:
    model_kwargs = {}
    # 为 BAAI/bge-base-zh-v1.5 模型添加特殊配置
    if config.model_name == 'BAAI/bge-base-zh-v1.5':
        model_kwargs = {
            'device': 'cpu',  # 如果有GPU可以改为'cuda'
            'normalize_embeddings': True  # bge 模型推荐开启归一化
        }
    
    return HuggingFaceEmbeddings(
        model_name=config.model_name,
        model_kwargs=model_kwargs,
        encode_kwargs={'normalize_embeddings': True}  # 确保输出向量被归一化
    )
```

#### 2.2 修改后的正确代码
```python
elif config.provider == EmbeddingProvider.HUGGINGFACE:
    # 修改模型配置参数
    if config.model_name == 'BAAI/bge-base-zh-v1.5':
        return HuggingFaceEmbeddings(
            model_name=config.model_name,
            model_kwargs={'device': 'cpu'},  # 如果有GPU可以改为'cuda'
            encode_kwargs={'normalize_embeddings': True}  # 在encode_kwargs中设置normalize_embeddings
        )
    else:
        # 其他huggingface模型使用默认配置
        return HuggingFaceEmbeddings(
            model_name=config.model_name
        )
```

### 3. 主要修改点说明

1. 参数设置的位置：
   - 原始代码中错误地将 `normalize_embeddings` 放在了 `model_kwargs` 中
   - 修改后的代码只在 `encode_kwargs` 中设置 `normalize_embeddings`
   - `model_kwargs` 中只保留了 `device` 参数

2. 代码结构：
   - 原始代码使用了中间变量 `model_kwargs`
   - 修改后的代码直接在返回语句中设置参数，更加简洁

3. 错误处理：
   - 修改后的代码增加了对非 BGE 模型的处理分支
   - 其他 huggingface 模型使用默认配置，不添加额外参数

4. 参数正确性：
   - 原始代码中的参数设置方式会导致错误，因为 `normalize_embeddings` 不是模型加载时的参数
   - 修改后的代码将 `normalize_embeddings` 正确地放在了 `encode_kwargs` 中，这是在实际编码过程中使用的参数

## 注意事项

1. 确保服务器已安装必要的依赖包
2. 第一次使用时会自动下载模型文件（约 400MB）
3. 如果服务器有 GPU 且已安装 CUDA，可以将 'device' 改为 'cuda' 以提高性能

## 测试方法

1. 在前端界面选择文档
2. 选择 "HuggingFace" 作为 Provider
3. 选择 "bge-base-zh-v1.5" 作为 Model
4. 点击 "Generate Embeddings" 按钮

系统会使用这个中文模型对文档进行向量化处理。 