# 任务状态检查和修复工具

这个命令行工具用于检查并修复可能卡在处理中状态的任务。在大量任务同时处理的情况下，有时任务会处于处理中状态但实际上已经完成，或者处理时间过长但没有结果。此工具可以帮助检测和修复这些问题。

## 主要功能

1. 检测任务状态与实际结果不匹配的情况（例如，有结果但状态不是已完成）
2. 检测长时间处理但无结果的任务
3. 检测长时间等待未处理的任务
4. 自动将状态不匹配的任务修复为正确状态
5. 自动将长时间无结果的处理中任务标记为超时

## 使用方法

### 基本使用

```bash
# 检查几分钟前更新过的处理中任务，仅报告不修复
python manage.py fix_stuck_tasks

# 检查并修复
python manage.py fix_stuck_tasks --force
```

### 指定任务ID

```bash
# 检查并修复指定任务
python manage.py fix_stuck_tasks --task-id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --force
```

### 检查所有未完成任务

```bash
# 检查所有未完成状态的任务
python manage.py fix_stuck_tasks --check-incomplete
```

### 参数说明

* `--check-only`: 仅检查不修复，只报告发现的问题
* `--minutes N`: 检查N分钟前更新的任务，默认5分钟
* `--task-id ID`: 指定任务ID进行检查和修复
* `--check-incomplete`: 检查所有未完成的任务，无时间限制
* `--force`: 强制更新所有匹配的任务状态，无论是否有结果
* `--status STATUS`: 强制更新为指定状态，默认completed，配合--force使用
* `--sync-records`: 同步更新关联的ImageUploadRecord记录

## 使用场景

1. **定期检查**: 设置为定时任务每10分钟运行一次，自动修复卡住的任务
   ```bash
   */10 * * * * cd /path/to/project && python manage.py fix_stuck_tasks --force --sync-records
   ```

2. **手动检查并修复特定任务**: 当用户报告特定任务卡住时
   ```bash
   python manage.py fix_stuck_tasks --task-id=任务ID --force --sync-records
   ```

3. **异常恢复**: 系统异常重启后，检查所有未完成的任务
   ```bash
   python manage.py fix_stuck_tasks --check-incomplete --force --sync-records
   ```

## 状态检测逻辑

1. 查找处理中但长时间未更新的任务
2. 检查是否有输出结果（图片URL）
3. 如果有结果，将状态更新为已完成
4. 如果处理时间过长无结果，标记为超时状态
5. 根据需要同步更新相关记录状态

## 注意事项

* 强制修复可能会将一些正在处理的任务错误地标记为已完成，请谨慎使用
* 建议在修复前先使用`--check-only`参数进行检查
* 处理大量任务时可能需要较长时间，建议在低峰期执行 