# TracePicker 重构完成总结

## 完成的工作

### ✅ 项目结构重构
- 将原始代码重构为标准Python包结构 (`src/tracepicker/`)
- 按功能模块分离：`core/`, `entities/`, `algorithms/`, `preprocessing/`, `utils/`
- 实现了清晰的模块导入和依赖关系

### ✅ 数据格式适配
- 新增 **Polars** 数据加载器支持现代parquet格式
- 保持向后兼容，支持原有pickle格式
- 自动检测和处理不同数据目录结构
- 解决schema不匹配问题（normal vs abnormal traces）

### ✅ 平台集成
- 实现 rcabench 平台适配器
- 符合 Algorithm 接口规范
- 提供标准化的输入输出格式

### ✅ 现代CLI界面
- 使用 **typer** 和 **rich** 构建用户友好的命令行界面
- 支持进度显示和彩色输出
- 提供 `run` 和 `info` 命令

### ✅ 兼容性保障
- 创建 legacy_loader.py 处理旧格式pickle文件
- 实现模块别名映射解决导入问题
- 保持所有原有功能不变

## 文件结构

```
TracePicker/
├── src/tracepicker/              # 主包目录
│   ├── __init__.py              # 包入口，lazy loading
│   ├── cli.py                   # 现代CLI界面
│   ├── core/                    # 核心算法
│   │   ├── tracepicker.py       # 主算法实现
│   │   ├── buffer.py            # 缓冲区管理
│   │   └── ...
│   ├── entities/                # 数据实体
│   │   ├── trace.py             # Trace/Span类定义
│   │   └── ...
│   ├── algorithms/              # 算法和优化
│   │   ├── platform_adapter.py  # 平台适配器
│   │   └── ...
│   ├── preprocessing/           # 数据预处理
│   │   └── ...
│   └── utils/                   # 工具模块
│       ├── new_data_loader.py   # 新数据格式加载器
│       ├── legacy_loader.py     # 旧格式兼容
│       └── ...
├── main.py                      # 原有CLI (兼容)
├── main_new.py                  # 新CLI入口
├── test_real_data.py            # 测试脚本
├── pyproject.toml               # 项目配置
├── README.md                    # 主文档
└── README_NEW.md                # 新功能文档
```

## 使用方法

### 1. 新数据格式 (推荐)

```bash
# 运行TracePicker
python main_new.py run /path/to/experiment/data --sample-rate 0.1

# 查看数据信息
python main_new.py info /path/to/experiment/data

# 完整参数
python main_new.py run /path/to/experiment/data \
    --sample-rate 0.15 \
    --buffer-size 5000 \
    --combinations 200 \
    --seed 42 \
    --verbose
```

### 2. 直接使用算法

```python
from tracepicker import tracepicker_algorithm
from pathlib import Path

result = tracepicker_algorithm(
    data_folder=Path("/path/to/experiment"),
    sample_rate=0.1,
    buffer_size=4000,
    seed=42
)
```

### 3. 平台集成

```python
from tracepicker import TracePickerAlgorithm

# 用作rcabench算法
algorithm = TracePickerAlgorithm()
```

### 4. 兼容旧格式

```bash
# 仍然支持原有pickle格式
python main.py --dataset A --data_dir TracePicker/data
```

## 数据格式支持

### 新格式 (Parquet)
- **直接结构**: `data_folder/normal_traces.parquet`, `data_folder/abnormal_traces.parquet`
- **子目录结构**: `data_folder/experiment-name/normal_traces.parquet`, `data_folder/experiment-name/abnormal_traces.parquet`

### 旧格式 (Pickle)
- 继续支持原有的pickle文件格式
- 自动处理模块路径变更问题

## 性能改进

### 🚀 数据加载
- **Polars**: 比pandas快10-100倍
- **Lazy evaluation**: 内存高效的大数据处理
- **Schema validation**: 自动处理不匹配的数据结构

### 🚀 用户体验
- **Rich CLI**: 彩色输出、进度条、表格显示
- **错误处理**: 详细的错误信息和建议
- **自动发现**: 智能检测数据文件位置

## 测试

```bash
# 测试CLI
python test_real_data.py --help

# 测试真实数据
python test_real_data.py run /path/to/real/data --sample-rate 0.1

# 查看数据信息
python test_real_data.py info /path/to/real/data
```

## 依赖

新增依赖：
- `polars>=0.20.0` - 高性能数据处理
- `typer[all]>=0.9.0` - 现代CLI框架
- `rich>=13.0.0` - 丰富的终端输出
- `rcabench-platform>=0.3.26` - 平台集成

## 重大变更

1. **CLI界面**: 新的typer界面，旧CLI仍可用
2. **数据格式**: 主要支持parquet，pickle格式仍兼容  
3. **依赖**: 新增polars、typer、rich
4. **输出格式**: 增强的JSON/CSV输出

## 迁移指南

### 从旧代码迁移

```python
# 旧方式 (仍然可用)
from main import main
main()

# 新方式 - 直接算法调用
from tracepicker import tracepicker_algorithm
result = tracepicker_algorithm(data_folder=Path("data"))

# 新方式 - CLI
from tracepicker.cli import app
app()

# 新方式 - 平台集成
from tracepicker import TracePickerAlgorithm
algorithm = TracePickerAlgorithm()
```

### 从旧数据格式迁移
- 旧pickle文件继续工作，无需修改
- 新parquet数据获得更好性能
- 支持混合使用两种格式

## 总结

本次重构实现了：
- ✅ **标准化项目结构**
- ✅ **现代数据格式支持** 
- ✅ **平台标准集成**
- ✅ **用户友好界面**
- ✅ **完全向后兼容**
- ✅ **性能大幅提升**

TracePicker现在是一个现代化的、符合标准的Python包，同时保持了所有原有功能。
