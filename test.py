import mediapipe as mp
import inspect

# 1. 打印模块基本信息
print("=" * 60)
print("📌 MediaPipe 模块基础信息")
print("=" * 60)
print(f"模块路径: {mp.__file__}")
print(f"模块版本: {getattr(mp, '__version__', '未知版本')}")
print(f"模块名称: {mp.__name__}")

# 2. 打印模块的所有顶层属性/方法（过滤内置私有属性）
print("\n" + "=" * 60)
print("📌 MediaPipe 顶层可访问属性/方法")
print("=" * 60)
# 过滤掉以 __ 开头的内置属性，只显示用户可访问的内容
top_level_attrs = [attr for attr in dir(mp) if not attr.startswith('__')]
for i, attr in enumerate(top_level_attrs, 1):
    # 获取属性的类型（模块/函数/类等）
    attr_obj = getattr(mp, attr)
    attr_type = type(attr_obj).__name__
    # 特殊处理：如果是模块，显示其下的子属性
    if inspect.ismodule(attr_obj):
        sub_attrs = [sub_attr for sub_attr in dir(attr_obj) if not sub_attr.startswith('__')][:5]  # 只显示前5个
        print(f"{i:2d}. {attr:<20} | 类型: {attr_type:<10} | 子属性示例: {sub_attrs}")
    else:
        print(f"{i:2d}. {attr:<20} | 类型: {attr_type:<10} | 说明: {str(attr_obj)[:50]}...")

# 3. 针对性检查关键属性（比如你关心的 solutions）
print("\n" + "=" * 60)
print("📌 关键属性存在性检查")
print("=" * 60)
check_list = ['solutions', 'tasks', 'hands', 'drawing_utils']
for check_attr in check_list:
    has_attr = hasattr(mp, check_attr)
    print(f"mp 是否有 '{check_attr}' 属性: {'✅ 是' if has_attr else '❌ 否'}")
    # 如果是嵌套属性（比如 mp.solutions.hands）
    if check_attr == 'solutions' and has_attr:
        has_hands = hasattr(mp.solutions, 'hands')
        has_drawing = hasattr(mp.solutions, 'drawing_utils')
        print(f"  - mp.solutions.hands: {'✅ 存在' if has_hands else '❌ 不存在'}")
        print(f"  - mp.solutions.drawing_utils: {'✅ 存在' if has_drawing else '❌ 不存在'}")
    if check_attr == 'tasks' and has_attr:
        # 检查新版 Tasks API 的核心模块
        has_vision = hasattr(mp.tasks, 'vision')
        print(f"  - mp.tasks.vision: {'✅ 存在' if has_vision else '❌ 不存在'}")

# 4. 打印模块的层级结构（简化版）
print("\n" + "=" * 60)
print("📌 MediaPipe 模块层级结构（简化）")
print("=" * 60)
def print_module_tree(obj, prefix="", level=0, max_level=2):
    """递归打印模块树，限制层级避免输出过多"""
    if level > max_level:
        return
    # 只处理模块/类，过滤函数/实例等
    if inspect.ismodule(obj) or inspect.isclass(obj):
        attrs = [a for a in dir(obj) if not a.startswith('__') and not callable(getattr(obj, a))]
        if attrs:
            print(f"{prefix}{obj.__name__}: {attrs[:8]}...")  # 只显示前8个
            for attr in attrs[:3]:  # 只递归前3个属性，避免输出爆炸
                try:
                    child_obj = getattr(obj, attr)
                    print_module_tree(child_obj, prefix + "  ", level + 1, max_level)
                except:
                    pass

print_module_tree(mp)